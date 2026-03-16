"""
Timeout Watcher Service — AI Agent Timeout Observer Feature

Background service ที่ทำงานทุก N นาทีเพื่อ:
- ตรวจสอบ tasks ที่ status='starting' และทิ้งช่วงนานเกิน threshold
- ส่ง Telegram alert เมื่อพบ task ที่ timeout
"""

import asyncio
import logging
from typing import Optional

from app.config import settings
from app.models.agent_task import AgentTaskLog
from app.services.agent_task_service import (
    find_timed_out_tasks,
    mark_task_timed_out,
    cleanup_expired_task_indices,
)
from app.services.telegram_service import tg_service

logger = logging.getLogger(__name__)


class TimeoutWatcher:
    """
    Background service that periodically checks for timed-out agent tasks.
    """

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._stop_event: Optional[asyncio.Event] = None

    async def start(self) -> None:
        """
        Start the timeout watcher background task.
        """
        if self._running:
            logger.warning("[TIMEOUT_WATCHER] Already running, ignoring start request")
            return

        self._running = True
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            f"[TIMEOUT_WATCHER] Started — interval: {settings.AGENT_TIMEOUT_CHECK_INTERVAL_MINUTES}min, "
            f"threshold: {settings.AGENT_TIMEOUT_THRESHOLD_MINUTES}min"
        )

    async def stop(self) -> None:
        """
        Stop the timeout watcher gracefully.
        """
        if not self._running:
            return

        self._running = False

        if self._stop_event:
            self._stop_event.set()

        if self._task:
            try:
                # Wait for the task to finish with a timeout
                await asyncio.wait_for(self._task, timeout=5.0)
            except asyncio.TimeoutError:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            except RuntimeError:
                # Task may be attached to a different loop (happens in tests)
                self._task = None
            self._task = None

        self._stop_event = None
        logger.info("[TIMEOUT_WATCHER] Stopped")

    async def _run_loop(self) -> None:
        """
        Main loop that runs periodically to check for timeouts.
        """
        interval_seconds = settings.AGENT_TIMEOUT_CHECK_INTERVAL_MINUTES * 60

        while self._running and self._stop_event and not self._stop_event.is_set():
            try:
                await self._check_timeouts()
                await self._cleanup_indices()
            except Exception as e:
                logger.error(f"[TIMEOUT_WATCHER] Error in check cycle: {e}", exc_info=True)

            # Wait for the next interval or until stopped
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=interval_seconds
                )
                # If we reach here, stop_event was set
                break
            except asyncio.TimeoutError:
                # Normal timeout — continue to next check cycle
                pass

    async def _check_timeouts(self) -> None:
        """
        Check for timed-out tasks and send alerts.
        """
        timed_out_tasks = await find_timed_out_tasks()

        if not timed_out_tasks:
            logger.debug("[TIMEOUT_WATCHER] No timed-out tasks found")
            return

        logger.warning(f"[TIMEOUT_WATCHER] Found {len(timed_out_tasks)} timed-out task(s)")

        for task_log in timed_out_tasks:
            try:
                # Mark as timed out in Redis
                await mark_task_timed_out(task_log.task_id)

                # Send Telegram alert
                await self._send_timeout_alert(task_log)

                logger.info(
                    f"[TIMEOUT_WATCHER] Marked task {task_log.task_id} as timeout "
                    f"(project: {task_log.project})"
                )
            except Exception as e:
                logger.error(
                    f"[TIMEOUT_WATCHER] Failed to process timeout for task {task_log.task_id}: {e}",
                    exc_info=True
                )

    async def _send_timeout_alert(self, task_log: AgentTaskLog) -> None:
        """
        Send a Telegram alert for a timed-out task.

        Args:
            task_log: AgentTaskLog that has timed out
        """
        # Determine chat_id
        chat_id_str = task_log.chat_id or settings.AKASA_CHAT_ID
        if not chat_id_str:
            logger.warning(
                f"[TIMEOUT_WATCHER] No chat_id for timeout alert (task: {task_log.task_id})"
            )
            return

        try:
            chat_id = int(chat_id_str)
        except ValueError:
            logger.error(f"[TIMEOUT_WATCHER] Invalid chat_id: {chat_id_str}")
            return

        # Build alert message
        from app.utils.markdown_utils import escape_markdown_v2_content, escape_markdown_v2

        safe_project = escape_markdown_v2_content(task_log.project)
        safe_task = escape_markdown_v2_content(
            task_log.task[:200] if len(task_log.task) > 200 else task_log.task
        )
        safe_source = escape_markdown_v2_content(task_log.source or "AI Agent")

        lines = [
            "⚠️ *🚨 ALERT: AI Agent Timeout!*",
            "",
            f"*Project:* {safe_project}",
            f"*Task:* {safe_task}",
            f"*Source:* {safe_source}",
            "",
            "_The AI agent seems to have crashed or stopped responding. "
            "No completion notification was received._",
        ]

        text = escape_markdown_v2("\n".join(lines))

        try:
            await tg_service.send_message(
                chat_id=chat_id,
                text=text,
            )
            logger.info(
                f"[TIMEOUT_WATCHER] Sent timeout alert to chat_id={chat_id} "
                f"for task {task_log.task_id}"
            )
        except Exception as e:
            logger.error(
                f"[TIMEOUT_WATCHER] Failed to send Telegram alert: {e}",
                exc_info=True
            )

    async def _cleanup_indices(self) -> None:
        """
        Periodically clean up expired task IDs from indices.
        """
        removed = await cleanup_expired_task_indices()
        if removed > 0:
            logger.info(f"[TIMEOUT_WATCHER] Cleaned up {removed} expired task IDs")


# Singleton instance
timeout_watcher = TimeoutWatcher()
