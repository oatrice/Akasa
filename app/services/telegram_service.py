import logging
from typing import TYPE_CHECKING, Optional

import httpx

from app.config import settings
from app.exceptions import BotBlockedException, UserChatIdNotFoundException
from app.services import redis_service
from app.utils.markdown_utils import escape_markdown_v2, escape_markdown_v2_content

if TYPE_CHECKING:
    from app.models.deployment import DeploymentRecord
    from app.models.notification import ReviewReadyRequest, TaskNotificationRequest

from datetime import datetime

logger = logging.getLogger(__name__)


class TelegramService:
    def __init__(self, bot_token: str):
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
        self.client = httpx.AsyncClient()

    async def send_message(
        self, chat_id: int, text: str, reply_markup: Optional[dict] = None, parse_mode: Optional[str] = "MarkdownV2"
    ) -> None:
        """
        Sends a text message to a specific chat using the Telegram Bot API.
        """
        payload = {
            "chat_id": chat_id,
            "text": text,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
            
        if reply_markup:
            payload["reply_markup"] = reply_markup

        try:
            response = await self.client.post(
                f"{self.api_url}/sendMessage", json=payload, timeout=10.0
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error(f"Telegram API Error: {e.response.text}")
            raise

    async def send_confirmation_message(self, chat_id: int, text: str, request_id: str):
        """
        ส่งข้อความยืนยันพร้อมปุ่ม Inline Keyboard (✅ Allow Once, 🛡️ Allow Session, ❌ Deny)
        """
        reply_markup = {
            "inline_keyboard": [
                [
                    {
                        "text": "✅ Allow Once",
                        "callback_data": f"confirm:{request_id}:allow",
                    },
                    {
                        "text": "🛡️ Allow Session",
                        "callback_data": f"confirm:{request_id}:session",
                    },
                    {"text": "❌ Deny", "callback_data": f"confirm:{request_id}:deny"},
                ]
            ]
        }
        await self.send_message(chat_id=chat_id, text=escape_markdown_v2(text), reply_markup=reply_markup)

    async def edit_message_text(
        self,
        chat_id: int,
        message_id: int,
        text: str,
        reply_markup: Optional[dict] = None,
        parse_mode: str = "MarkdownV2"
    ):
        """
        แก้ไขข้อความเดิม (ใช้สำหรับอัปเดตสถานะหลังจากกดปุ่ม)
        """
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup

        response = await self.client.post(
            f"{self.api_url}/editMessageText", json=payload, timeout=10.0
        )
        response.raise_for_status()

    async def send_proactive_message(self, user_id: int, text: str):
        """
        Sends a proactive message to a user by their user_id.
        """
        chat_id_str = await redis_service.get_chat_id_for_user(user_id)

        if not chat_id_str:
            logger.error(f"Chat ID not found for user_id: {user_id}")
            raise UserChatIdNotFoundException(
                f"Chat ID not found for user_id: {user_id}"
            )

        chat_id = int(chat_id_str)
        try:
            await self.send_message(chat_id=chat_id, text=escape_markdown_v2(text))
            logger.info(f"Proactive message sent to user_id: {user_id}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                logger.warning(f"Failed to send to user_id {user_id}: Bot was blocked.")
                raise BotBlockedException(f"Bot was blocked by user_id: {user_id}")
            else:
                logger.error(
                    f"HTTP error sending proactive message to user_id {user_id}: {e}"
                )
                raise  # Re-raise other HTTP errors

    async def send_task_notification(
        self, chat_id: int, request: "TaskNotificationRequest"
    ) -> None:
        """
        Sends a formatted task completion/failure notification to a Telegram chat.

        Builds a pre-escaped MarkdownV2 message with emoji status indicators and
        structured fields. Dynamic content (project, task, etc.) is escaped with
        escape_markdown_v2_content() to prevent accidental formatting from
        user-supplied strings containing characters like _ or *.

        This method sends the pre-formatted text directly to the Telegram API —
        bypassing send_message() — to avoid double-escaping the content.

        Args:
            chat_id: Telegram chat ID to send the notification to.
            request: TaskNotificationRequest containing task details.
        """
        status_config = {
            "success": ("✅", "Task Completed\\!"),
            "failure": ("❌", "Task Failed\\!"),
            "partial": ("⚠️", "Task Completed with Warnings"),
            "retrying": ("🔄", None),  # title built dynamically with retry counts
            "limit_reached": ("🚫", None),  # title built dynamically with retry counts
            "timeout": ("⏰", "Task Timed Out\\!"),
        }
        emoji, title = status_config.get(request.status, ("🔔", "Task Notification"))

        # Build dynamic title for retry statuses
        if title is None:
            if request.status == "retrying":
                if request.retry_count is not None and request.max_retries is not None:
                    title = f"Retrying\\.\\.\\. \\(Attempt {request.retry_count}/{request.max_retries}\\)"
                else:
                    title = "Retrying Task\\.\\.\\."
            elif request.status == "limit_reached":
                if request.max_retries is not None:
                    title = f"Retry Limit Reached \\({request.max_retries}/{request.max_retries}\\)"
                else:
                    title = "Retry Limit Reached"
            else:
                title = "Task Notification"

        # Truncate long task descriptions (Telegram message limit: 4096 chars)
        task_desc = request.task
        if len(task_desc) > 500:
            task_desc = task_desc[:497] + "..."

        # Pre-escape all dynamic content to prevent MarkdownV2 injection from
        # user-supplied strings that may contain * _ [ ] ( ) etc.
        safe_project = escape_markdown_v2_content(request.project or "General")
        safe_task = escape_markdown_v2_content(task_desc)

        lines = [f"{emoji} *{title}*", ""]
        lines.append(f"*Project:* {safe_project}")
        lines.append(f"*Task:* {safe_task}")

        if request.duration:
            safe_duration = escape_markdown_v2_content(request.duration)
            lines.append(f"*Duration:* {safe_duration}")

        if request.source:
            safe_source = escape_markdown_v2_content(request.source)
            lines.append(f"*Source:* {safe_source}")

        if request.message:
            msg = request.message
            if len(msg) > 300:
                msg = msg[:297] + "..."
            safe_message = escape_markdown_v2_content(msg)
            lines.append(f"*Details:* {safe_message}")

        if request.retry_count is not None and request.max_retries is not None:
            if request.status not in ("retrying", "limit_reached"):
                # Show retry summary on non-retry statuses (e.g., succeeded after 2 retries)
                lines.append(f"*Attempts:* {request.retry_count}/{request.max_retries}")

        if request.link:
            safe_link = escape_markdown_v2_content(request.link)
            lines.append(f"*Link:* {safe_link}")

        text = "\n".join(lines)

        # Send pre-formatted MarkdownV2 directly — do NOT route through
        # send_message() as that would call escape_markdown_v2() again
        # and double-escape the already-escaped content.
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "MarkdownV2",
        }
        response = await self.client.post(
            f"{self.api_url}/sendMessage",
            json=payload,
            timeout=10.0,
        )
        response.raise_for_status()
        logger.info(
            f"Task notification sent to chat_id: {chat_id}, status: {request.status}"
        )

    async def send_deployment_notification(
        self, chat_id: int, record: "DeploymentRecord"
    ) -> None:
        """
        Issue #34: ส่ง Telegram notification เมื่อ deployment เสร็จสิ้น
        ถ้า URL ถูก extract ได้จาก output จะแนบ Inline Keyboard URL button มาด้วย

        Args:
            chat_id: Telegram chat ID ที่จะส่งข้อความ
            record:  DeploymentRecord ที่มีผลลัพธ์การ deploy
        """
        if record.status == "success":
            status_emoji = "✅"
            status_title = "Deployment Succeeded\\!"
        else:
            status_emoji = "❌"
            status_title = "Deployment Failed\\!"

        safe_project = escape_markdown_v2_content(record.project)
        safe_command = escape_markdown_v2_content(record.command)

        lines = [f"{status_emoji} *{status_title}*", ""]
        lines.append(f"*Project:* {safe_project}")
        lines.append(f"*Command:* `{safe_command}`")

        # Compute human-readable duration from timestamps
        if record.started_at and record.finished_at:
            try:
                start = datetime.fromisoformat(record.started_at)
                end = datetime.fromisoformat(record.finished_at)
                secs = int((end - start).total_seconds())
                duration_str = (
                    f"{secs // 60}m {secs % 60}s" if secs >= 60 else f"{secs}s"
                )
                lines.append(f"*Duration:* {escape_markdown_v2_content(duration_str)}")
            except Exception:
                pass

        # Show last 200 chars of stderr on failure
        if record.status == "failed" and record.stderr:
            stderr_preview = record.stderr.strip()[-200:]
            lines.append(f"*Error:* {escape_markdown_v2_content(stderr_preview)}")

        # Show URL as plain text (also appears on the button below)
        if record.url:
            lines.append(f"*URL:* {escape_markdown_v2_content(record.url)}")

        text = "\n".join(lines)

        payload: dict = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "MarkdownV2",
        }

        # Attach URL button when a deployed URL was found (Issue #34)
        if record.url:
            payload["reply_markup"] = {
                "inline_keyboard": [[{"text": "🔗 Open Deployment", "url": record.url}]]
            }

        response = await self.client.post(
            f"{self.api_url}/sendMessage",
            json=payload,
            timeout=10.0,
        )
        response.raise_for_status()
        logger.info(
            f"Deployment notification sent to chat_id={chat_id}, "
            f"status={record.status}, url={record.url!r}"
        )

    async def send_review_notification(
        self, chat_id: int, request: "ReviewReadyRequest"
    ) -> None:
        """
        Send a "Changes Ready for Review" notification to Telegram.

        Called by the MCP tool `notify_pending_review` when Zed AI has finished
        generating changes and is waiting for the user to Accept / Reject them
        in the IDE.

        Args:
            chat_id: Telegram chat ID to send the notification to.
            request: ReviewReadyRequest containing task and change details.
        """
        safe_project = escape_markdown_v2_content(request.project or "General")
        safe_task = escape_markdown_v2_content(request.task)

        lines = [
            "✏️ *Changes Ready for Review*",
            "",
            f"*Project:* {safe_project}",
            f"*Task:* {safe_task}",
        ]

        if request.files_changed:
            # Show up to 10 files; truncate the rest
            shown = request.files_changed[:10]
            rest = len(request.files_changed) - len(shown)
            files_text = "\n".join(
                f"  • {escape_markdown_v2_content(f)}" for f in shown
            )
            if rest > 0:
                files_text += f"\n  \\.\\.\\. \\+{rest} more"
            lines.append(f"*Files Changed:*\n{files_text}")

        if request.summary:
            summary = request.summary
            if len(summary) > 300:
                summary = summary[:297] + "..."
            lines.append(f"*Summary:* {escape_markdown_v2_content(summary)}")

        lines += ["", "👆 *Open Zed to Accept / Reject*"]

        text = "\n".join(lines)

        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "MarkdownV2",
        }
        response = await self.client.post(
            f"{self.api_url}/sendMessage",
            json=payload,
            timeout=10.0,
        )
        response.raise_for_status()
        logger.info(
            f"Review-ready notification sent to chat_id: {chat_id}, task: {request.task!r}"
        )


# Create a singleton instance for the application to use
tg_service = TelegramService(settings.TELEGRAM_BOT_TOKEN)
