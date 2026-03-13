import logging
from typing import TYPE_CHECKING, Optional

import httpx

from app.config import settings
from app.exceptions import BotBlockedException, UserChatIdNotFoundException
from app.services import redis_service
from app.utils.markdown_utils import escape_markdown_v2, escape_markdown_v2_content

if TYPE_CHECKING:
    from app.models.notification import TaskNotificationRequest

logger = logging.getLogger(__name__)


class TelegramService:
    def __init__(self, bot_token: str):
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
        self.client = httpx.AsyncClient()

    async def send_message(
        self, chat_id: int, text: str, reply_markup: Optional[dict] = None
    ) -> None:
        """
        Sends a text message to a specific chat using the Telegram Bot API.
        """
        payload = {
            "chat_id": chat_id,
            "text": escape_markdown_v2(text),
            "parse_mode": "MarkdownV2",
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        response = await self.client.post(
            f"{self.api_url}/sendMessage", json=payload, timeout=10.0
        )
        response.raise_for_status()

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
        await self.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)

    async def edit_message_text(
        self,
        chat_id: int,
        message_id: int,
        text: str,
        reply_markup: Optional[dict] = None,
    ):
        """
        แก้ไขข้อความเดิม (ใช้สำหรับอัปเดตสถานะหลังจากกดปุ่ม)
        """
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": escape_markdown_v2(text),
            "parse_mode": "MarkdownV2",
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
            await self.send_message(chat_id=chat_id, text=text)
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


# Create a singleton instance for the application to use
tg_service = TelegramService(settings.TELEGRAM_BOT_TOKEN)
