"""
Chat Service — ประสานงานระหว่าง Telegram, Redis, และ LLM

Flow: Telegram → ดึง history จาก Redis → สร้าง messages context → LLM → บันทึก history → ส่งกลับ Telegram
Graceful degradation: ถ้า Redis ล่ม ยังทำงานได้เป็น stateless
"""

from app.models.telegram import Update
from app.services import llm_service, telegram_service, redis_service
import httpx
import logging
import os
import subprocess
from datetime import datetime

logger = logging.getLogger(__name__)

# Cache build info at startup
_BUILD_INFO_CACHE = None

def get_build_info() -> str:
    global _BUILD_INFO_CACHE
    if _BUILD_INFO_CACHE:
        return _BUILD_INFO_CACHE

    # Version
    version = "Unknown"
    version_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "VERSION")
    if os.path.exists(version_file):
        with open(version_file, "r") as f:
            version = f.read().strip()

    # Time (Server Startup time)
    built_at = datetime.now().astimezone().isoformat()

    # Git Hash
    git_hash = "Unknown"
    try:
        git_hash = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], 
            cwd=os.path.dirname(os.path.abspath(__file__)),
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
    except Exception:
        pass

    from app.config import settings
    _BUILD_INFO_CACHE = f"🤖 Version {version}\n🌍 Env {settings.ENVIRONMENT}\n🏗️ Built at {built_at}\n🔗 Commit {git_hash}"
    return _BUILD_INFO_CACHE

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

    # สร้าง messages context: system prompt + history + ข้อความใหม่ของ user
    from app.config import settings
    messages = [{"role": "system", "content": settings.SYSTEM_PROMPT}] + history + [{"role": "user", "content": prompt}]

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

    # Issue #25: Append build info in local development
    final_reply_to_send = reply
    if settings.ENVIRONMENT == "development":
        build_info = get_build_info()
        final_reply_to_send = f"{reply}\n\n---\n*Local Dev Info*\n{build_info}"

    try:
        await telegram_service.send_message(chat_id, final_reply_to_send)
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
