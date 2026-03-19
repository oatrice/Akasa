"""
Telegram inbound message rate limiter.
"""

from typing import Optional, Union

from app.config import settings
from app.services.redis_service import redis_pool


def _telegram_rate_key(identifier: Union[int, str]) -> str:
    return f"akasa:tg_rate:{identifier}"


async def check_telegram_message_rate_limit(
    identifier: Union[int, str],
    limit: Optional[int] = None,
    window_seconds: Optional[int] = None,
) -> tuple[bool, int]:
    """
    Check and increment the inbound Telegram message counter for a user/chat.

    Returns:
        (allowed, retry_after_seconds)
    """
    configured_limit = (
        settings.TELEGRAM_MESSAGE_RATE_LIMIT if limit is None else limit
    )
    configured_window = (
        settings.TELEGRAM_MESSAGE_RATE_WINDOW_SECONDS
        if window_seconds is None
        else window_seconds
    )

    if configured_limit <= 0 or configured_window <= 0:
        return True, 0

    key = _telegram_rate_key(identifier)
    current = await redis_pool.get(key)
    if current is not None and int(current) >= configured_limit:
        ttl = await redis_pool.ttl(key)
        return False, max(ttl, 1)

    await redis_pool.incr(key)
    if current is None:
        await redis_pool.expire(key, configured_window)

    return True, 0
