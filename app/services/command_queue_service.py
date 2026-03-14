"""
Command Queue Service — Feature #66
Telegram → Local Tools Command Queue (Bidirectional Control)

Responsibilities:
- Load and validate the command whitelist from config/command_whitelist.yaml
- Enqueue commands into Redis (LPUSH) with TTL meta key
- Dequeue commands (BRPOP) for the local daemon
- Track command status in Redis Hash
- Enforce per-user rate limiting
- Validate commands against the whitelist before enqueuing
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import yaml

from app.config import settings
from app.models.command import (
    CommandPayload,
    CommandQueueRequest,
    CommandQueueResponse,
    CommandStatusLiteral,
    CommandStatusResponse,
)
from app.services.redis_service import redis_pool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Whitelist loading
# ---------------------------------------------------------------------------

# Resolve config file relative to the project root (one level above this file's package)
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_WHITELIST_PATH = os.path.join(_PROJECT_ROOT, "config", "command_whitelist.yaml")

# In-memory cache so we only read the YAML once per process lifetime
_whitelist_cache: Optional[Dict[str, List[str]]] = None


def _load_whitelist() -> Dict[str, List[str]]:
    """
    Load the command whitelist from config/command_whitelist.yaml.

    Returns a flat dict: {tool_name: [allowed_command_name, ...]}

    Falls back to an empty dict if the file is missing or malformed so that
    the app can still start (all commands will then be rejected, which is
    the safe default).
    """
    global _whitelist_cache
    if _whitelist_cache is not None:
        return _whitelist_cache

    if not os.path.exists(_WHITELIST_PATH):
        logger.warning(
            f"Command whitelist file not found at {_WHITELIST_PATH}. "
            "All commands will be rejected."
        )
        _whitelist_cache = {}
        return _whitelist_cache

    try:
        with open(_WHITELIST_PATH, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)

        tools: Dict[str, List[str]] = {}
        for tool_name, tool_cfg in (data or {}).get("tools", {}).items():
            cmds = [
                entry["name"]
                for entry in (tool_cfg or {}).get("allowed_commands", [])
                if isinstance(entry, dict) and "name" in entry
            ]
            tools[tool_name] = cmds

        _whitelist_cache = tools
        logger.info(
            f"Loaded command whitelist: "
            + ", ".join(f"{t}={v}" for t, v in tools.items())
        )
        return _whitelist_cache

    except Exception as exc:
        logger.error(f"Failed to load command whitelist: {exc}", exc_info=True)
        _whitelist_cache = {}
        return _whitelist_cache


def reload_whitelist() -> None:
    """Force reload of the whitelist from disk (useful for tests)."""
    global _whitelist_cache
    _whitelist_cache = None
    _load_whitelist()


# ---------------------------------------------------------------------------
# Public validation helpers
# ---------------------------------------------------------------------------


def get_allowed_tools() -> List[str]:
    """Return the list of tool names that have at least one whitelisted command."""
    return list(_load_whitelist().keys())


def get_allowed_commands(tool: str) -> List[str]:
    """Return the list of allowed command names for a given tool."""
    return _load_whitelist().get(tool.lower(), [])


def is_tool_whitelisted(tool: str) -> bool:
    """Return True if the tool has any allowed commands configured."""
    return tool.lower() in _load_whitelist()


def is_command_whitelisted(tool: str, command: str) -> bool:
    """Return True if the (tool, command) pair is in the whitelist."""
    return command in get_allowed_commands(tool.lower())


def get_command_whitelist_entry(tool: str, command: str) -> Optional[dict]:
    """
    Return the whitelist entry for a (tool, command) pair.
    Returns None if not found. Used by local_tool_daemon for validation.
    """
    allowed = get_allowed_commands(tool.lower())
    if command in allowed:
        return {"tool": tool.lower(), "command": command}
    return None


# ---------------------------------------------------------------------------
# Redis key helpers
# ---------------------------------------------------------------------------


def _queue_key(tool: str) -> str:
    """Redis List key for pending commands."""
    return f"akasa:commands:{tool}"


def _status_key(command_id: str) -> str:
    """Redis Hash key for command status/result tracking."""
    return f"akasa:cmd_status:{command_id}"


def _meta_key(command_id: str) -> str:
    """
    Redis String key used exclusively as a TTL sentinel.

    The daemon checks for this key's existence before executing a command.
    If the key has expired (TTL elapsed), the command must not be executed.
    """
    return f"akasa:cmd_meta:{command_id}"


def _rate_key(user_id: int) -> str:
    """Redis String key for per-user rate limiting (expires after 60s)."""
    return f"akasa:cmd_rate:{user_id}"


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


async def check_rate_limit(user_id: int) -> tuple[bool, int]:
    """
    Check and increment the per-user command rate counter.

    Returns:
        (allowed: bool, retry_after_seconds: int)
        - allowed=True means the command may proceed.
        - allowed=False means the limit has been reached; retry_after_seconds
          indicates how many seconds remain on the current window.
    """
    key = _rate_key(user_id)
    limit = settings.COMMAND_QUEUE_RATE_LIMIT

    current = await redis_pool.get(key)
    if current is not None and int(current) >= limit:
        ttl = await redis_pool.ttl(key)
        return False, max(ttl, 1)

    # Increment and set/refresh a 60-second window
    await redis_pool.incr(key)
    # Only set expire when the key is new (first increment)
    if current is None:
        await redis_pool.expire(key, 60)

    return True, 0


# ---------------------------------------------------------------------------
# Enqueue
# ---------------------------------------------------------------------------


async def enqueue_command(
    request: CommandQueueRequest,
    user_id: int,
    chat_id: int,
) -> CommandQueueResponse:
    """
    Validate and push a command to the Redis queue.

    Steps:
    1. Normalise tool/command names.
    2. Validate against the whitelist.
    3. Build the payload with a fresh UUID command_id.
    4. LPUSH JSON payload to akasa:commands:{tool}.
    5. SET meta key with TTL so the daemon can detect expiry.
    6. Store initial status in a Redis Hash.

    Returns a CommandQueueResponse with the new command_id.
    Raises ValueError on whitelist violations (caller maps to HTTP 400).
    """
    tool = request.tool.strip().lower()
    command = request.command.strip()

    if not is_tool_whitelisted(tool):
        raise ValueError(f"Unknown tool '{tool}'. Allowed tools: {get_allowed_tools()}")

    if not is_command_whitelisted(tool, command):
        allowed = get_allowed_commands(tool)
        raise ValueError(
            f"Command '{command}' is not in the whitelist for tool '{tool}'. "
            f"Allowed commands: {allowed}"
        )

    now = datetime.now(timezone.utc)
    command_id = f"cmd_{uuid.uuid4().hex[:12]}"
    ttl = request.ttl_seconds or settings.COMMAND_QUEUE_TTL_SECONDS
    expires_at = now.replace(microsecond=0).isoformat().replace("+00:00", "Z")

    # Build the expiry timestamp as an ISO string for human-readable storage
    from datetime import timedelta

    expires_dt = now + timedelta(seconds=ttl)
    expires_str = expires_dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")

    queued_at_str = now.replace(microsecond=0).isoformat().replace("+00:00", "Z")

    payload = CommandPayload(
        command_id=command_id,
        tool=tool,
        command=command,
        args=request.args or {},
        user_id=user_id,
        chat_id=chat_id,
        queued_at=queued_at_str,
        ttl_seconds=ttl,
    )

    payload_json = payload.model_dump_json()

    try:
        # 1. Push payload to the queue list (LPUSH = stack, but daemon uses BRPOP
        #    which pops from the right — giving FIFO order when combined with LPUSH)
        await redis_pool.rpush(_queue_key(tool), payload_json)

        # 2. Set the TTL meta key so the daemon can verify freshness
        await redis_pool.set(_meta_key(command_id), "1", ex=ttl)

        # 3. Persist initial status in a Redis Hash (TTL = command TTL + 5 min buffer)
        status_data = {
            "command_id": command_id,
            "status": "queued",
            "tool": tool,
            "command": command,
            "queued_at": queued_at_str,
            "picked_up_at": "",
            "completed_at": "",
            "result": "",
            "error": "",
            "chat_id": str(chat_id),  # Store for routing notifications
        }
        status_key = _status_key(command_id)
        await redis_pool.hset(status_key, mapping=status_data)
        await redis_pool.expire(status_key, ttl + 300)

    except Exception as exc:
        logger.error(
            f"Redis error while enqueueing command {command_id}: {exc}", exc_info=True
        )
        raise

    logger.info(
        f"[ENQUEUE] {command_id} — tool={tool}, command={command}, "
        f"user_id={user_id}, ttl={ttl}s"
    )

    return CommandQueueResponse(
        command_id=command_id,
        status="queued",
        tool=tool,
        command=command,
        queued_at=queued_at_str,
        expires_at=expires_str,
    )


# ---------------------------------------------------------------------------
# Dequeue (used by the daemon)
# ---------------------------------------------------------------------------


async def dequeue_command(
    tool: str,
    timeout: int = 5,
) -> Optional[CommandPayload]:
    """
    Blocking pop a command from the Redis queue for the given tool.

    Uses BLPOP so the daemon can block efficiently rather than busy-polling.
    Returns None on timeout or if the queue is empty.

    The caller (daemon) is responsible for checking payload.is_expired()
    before executing the command.
    """
    result = await redis_pool.blpop(_queue_key(tool), timeout=timeout)
    if result is None:
        return None

    _, raw_json = result
    try:
        data = json.loads(raw_json)
        return CommandPayload(**data)
    except Exception as exc:
        logger.error(
            f"[DEQUEUE] Failed to parse payload for tool={tool}: {exc} — raw: {raw_json}"
        )
        return None


async def is_meta_key_alive(command_id: str) -> bool:
    """
    Return True if the TTL meta key still exists (command has NOT expired).

    The daemon calls this before executing a dequeued command.  If it returns
    False, the command's TTL has elapsed and execution must be skipped.
    """
    return await redis_pool.exists(_meta_key(command_id)) > 0


# ---------------------------------------------------------------------------
# Status management
# ---------------------------------------------------------------------------


async def get_command_status(command_id: str) -> Optional[CommandStatusResponse]:
    """
    Retrieve the current status of a command from the Redis Hash.

    Returns None if the command_id is unknown (expired + evicted from Redis).
    """
    data = await redis_pool.hgetall(_status_key(command_id))
    if not data:
        return None

    def _opt(val: str) -> Optional[str]:
        return val if val else None

    def _opt_int(val: str) -> Optional[int]:
        return int(val) if val else None

    return CommandStatusResponse(
        command_id=data.get("command_id", command_id),
        status=data.get("status", "queued"),  # type: ignore[arg-type]
        tool=data.get("tool", ""),
        command=data.get("command", ""),
        queued_at=data.get("queued_at", ""),
        picked_up_at=_opt(data.get("picked_up_at", "")),
        completed_at=_opt(data.get("completed_at", "")),
        result=_opt(data.get("result", "")),
        error=_opt(data.get("error", "")),
        chat_id=_opt_int(data.get("chat_id", "")),
    )


async def update_command_status(
    command_id: str,
    status: CommandStatusLiteral,
    result: Optional[str] = None,
    error: Optional[str] = None,
) -> bool:
    """
    Update the status Hash for a command.

    Returns True if the key existed (update succeeded), False if the command
    is unknown or has already been evicted from Redis.
    """
    key = _status_key(command_id)
    exists = await redis_pool.exists(key)
    if not exists:
        logger.warning(f"[STATUS] Cannot update {command_id} — key not found in Redis")
        return False

    now_str = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    update: Dict[str, str] = {"status": status}

    if status == "picked_up":
        update["picked_up_at"] = now_str
    elif status in ("success", "failed", "expired"):
        update["completed_at"] = now_str

    if result is not None:
        # Truncate to avoid oversized hashes
        update["result"] = result[:3000] if len(result) > 3000 else result

    if error is not None:
        update["error"] = error[:1000] if len(error) > 1000 else error

    await redis_pool.hset(key, mapping=update)
    logger.info(f"[STATUS] {command_id} → {status}")
    return True


async def mark_command_expired(command_id: str) -> None:
    """
    Mark a command as expired in the status Hash and delete the meta key.

    Called by the daemon when it dequeues a command but finds the meta key
    missing (TTL has elapsed).
    """
    await update_command_status(command_id, "expired")
    await redis_pool.delete(_meta_key(command_id))
    logger.info(f"[EXPIRE] {command_id} marked as expired")


# ---------------------------------------------------------------------------
# Queue monitoring
# ---------------------------------------------------------------------------


async def get_pending_count(tool: str) -> int:
    """Return the number of pending commands in the queue for a given tool."""
    return await redis_pool.llen(_queue_key(tool))
