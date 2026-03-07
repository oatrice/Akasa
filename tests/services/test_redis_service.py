import pytest
import pytest_asyncio
import json
import fakeredis.aioredis


@pytest_asyncio.fixture
async def fake_redis():
    """Create a fakeredis instance for testing."""
    server = fakeredis.aioredis.FakeServer()
    client = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
    yield client
    await client.flushall()
    await client.aclose()


@pytest.fixture
def patch_redis(fake_redis, monkeypatch):
    """Patch redis_service to use fakeredis."""
    import app.services.redis_service as rs
    monkeypatch.setattr(rs, "redis_pool", fake_redis)
    return fake_redis


# --- get_chat_history ---

@pytest.mark.asyncio
async def test_get_chat_history_empty(patch_redis):
    """ถ้าไม่มี history ต้อง return list ว่าง"""
    from app.services.redis_service import get_chat_history
    history = await get_chat_history(chat_id=99999)
    assert history == []


@pytest.mark.asyncio
async def test_get_chat_history_returns_chronological_order(patch_redis):
    """ดึง history กลับมาต้องเรียงตามลำดับเวลา (เก่าสุดก่อน)"""
    from app.services.redis_service import get_chat_history, add_message_to_history

    await add_message_to_history(100, "user", "Hello")
    await add_message_to_history(100, "assistant", "Hi there!")
    await add_message_to_history(100, "user", "How are you?")

    history = await get_chat_history(100)

    assert len(history) == 3
    assert history[0] == {"role": "user", "content": "Hello"}
    assert history[1] == {"role": "assistant", "content": "Hi there!"}
    assert history[2] == {"role": "user", "content": "How are you?"}


# --- add_message_to_history ---

@pytest.mark.asyncio
async def test_add_message_stores_correct_json(patch_redis):
    """ข้อความที่เก็บต้องเป็น JSON ที่ถูกต้อง"""
    from app.services.redis_service import add_message_to_history

    await add_message_to_history(200, "user", "Test message")

    raw = await patch_redis.lrange("chat_history:200", 0, -1)
    assert len(raw) == 1
    parsed = json.loads(raw[0])
    assert parsed == {"role": "user", "content": "Test message"}


# --- LTRIM (History Limit) ---

@pytest.mark.asyncio
async def test_history_is_trimmed_at_limit(patch_redis, monkeypatch):
    """ประวัติต้องถูกตัดไม่เกิน HISTORY_LIMIT"""
    from app.services import redis_service
    from app.services.redis_service import add_message_to_history, get_chat_history
    monkeypatch.setattr(redis_service.settings, "REDIS_HISTORY_LIMIT", 4)

    # เพิ่ม 6 ข้อความ (เกิน limit 4)
    for i in range(6):
        await add_message_to_history(300, "user", f"msg-{i}")

    history = await get_chat_history(300)

    # ควรเหลือแค่ 4 ข้อความล่าสุด
    assert len(history) == 4
    assert history[0]["content"] == "msg-2"
    assert history[3]["content"] == "msg-5"


# --- TTL ---

@pytest.mark.asyncio
async def test_ttl_is_set_on_history_key(patch_redis):
    """หลังเพิ่มข้อความ, key ต้องมี TTL"""
    from app.services.redis_service import add_message_to_history

    await add_message_to_history(400, "user", "Test TTL")

    ttl = await patch_redis.ttl("chat_history:400")
    # TTL should be set (positive value, default 86400)
    assert ttl > 0


# --- Chat Isolation ---

@pytest.mark.asyncio
async def test_chat_isolation(patch_redis):
    """ประวัติของแต่ละ chat_id ต้องแยกจากกัน"""
    from app.services.redis_service import add_message_to_history, get_chat_history

    await add_message_to_history(500, "user", "Chat A message")
    await add_message_to_history(600, "user", "Chat B message")

    history_a = await get_chat_history(500)
    history_b = await get_chat_history(600)

    assert len(history_a) == 1
    assert history_a[0]["content"] == "Chat A message"
    assert len(history_b) == 1
    assert history_b[0]["content"] == "Chat B message"
