from app.models.telegram import Update
from app.services import llm_service, telegram_service
import httpx
import logging

logger = logging.getLogger(__name__)

async def handle_chat_message(update: Update) -> None:
    """
    Processes an incoming Telegram update.
    Extracts text, sends to LLM, and sends the reply back to the user.
    """
    if not update.message or not update.message.text:
        # Ignore updates that are not text messages (e.g., edited messages, stickers)
        return

    chat_id = update.message.chat.id
    prompt = update.message.text

    try:
        reply = await llm_service.get_llm_reply(prompt)
        await telegram_service.send_message(chat_id, reply)
    except httpx.HTTPError as e:
        logger.error(f"Error communicating with external API: {e}")
        # Optionally, notify the user that an error occurred.
        # await telegram_service.send_message(chat_id, "Sorry, I am having trouble connecting to my brain right now.")
    except Exception as e:
        logger.error(f"Unexpected error in handle_chat_message: {e}")
