"""
Chat Service — ประสานงานระหว่าง Telegram, Redis, และ LLM

Flow: Telegram → ดึง history จาก Redis → สร้าง messages context → LLM → บันทึก history → ส่งกลับ Telegram
Graceful degradation: ถ้า Redis ล่ม ยังทำงานได้เป็น stateless
"""

from app.models.telegram import Update
from app.services import llm_service, telegram_service, redis_service
import httpx
import logging

logger = logging.getLogger(__name__)

async def handle_chat_message(update: Update) -> None:
    """
    Processes an incoming Telegram update.
    ดึง history จาก Redis, ส่งพร้อม prompt ไปให้ LLM, บันทึก history กลับ Redis
    """
    if not update.message or not update.message.text:
        return

    chat_id = update.message.chat.id
    prompt = update.message.text
    print(f"--- [DEBUG] Processing message from {chat_id}: {prompt} ---")

    # ดึง history จาก Redis (graceful: ถ้า Redis ล่ม → ใช้ list ว่าง)
    try:
        history = await redis_service.get_chat_history(chat_id)
    except Exception as e:
        logger.warning(f"Redis get_chat_history failed for {chat_id}: {e}")
        history = []

    # สร้าง messages context: history + ข้อความใหม่ของ user
    messages = history + [{"role": "user", "content": prompt}]

    try:
        reply = await llm_service.get_llm_reply(messages)
        print(f"--- [DEBUG] Received reply from LLM: {reply} ---")
        await telegram_service.send_message(chat_id, reply)
        print(f"--- [DEBUG] Message successfully sent to Telegram chat {chat_id} ---")

        # บันทึก user message + assistant reply ลง Redis
        try:
            await redis_service.add_message_to_history(chat_id, "user", prompt)
            await redis_service.add_message_to_history(chat_id, "assistant", reply)
        except Exception as e:
            logger.warning(f"Redis add_message_to_history failed for {chat_id}: {e}")

    except httpx.HTTPError as e:
        import traceback
        err_msg = f"Error communicating with external API: {e}\n{traceback.format_exc()}"
        logger.error(err_msg)
        with open("error.log", "a") as f:
            f.write(err_msg + "\n")
    except Exception as e:
        logger.error(f"Unexpected error in handle_chat_message: {e}")
