"""
Deploy Service — Async Deployment Service (Issue #33)

รันคำสั่ง Build/Deploy แบบ Asynchronous ด้วย asyncio.create_subprocess_shell
และเก็บสถานะการ Build ลงใน Redis เพื่อให้ Client poll ได้
"""

import asyncio
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Callable, Optional

from app.models.deployment import DeploymentRecord
from app.services.redis_service import redis_pool

logger = logging.getLogger(__name__)

# Redis key TTL — เก็บข้อมูล deployment ไว้ 24 ชั่วโมง
DEPLOYMENT_TTL = 86400


# ---------------------------------------------------------------------------
# URL extraction
# ---------------------------------------------------------------------------


def extract_url(text: str) -> Optional[str]:
    """
    ดึง HTTPS URL แรกที่พบจาก text output ของ deploy command
    ตัด trailing punctuation เพื่อให้ URL ใช้งานได้จริง
    """
    match = re.search(r"https://[^\s\"'<>\)\]]+", text)
    if not match:
        return None
    url = match.group(0).rstrip(".,;:")
    return url


# ---------------------------------------------------------------------------
# Redis CRUD
# ---------------------------------------------------------------------------


async def save_deployment(record: DeploymentRecord) -> None:
    """บันทึก DeploymentRecord ลงใน Redis"""
    await redis_pool.set(
        f"deployment:{record.deployment_id}",
        record.model_dump_json(),
        ex=DEPLOYMENT_TTL,
    )


async def get_deployment(deployment_id: str) -> Optional[DeploymentRecord]:
    """ดึง DeploymentRecord จาก Redis คืนค่า None ถ้าไม่พบ"""
    data = await redis_pool.get(f"deployment:{deployment_id}")
    if not data:
        return None
    try:
        return DeploymentRecord.model_validate_json(data)
    except Exception as e:
        logger.error(f"Failed to decode DeploymentRecord for {deployment_id}: {e}")
        return None


# ---------------------------------------------------------------------------
# Lifecycle helpers
# ---------------------------------------------------------------------------


async def create_deployment(
    command: str,
    cwd: str,
    project: str = "General",
    chat_id: Optional[str] = None,
) -> DeploymentRecord:
    """
    สร้าง DeploymentRecord ใหม่ในสถานะ 'pending' และบันทึกลง Redis
    คืนค่า record ที่สร้างขึ้น
    """
    deployment_id = str(uuid.uuid4())
    record = DeploymentRecord(
        deployment_id=deployment_id,
        status="pending",
        command=command,
        cwd=cwd,
        project=project,
        chat_id=chat_id,
    )
    await save_deployment(record)
    logger.info(
        f"Deployment created: id={deployment_id}, project={project!r}, "
        f"command={command!r}, cwd={cwd!r}"
    )
    return record


# ---------------------------------------------------------------------------
# Background task
# ---------------------------------------------------------------------------


async def run_deployment(
    deployment_id: str,
    notify_callback: Optional[Callable] = None,
) -> None:
    """
    Background task สำหรับรันคำสั่ง deploy และอัปเดตสถานะใน Redis

    ขั้นตอน:
    1. โหลด record จาก Redis → ตั้งสถานะ 'running'
    2. รัน command ด้วย asyncio subprocess
    3. จับ stdout/stderr และ exit code
    4. Extract URL จาก output (Issue #34)
    5. ตั้งสถานะ 'success' หรือ 'failed'
    6. บันทึกผลลงใน Redis
    7. เรียก notify_callback(record) สำหรับส่ง Telegram notification (Issue #34)

    Args:
        deployment_id: UUID ของ deployment ที่จะรัน
        notify_callback: Coroutine function ที่รับ DeploymentRecord เป็น arg
                         ใช้ส่ง Telegram notification หลังงานเสร็จ
    """
    record = await get_deployment(deployment_id)
    if not record:
        logger.error(f"Deployment not found in Redis: {deployment_id}")
        return

    # --- Mark as running ---
    record.status = "running"
    record.started_at = datetime.now(timezone.utc).isoformat()
    await save_deployment(record)
    logger.info(f"Deployment {deployment_id} started: {record.command!r}")

    try:
        proc = await asyncio.create_subprocess_shell(
            record.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=record.cwd,
        )
        stdout_bytes, stderr_bytes = await proc.communicate()

        record.stdout = stdout_bytes.decode("utf-8", errors="replace")
        record.stderr = stderr_bytes.decode("utf-8", errors="replace")
        record.exit_code = proc.returncode
        record.finished_at = datetime.now(timezone.utc).isoformat()

        # Extract deployed URL from stdout first, fallback to stderr
        record.url = extract_url(record.stdout) or extract_url(record.stderr)

        record.status = "success" if proc.returncode == 0 else "failed"

        logger.info(
            f"Deployment {deployment_id} finished: status={record.status}, "
            f"exit_code={record.exit_code}, url={record.url!r}"
        )

    except Exception as e:
        logger.error(f"Deployment {deployment_id} crashed: {e}", exc_info=True)
        record.status = "failed"
        record.stderr = str(e)
        record.exit_code = -1
        record.finished_at = datetime.now(timezone.utc).isoformat()

    await save_deployment(record)

    # --- Issue #34: Send Telegram notification ---
    if notify_callback:
        try:
            await notify_callback(record)
        except Exception as e:
            logger.error(
                f"Deployment notification callback failed for {deployment_id}: {e}",
                exc_info=True,
            )
