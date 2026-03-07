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
    print(f"--- [DEBUG] Processing message from {chat_id}: {prompt} ---")

    try:
        reply = await llm_service.get_llm_reply(prompt)
        print(f"--- [DEBUG] Received reply from LLM: {reply} ---")
        await telegram_service.send_message(chat_id, reply)
        print(f"--- [DEBUG] Message successfully sent to Telegram chat {chat_id} ---")
    except httpx.HTTPError as e:
        import traceback
        err_msg = f"Error communicating with external API: {e}\n{traceback.format_exc()}"
        logger.error(err_msg)
        with open("error.log", "a") as f:
            f.write(err_msg + "\n")
        # await telegram_service.send_message(chat_id, "Sorry, I am having trouble connecting to my brain right now.")
    except Exception as e:
        logger.error(f"Unexpected error in handle_chat_message: {e}")
