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

@pytest.mark.asyncio
async def test_get_chat_history_with_corrupted_json(patch_redis):
    """ถ้ามีข้อมูลบางตัวใน Redis ไม่ใช่ JSON ที่อ่านได้ (corrupted) → ต้องข้ามตัวนั้นและคืนค่าเฉพาะตัวที่อ่านได้"""
    from app.services.redis_service import get_chat_history
    import json

    # Push corrupted data directly to Redis
    await patch_redis.lpush("chat_history:150:default", json.dumps({"role": "user", "content": "Good"}))
    await patch_redis.lpush("chat_history:150:default", "NOT A JSON!!")
    await patch_redis.lpush("chat_history:150:default", json.dumps({"role": "assistant", "content": "Also Good"}))

    history = await get_chat_history(150)

    # ควรดึงได้แค่ 2 ข้อความที่อ่านเป็น JSON ได้
    assert len(history) == 2
    # ลำดับใน Redis = ["Also Good", "NOT A JSON!!", "Good"] (ล่าสุดอยู่ซ้ายสุด)
    # แต่ get_chat_history return `reversed` -> ["Good", "Also Good"]
    assert history[0]["content"] == "Good"
    assert history[1]["content"] == "Also Good"

# --- add_message_to_history ---

@pytest.mark.asyncio
async def test_add_message_stores_correct_json(patch_redis):
    """ข้อความที่เก็บต้องเป็น JSON ที่ถูกต้อง"""
    from app.services.redis_service import add_message_to_history

    await add_message_to_history(200, "user", "Test message")

    raw = await patch_redis.lrange("chat_history:200:default", 0, -1)
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


@pytest.mark.asyncio
async def test_redis_limit_zero(patch_redis, monkeypatch):
    """ถ้า REDIS_HISTORY_LIMIT = 0 ต้องไม่เก็บข้อมูลและ get_chat_history คืนค่าว่าง"""
    from app.services import redis_service
    from app.services.redis_service import add_message_to_history, get_chat_history
    monkeypatch.setattr(redis_service.settings, "REDIS_HISTORY_LIMIT", 0)

    chat_id = 350
    await add_message_to_history(chat_id, "user", "This should not be saved")

    history = await get_chat_history(chat_id)
    assert history == []

    # ตรวจสอบใน Redis จริงๆ ว่าไม่มี key หรือ key ว่างเปล่า
    raw = await patch_redis.lrange(f"chat_history:{chat_id}", 0, -1)
    assert len(raw) == 0

# --- TTL ---

@pytest.mark.asyncio
async def test_ttl_is_set_on_history_key(patch_redis):
    """หลังเพิ่มข้อความ, key ต้องมี TTL"""
    from app.services.redis_service import add_message_to_history

    await add_message_to_history(400, "user", "Test TTL")

    ttl = await patch_redis.ttl("chat_history:400:default")
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


# --- User Model Preference ---

@pytest.mark.asyncio
async def test_get_user_model_preference_none(patch_redis):
    """ถ้าผู้ใช้ยังไม่เคยตั้งค่า ต้องคืนค่า None"""
    from app.services.redis_service import get_user_model_preference
    pref = await get_user_model_preference(chat_id=777)
    assert pref is None


@pytest.mark.asyncio
async def test_set_and_get_user_model_preference(patch_redis):
    """ตั้งค่าแล้วต้องดึงกลับมาได้ถูกต้อง"""
    from app.services.redis_service import set_user_model_preference, get_user_model_preference
    
    chat_id = 888
    model_id = "anthropic/claude-3.5-sonnet"
    
    await set_user_model_preference(chat_id, model_id)
    
    pref = await get_user_model_preference(chat_id)
    assert pref == model_id


@pytest.mark.asyncio
async def test_model_preference_has_ttl(patch_redis):
    """การตั้งค่าโมเดลต้องมี TTL"""
    from app.services.redis_service import set_user_model_preference
    
    chat_id = 999
    await set_user_model_preference(chat_id, "some-model")
    
    ttl = await patch_redis.ttl(f"user_model_pref:{chat_id}")
    assert ttl > 0


# --- User ID to Chat ID Mapping (for Proactive Messaging - Issue #30) ---

@pytest.mark.asyncio
async def test_set_and_get_user_chat_id_mapping(patch_redis):
    """ทดสอบการเก็บและดึง mapping ระหว่าง user_id และ chat_id"""
    from app.services.redis_service import set_user_chat_id_mapping, get_chat_id_for_user

    user_id = 12345
    chat_id = 67890

    # 1. ทดสอบ get user ที่ยังไม่มี -> ควรได้ None
    retrieved_chat_id = await get_chat_id_for_user(user_id)
    assert retrieved_chat_id is None

    # 2. ตั้งค่า mapping
    await set_user_chat_id_mapping(user_id, chat_id)

    # 3. ดึงค่ากลับมา -> ต้องตรงกับที่ตั้งไว้ (และเป็น string ตามที่ Redis เก็บ)
    retrieved_chat_id = await get_chat_id_for_user(user_id)
    assert retrieved_chat_id == str(chat_id)

    # 4. Key ต้องมี TTL
    ttl = await patch_redis.ttl(f"user_chat_id:{user_id}")
    assert ttl > 0
