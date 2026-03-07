"""
Redis Service — จัดการประวัติการสนทนาใน Redis

ใช้ Redis LIST เก็บ messages แบบ LIFO (LPUSH) แล้ว reverse ตอนดึง
เพื่อให้ได้ลำดับเวลาถูกต้อง (เก่าสุด → ใหม่สุด)
"""

import redis.asyncio as redis
import json
from app.config import settings

# Connection pool — reuse connection ตลอด application lifetime
redis_pool = redis.from_url(settings.REDIS_URL, decode_responses=True)


async def get_chat_history(chat_id: int) -> list[dict]:
    """ดึงประวัติการสนทนาล่าสุดสำหรับ chat_id ในลำดับเวลา"""
    history_key = f"chat_history:{chat_id}"
    raw_history = await redis_pool.lrange(history_key, 0, settings.REDIS_HISTORY_LIMIT - 1)
    # LPUSH เก็บแบบ LIFO → reverse เพื่อให้ได้ chronological order
    return [json.loads(msg) for msg in reversed(raw_history)]


async def add_message_to_history(chat_id: int, role: str, content: str):
    """เพิ่มข้อความลงในประวัติการสนทนาของ chat_id"""
    history_key = f"chat_history:{chat_id}"
    message = json.dumps({"role": role, "content": content})
    # Push ข้อความใหม่ไปที่หัว list
    await redis_pool.lpush(history_key, message)
    # ตัด list ให้เหลือไม่เกิน limit
    await redis_pool.ltrim(history_key, 0, settings.REDIS_HISTORY_LIMIT - 1)
    # ตั้ง TTL เพื่อให้ key หมดอายุอัตโนมัติ (รีเซ็ตทุกครั้งที่มีข้อความใหม่)
    await redis_pool.expire(history_key, settings.REDIS_TTL_SECONDS)
