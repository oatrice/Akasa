import asyncio

import fakeredis.aioredis
import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def fake_redis():
    server = fakeredis.aioredis.FakeServer()
    client = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
    yield client
    await client.flushall()
    await client.aclose()


@pytest.fixture
def patch_rate_limiter(fake_redis, monkeypatch):
    import app.services.rate_limiter as rl

    monkeypatch.setattr(rl, "redis_pool", fake_redis)
    return fake_redis


@pytest.mark.asyncio
async def test_check_telegram_message_rate_limit_blocks_after_limit(patch_rate_limiter):
    from app.services.rate_limiter import check_telegram_message_rate_limit

    for _ in range(5):
        allowed, retry_after = await check_telegram_message_rate_limit(
            identifier=123,
            limit=5,
            window_seconds=60,
        )
        assert allowed is True
        assert retry_after == 0

    allowed, retry_after = await check_telegram_message_rate_limit(
        identifier=123,
        limit=5,
        window_seconds=60,
    )
    assert allowed is False
    assert retry_after >= 1


@pytest.mark.asyncio
async def test_check_telegram_message_rate_limit_resets_after_window(patch_rate_limiter):
    from app.services.rate_limiter import check_telegram_message_rate_limit

    allowed, _ = await check_telegram_message_rate_limit(
        identifier="chat-1",
        limit=1,
        window_seconds=1,
    )
    assert allowed is True

    allowed, _ = await check_telegram_message_rate_limit(
        identifier="chat-1",
        limit=1,
        window_seconds=1,
    )
    assert allowed is False

    await asyncio.sleep(1.1)

    allowed, retry_after = await check_telegram_message_rate_limit(
        identifier="chat-1",
        limit=1,
        window_seconds=1,
    )
    assert allowed is True
    assert retry_after == 0

