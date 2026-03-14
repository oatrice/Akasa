"""
Agent Task Service — AI Agent Timeout Observer Feature

Service สำหรับจัดการ AgentTaskLog ใน Redis:
- สร้าง/อัปเดต task log
- ค้นหา tasks ที่ timeout
- จัดการ lifecycle ของ task
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from app.config import settings
from app.models.agent_task import AgentTaskLog, AgentTaskStatus
from app.services.redis_service import redis_pool

logger = logging.getLogger(__name__)

# Redis key patterns
def _task_key(task_id: str) -> str:
    """Redis key for a single task log."""
    return f"akasa:agent_task:{task_id}"


def _task_index_key() -> str:
    """Redis Set key for tracking all active task IDs."""
    return "akasa:agent_tasks:active"


def _project_tasks_key(project: str) -> str:
    """Redis Set key for tracking tasks by project."""
    return f"akasa:agent_tasks:project:{project}"


async def create_task(
    project: str,
    task: str,
    source: Optional[str] = None,
    chat_id: Optional[str] = None,
    task_id: Optional[str] = None,
) -> AgentTaskLog:
    """
    Create a new agent task log with status 'starting'.

    Args:
        project: Project name
        task: Task description
        source: Source agent (e.g., 'Antigravity IDE')
        chat_id: Telegram chat ID for notifications
        task_id: Optional task ID (auto-generated if not provided)

    Returns:
        Created AgentTaskLog
    """
    if not task_id:
        task_id = f"task_{uuid.uuid4().hex[:12]}"

    task_log = AgentTaskLog(
        task_id=task_id,
        project=project,
        task=task,
        status="starting",
        source=source,
        chat_id=chat_id,
    )

    # Store in Redis with TTL (2x timeout threshold for safety)
    key = _task_key(task_id)
    ttl_seconds = settings.AGENT_TIMEOUT_THRESHOLD_MINUTES * 60 * 2
    await redis_pool.set(key, task_log.model_dump_json(), ex=ttl_seconds)

    # Add to active tasks index
    await redis_pool.sadd(_task_index_key(), task_id)
    # No TTL on index - we'll clean it up when tasks complete

    # Add to project-specific index
    await redis_pool.sadd(_project_tasks_key(project), task_id)

    logger.info(f"[AGENT_TASK] Created task {task_id} for project '{project}': {task[:50]}...")
    return task_log


async def update_task(
    task_id: str,
    status: AgentTaskStatus,
    duration: Optional[str] = None,
    message: Optional[str] = None,
    link: Optional[str] = None,
) -> Optional[AgentTaskLog]:
    """
    Update an existing task's status.

    Args:
        task_id: Task ID to update
        status: New status (success, failure, partial, timeout)
        duration: Optional task duration
        message: Optional message
        link: Optional link

    Returns:
        Updated AgentTaskLog or None if not found
    """
    task_log = await get_task(task_id)
    if not task_log:
        logger.warning(f"[AGENT_TASK] Cannot update task {task_id} — not found")
        return None

    # Update status
    task_log.mark_completed(status)

    # Update optional fields
    if duration:
        task_log.duration = duration
    if message:
        task_log.message = message
    if link:
        task_log.link = link

    # Update in Redis (keep existing TTL or set new one)
    key = _task_key(task_id)
    ttl = await redis_pool.ttl(key)
    if ttl < 0:
        ttl = 3600  # 1 hour default if TTL was lost

    await redis_pool.set(key, task_log.model_dump_json(), ex=ttl)

    # Remove from active tasks index if completed
    if status in ("success", "failure", "partial", "timeout"):
        await redis_pool.srem(_task_index_key(), task_id)

    logger.info(f"[AGENT_TASK] Updated task {task_id} → {status}")
    return task_log


async def get_task(task_id: str) -> Optional[AgentTaskLog]:
    """
    Retrieve a task log by ID.

    Args:
        task_id: Task ID to retrieve

    Returns:
        AgentTaskLog or None if not found
    """
    key = _task_key(task_id)
    data = await redis_pool.get(key)
    if not data:
        return None

    try:
        return AgentTaskLog.model_validate_json(data)
    except Exception as e:
        logger.error(f"[AGENT_TASK] Failed to parse task {task_id}: {e}")
        return None


async def get_active_tasks() -> List[AgentTaskLog]:
    """
    Get all tasks currently in 'starting' status.

    Returns:
        List of AgentTaskLog with status 'starting'
    """
    # Get all task IDs from active index
    task_ids = await redis_pool.smembers(_task_index_key())
    if not task_ids:
        return []

    tasks = []
    for task_id in task_ids:
        task_log = await get_task(task_id)
        if task_log and task_log.status == "starting":
            tasks.append(task_log)
        elif task_log is None:
            # Task expired in Redis but still in index — clean up
            await redis_pool.srem(_task_index_key(), task_id)

    return tasks


async def find_timed_out_tasks() -> List[AgentTaskLog]:
    """
    Find all tasks that have exceeded the timeout threshold.

    Returns:
        List of AgentTaskLog that have timed out
    """
    active_tasks = await get_active_tasks()
    threshold = settings.AGENT_TIMEOUT_THRESHOLD_MINUTES

    timed_out = []
    for task_log in active_tasks:
        if task_log.is_timed_out(threshold):
            timed_out.append(task_log)

    return timed_out


async def mark_task_timed_out(task_id: str) -> Optional[AgentTaskLog]:
    """
    Mark a task as timed out.

    Args:
        task_id: Task ID to mark as timed out

    Returns:
        Updated AgentTaskLog or None if not found
    """
    return await update_task(task_id, "timeout")


async def get_tasks_by_project(project: str) -> List[AgentTaskLog]:
    """
    Get all tasks for a specific project.

    Args:
        project: Project name

    Returns:
        List of AgentTaskLog for the project
    """
    task_ids = await redis_pool.smembers(_project_tasks_key(project))
    if not task_ids:
        return []

    tasks = []
    for task_id in task_ids:
        task_log = await get_task(task_id)
        if task_log:
            tasks.append(task_log)

    return tasks


async def cleanup_expired_task_indices() -> int:
    """
    Clean up task IDs from indices that have expired in Redis.

    This should be called periodically to prevent index bloat.

    Returns:
        Number of expired task IDs removed
    """
    task_ids = await redis_pool.smembers(_task_index_key())
    removed = 0

    for task_id in task_ids:
        key = _task_key(task_id)
        exists = await redis_pool.exists(key)
        if not exists:
            await redis_pool.srem(_task_index_key(), task_id)
            # Also try to remove from project indices
            # (we don't know which project, so we leave this for now)
            removed += 1

    if removed > 0:
        logger.info(f"[AGENT_TASK] Cleaned up {removed} expired task IDs from index")

    return removed
