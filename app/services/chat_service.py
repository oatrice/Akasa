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

    reply = ""
    try:
        reply = await llm_service.get_llm_reply(messages)
        print(f"--- [DEBUG] Received reply from LLM: {reply} ---")
    except (httpx.TimeoutException, httpx.HTTPError) as e:
        logger.error(f"API Error getting LLM reply for {chat_id}: {e}")
        await telegram_service.send_message(chat_id, "ขออภัย ระบบขัดข้องชั่วคราวในการตอบสนอง 🙇‍♂️")
        return
    except (ValueError, KeyError, TypeError) as e:
        logger.error(f"Malformed LLM response for {chat_id}: {e}")
        await telegram_service.send_message(chat_id, "ขออภัย ระบบไม่สามารถประมวลผลคำตอบได้ 🙇‍♂️")
        return
    except Exception as e:
        logger.error(f"Unexpected error getting LLM reply for {chat_id}: {e}")
        return

    try:
        await telegram_service.send_message(chat_id, reply)
        print(f"--- [DEBUG] Message successfully sent to Telegram chat {chat_id} ---")
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to send message to Telegram for {chat_id}. HTTP Status Error: {e}")
        return
    except Exception as e:
        logger.error(f"Unexpected error sending to Telegram for {chat_id}: {e}")
        return

    # บันทึก user message + assistant reply ลง Redis
    try:
        await redis_service.add_message_to_history(chat_id, "user", prompt)
        await redis_service.add_message_to_history(chat_id, "assistant", reply)
    except Exception as e:
        logger.warning(f"Redis add_message_to_history failed for {chat_id}: {e}")
