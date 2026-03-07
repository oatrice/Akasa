"""
Integration Tests สำหรับ Redis Service
ทดสอบกับ Redis จริง (ไม่ใช่ fakeredis) เพื่อให้ใกล้เคียง production

ถ้าไม่มี Redis → skip ตัวเองอัตโนมัติ
"""

import pytest
import pytest_asyncio
import json
import redis.asyncio as redis


def is_redis_available():
    """เช็คว่ามี Redis server พร้อมใช้งานหรือไม่"""
    import redis as sync_redis
    try:
        client = sync_redis.Redis(host="localhost", port=6379, socket_timeout=1)
        client.ping()
        client.close()
        return True
    except Exception:
        return False


# Skip ทั้ง module ถ้าไม่มี Redis
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not is_redis_available(), reason="Redis server is not available"),
]


@pytest_asyncio.fixture
async def redis_client():
    """สร้าง Redis connection จริงสำหรับ test"""
    client = redis.from_url("redis://localhost:6379", decode_responses=True)
    yield client
    # Cleanup: ลบ keys ที่ test สร้างขึ้น
    keys = await client.keys("chat_history:test_*")
    if keys:
        await client.delete(*keys)
    await client.aclose()


@pytest_asyncio.fixture
async def setup_redis_service(redis_client, monkeypatch):
    """Patch redis_service ให้ใช้ Redis จริง"""
    import app.services.redis_service as rs
    monkeypatch.setattr(rs, "redis_pool", redis_client)
    return redis_client


@pytest.mark.asyncio
async def test_write_and_read_roundtrip(setup_redis_service):
    """ทดสอบ write → read roundtrip กับ Redis จริง"""
    from app.services.redis_service import add_message_to_history, get_chat_history

    chat_id = "test_roundtrip"
    await add_message_to_history(chat_id, "user", "Hello")
    await add_message_to_history(chat_id, "assistant", "Hi there!")

    history = await get_chat_history(chat_id)

    assert len(history) == 2
    assert history[0] == {"role": "user", "content": "Hello"}
    assert history[1] == {"role": "assistant", "content": "Hi there!"}


@pytest.mark.asyncio
async def test_ltrim_behavior(setup_redis_service, monkeypatch):
    """ทดสอบ LTRIM ตัด history ที่เกิน limit"""
    import app.services.redis_service as rs
    from app.services.redis_service import add_message_to_history, get_chat_history
    monkeypatch.setattr(rs.settings, "REDIS_HISTORY_LIMIT", 4)

    chat_id = "test_ltrim"
    for i in range(6):
        await add_message_to_history(chat_id, "user", f"msg-{i}")

    history = await get_chat_history(chat_id)

    assert len(history) == 4
    assert history[0]["content"] == "msg-2"
    assert history[3]["content"] == "msg-5"


@pytest.mark.asyncio
async def test_ttl_is_set(setup_redis_service):
    """ทดสอบว่า TTL ถูกตั้งค่าหลังเพิ่มข้อความ"""
    from app.services.redis_service import add_message_to_history

    chat_id = "test_ttl"
    await add_message_to_history(chat_id, "user", "Test TTL")

    ttl = await setup_redis_service.ttl(f"chat_history:{chat_id}")
    assert ttl > 0


@pytest.mark.asyncio
async def test_concurrent_chat_isolation(setup_redis_service):
    """ทดสอบว่า history ของแต่ละ chat_id แยกจากกัน"""
    from app.services.redis_service import add_message_to_history, get_chat_history

    await add_message_to_history("test_isolation_A", "user", "Message for A")
    await add_message_to_history("test_isolation_B", "user", "Message for B")

    history_a = await get_chat_history("test_isolation_A")
    history_b = await get_chat_history("test_isolation_B")

    assert history_a[0]["content"] == "Message for A"
    assert len(history_b) == 1
    assert history_b[0]["content"] == "Message for B"

@pytest.mark.asyncio
async def test_ttl_short_sleep(setup_redis_service, monkeypatch):
    """ทดสอบว่าเมื่อตั้ง TTL=1 วิ แล้วรอ 1.1 วิ ประวัติต้องถูกลบอัตโนมัติจาก Redis"""
    import asyncio
    import app.services.redis_service as rs
    from app.services.redis_service import add_message_to_history, get_chat_history
    
    monkeypatch.setattr(rs.settings, "REDIS_TTL_SECONDS", 1)

    chat_id = "test_ttl_sleep"
    await add_message_to_history(chat_id, "user", "This expires quickly")
    
    history_before = await get_chat_history(chat_id)
    assert len(history_before) == 1
    
    await asyncio.sleep(1.1)
    
    history_after = await get_chat_history(chat_id)
    assert len(history_after) == 0
