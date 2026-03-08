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
from app.config import settings

logger = logging.getLogger(__name__)

# Cache build info at startup
_BUILD_INFO_CACHE = None

def get_build_info() -> str:
    global _BUILD_INFO_CACHE
    if _BUILD_INFO_CACHE:
        return _BUILD_INFO_CACHE

    # Version
    version = "Unknown"
    version_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "VERSION")
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

    _BUILD_INFO_CACHE = f"🤖 Version {version}\n🌍 Env {settings.ENVIRONMENT}\n🏗️ Built at {built_at}\n🔗 Commit {git_hash}"
    return _BUILD_INFO_CACHE


async def _send_response(chat_id: int, text: str) -> None:
    """Helper สำหรับส่งข้อความพร้อมเติม Local Dev Info ถ้าอยู่ในโหมด development"""
    final_text = text
    if settings.ENVIRONMENT == "development":
        build_info = get_build_info()
        final_text = f"{text}\n\n---\n*Local Dev Info*\n{build_info}"
    
    try:
        await telegram_service.send_message(chat_id, final_text)
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to send message to Telegram for {chat_id}. HTTP Status Error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error sending to Telegram for {chat_id}: {e}")


async def handle_chat_message(update: Update) -> None:
    """
    Processes an incoming Telegram update.
    แยกแยะระหว่างคำสั่ง (Command) และข้อความปกติ
    """
    if not update.message or not update.message.text:
        return

    chat_id = update.message.chat.id
    text = update.message.text.strip()
    print(f"--- [DEBUG] Processing message from {chat_id}: {text} ---")

    if text.startswith("/"):
        await _handle_command(chat_id, text)
    else:
        await _handle_standard_message(chat_id, text)


async def _handle_command(chat_id: int, command_text: str) -> None:
    """จัดการคำสั่งต่างๆ (เช่น /model)"""
    parts = command_text.split()
    cmd = parts[0].lower()
    
    if cmd == "/model":
        await _handle_model_command(chat_id, parts[1:] if len(parts) > 1 else [])
    else:
        await _send_response(chat_id, f"❌ Unknown command: {cmd}")


async def _handle_model_command(chat_id: int, args: list[str]) -> None:
    """จัดการคำสั่ง /model"""
    available_models = settings.AVAILABLE_MODELS
    
    if not args:
        # กรณี /model เฉยๆ -> แสดงสถานะปัจจุบันและรายการที่เลือกได้
        try:
            current_pref = await redis_service.get_user_model_preference(chat_id)
        except Exception:
            current_pref = None
            
        model_name = "Default (Gemini 2.5 Flash)"
        if current_pref:
            # หาชื่อเล่นจาก identifier
            for alias, info in available_models.items():
                if info["identifier"] == current_pref:
                    model_name = info["name"]
                    break
            else:
                model_name = current_pref # fallback ถ้าหา alias ไม่เจอ
                
        message = f"❇️ Current model: `{model_name}`\n\nTo switch, use `/model <alias>`:\n"
        for alias, info in available_models.items():
            message += f"- `{alias}`: {info['name']}\n"
            
        await _send_response(chat_id, message)
        return

    # กรณี /model <alias> -> อัปเดตการตั้งค่า
    alias = args[0].lower()
    if alias in available_models:
        model_info = available_models[alias]
        try:
            await redis_service.set_user_model_preference(chat_id, model_info["identifier"])
            await _send_response(chat_id, f"✅ Model selection updated to: {model_info['name']}")
        except Exception as e:
            logger.error(f"Failed to save model preference for {chat_id}: {e}")
            await _send_response(chat_id, "❌ Failed to save model preference. Please try again.")
    else:
        # Alias ไม่ถูกต้อง
        message = f"❌ Invalid model '{alias}'.\nAvailable models:\n"
        for a in available_models.keys():
            message += f"- `{a}`\n"
        await _send_response(chat_id, message)


async def _handle_standard_message(chat_id: int, prompt: str) -> None:
    """จัดการข้อความปกติ (ดึง history, เรียก LLM, บันทึก history)"""
    
    # ดึง Model Preference จาก Redis
    try:
        model_pref = await redis_service.get_user_model_preference(chat_id)
    except Exception as e:
        logger.warning(f"Redis get_user_model_preference failed for {chat_id}: {e}")
        model_pref = None

    # ดึง history จาก Redis (graceful: ถ้า Redis ล่ม → ใช้ list ว่าง)
    try:
        history = await redis_service.get_chat_history(chat_id)
    except Exception as e:
        logger.warning(f"Redis get_chat_history failed for {chat_id}: {e}")
        history = []

    # สร้าง messages context: system prompt + history + ข้อความใหม่ของ user
    messages = [{"role": "system", "content": settings.SYSTEM_PROMPT}] + history + [{"role": "user", "content": prompt}]

    reply = ""
    try:
        # เรียก LLM พร้อมส่งโมเดลที่ผู้ใช้เลือก (ถ้ามี)
        reply = await llm_service.get_llm_reply(messages, model=model_pref)
        print(f"--- [DEBUG] Received reply from LLM: {reply} ---")
    except (httpx.TimeoutException, httpx.HTTPError) as e:
        logger.error(f"API Error getting LLM reply for {chat_id}: {e}")
        await _send_response(chat_id, "ขออภัย ระบบขัดข้องชั่วคราวในการตอบสนอง 🙇‍♂️")
        return
    except (ValueError, KeyError, TypeError) as e:
        logger.error(f"Malformed LLM response for {chat_id}: {e}")
        await _send_response(chat_id, "ขออภัย ระบบไม่สามารถประมวลผลคำตอบได้ 🙇‍♂️")
        return
    except Exception as e:
        logger.error(f"Unexpected error getting LLM reply for {chat_id}: {e}")
        await _send_response(chat_id, "ขออภัย เกิดข้อผิดพลาดที่ไม่คาดคิด โปรดลองอีกครั้งในภายหลัง")
        return

    # ส่งคำตอบกลับหาผู้ใช้
    await _send_response(chat_id, reply)

    # บันทึก user message + assistant reply ลง Redis
    try:
        await redis_service.add_message_to_history(chat_id, "user", prompt)
        await redis_service.add_message_to_history(chat_id, "assistant", reply)
    except Exception as e:
        logger.warning(f"Redis add_message_to_history failed for {chat_id}: {e}")
