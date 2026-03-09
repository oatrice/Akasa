import httpx
from app.config import settings
from app.utils.markdown_utils import escape_markdown_v2
from app.services import redis_service
from app.exceptions import UserChatIdNotFoundException, BotBlockedException
import logging

logger = logging.getLogger(__name__)

class TelegramService:
    def __init__(self, bot_token: str):
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
        self.client = httpx.AsyncClient()

    async def send_message(self, chat_id: int, text: str) -> None:
        """
        Sends a text message to a specific chat using the Telegram Bot API.
        """
        payload = {
            "chat_id": chat_id,
            "text": escape_markdown_v2(text),
            "parse_mode": "MarkdownV2"
        }

        response = await self.client.post(
            f"{self.api_url}/sendMessage",
            json=payload,
            timeout=10.0
        )
        response.raise_for_status()

    async def send_proactive_message(self, user_id: int, text: str):
        """
        Sends a proactive message to a user by their user_id.
        """
        chat_id_str = await redis_service.get_chat_id_for_user(user_id)
        
        if not chat_id_str:
            logger.error(f"Chat ID not found for user_id: {user_id}")
            raise UserChatIdNotFoundException(f"Chat ID not found for user_id: {user_id}")

        chat_id = int(chat_id_str)
        try:
            await self.send_message(chat_id=chat_id, text=text)
            logger.info(f"Proactive message sent to user_id: {user_id}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                logger.warning(f"Failed to send to user_id {user_id}: Bot was blocked.")
                raise BotBlockedException(f"Bot was blocked by user_id: {user_id}")
            else:
                logger.error(f"HTTP error sending proactive message to user_id {user_id}: {e}")
                raise  # Re-raise other HTTP errors

# Create a singleton instance for the application to use
tg_service = TelegramService(settings.TELEGRAM_BOT_TOKEN)
