"""
Tests for CommandQueueService — Feature #66
TDD: Red → Green → Refactor

Tests cover:
  - Whitelist loading & validation
  - Enqueue / dequeue commands
  - Rate limiting
  - TTL meta key checks
  - Status management
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest

from app.models.command import (
    CommandPayload,
    CommandQueueRequest,
    CommandQueueResponse,
    CommandStatusResponse,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_WHITELIST_YAML = """
tools:
  gemini:
    allowed_commands:
      - name: run_task
        description: "Run a Gemini CLI task"
        allowed_args: [task, pr_number]
      - name: check_status
        description: "Check Gemini CLI status"
        allowed_args: []
  luma:
    allowed_commands:
      - name: list_issues
        description: "List open Luma issues"
        allowed_args: [project]
"""

SAMPLE_WHITELIST_WITH_EXECUTION = """
tools:
  zed:
    defaults:
      execution:
        type: cli
        executable: zed
        include_command_name: false
        path_arg_keys: [path]
        allowed_paths: ["/tmp"]
    allowed_commands:
      - name: open_file
        description: "Open file"
        allowed_args: [path]
      - name: run_task
        description: "Run task"
        allowed_args: [task_name]
        execution:
          include_command_name: true
          path_arg_keys: []
"""


@pytest.fixture(autouse=True)
def reset_whitelist_cache():
    """Reset the module-level whitelist cache before each test."""
    import app.services.command_queue_service as svc

    svc._whitelist_cache = None
    svc._whitelist_raw_cache = None
    yield
    svc._whitelist_cache = None
    svc._whitelist_raw_cache = None


@pytest.fixture
def mock_redis():
    """Provide a mock redis_pool for all service calls."""
    with patch("app.services.command_queue_service.redis_pool") as mock:
        # Default returns for common operations
        mock.rpush = AsyncMock(return_value=1)
        mock.set = AsyncMock(return_value=True)
        mock.hset = AsyncMock(return_value=True)
        mock.expire = AsyncMock(return_value=True)
        mock.get = AsyncMock(return_value=None)
        mock.incr = AsyncMock(return_value=1)
        mock.exists = AsyncMock(return_value=1)
        mock.ttl = AsyncMock(return_value=30)
        mock.llen = AsyncMock(return_value=0)
        mock.blpop = AsyncMock(return_value=None)
        mock.hgetall = AsyncMock(return_value={})
        mock.delete = AsyncMock(return_value=1)
        yield mock


# ---------------------------------------------------------------------------
# Whitelist tests
# ---------------------------------------------------------------------------


class TestWhitelistLoading:
    """Verify command whitelist loading from YAML."""

    def test_load_whitelist_parses_yaml(self):
        """whitelist ถูกโหลดจาก YAML — tool gemini มี 2 commands."""
        import app.services.command_queue_service as svc

        with patch("builtins.open", mock_open(read_data=SAMPLE_WHITELIST_YAML)):
            with patch("os.path.exists", return_value=True):
                svc._whitelist_cache = None
                result = svc._load_whitelist()

        assert "gemini" in result
        assert "run_task" in result["gemini"]
        assert "check_status" in result["gemini"]
        assert len(result["gemini"]) == 2

    def test_load_whitelist_missing_file_returns_empty(self):
        """ถ้าไฟล์ whitelist ไม่มี ต้อง return {} (safe default)."""
        import app.services.command_queue_service as svc

        with patch("os.path.exists", return_value=False):
            svc._whitelist_cache = None
            result = svc._load_whitelist()

        assert result == {}

    def test_load_whitelist_malformed_yaml_returns_empty(self):
        """YAML ที่ อ่านไม่ได้ ต้อง return {} (graceful fallback)."""
        import app.services.command_queue_service as svc

        with patch("builtins.open", side_effect=Exception("YAML parse error")):
            with patch("os.path.exists", return_value=True):
                svc._whitelist_cache = None
                result = svc._load_whitelist()

        assert result == {}

    def test_is_tool_whitelisted_known_tool(self):
        """gemini ต้อง return True."""
        import app.services.command_queue_service as svc

        with patch("builtins.open", mock_open(read_data=SAMPLE_WHITELIST_YAML)):
            with patch("os.path.exists", return_value=True):
                svc._whitelist_cache = None
                assert svc.is_tool_whitelisted("gemini") is True

    def test_is_tool_whitelisted_unknown_tool(self):
        """unknown_tool ต้อง return False."""
        import app.services.command_queue_service as svc

        with patch("builtins.open", mock_open(read_data=SAMPLE_WHITELIST_YAML)):
            with patch("os.path.exists", return_value=True):
                svc._whitelist_cache = None
                assert svc.is_tool_whitelisted("unknown_tool") is False

    def test_is_command_whitelisted_valid(self):
        """run_task ใน gemini ต้อง return True."""
        import app.services.command_queue_service as svc

        with patch("builtins.open", mock_open(read_data=SAMPLE_WHITELIST_YAML)):
            with patch("os.path.exists", return_value=True):
                svc._whitelist_cache = None
                assert svc.is_command_whitelisted("gemini", "run_task") is True

    def test_is_command_whitelisted_invalid(self):
        """delete_all ใน gemini ต้อง return False."""
        import app.services.command_queue_service as svc

        with patch("builtins.open", mock_open(read_data=SAMPLE_WHITELIST_YAML)):
            with patch("os.path.exists", return_value=True):
                svc._whitelist_cache = None
                assert svc.is_command_whitelisted("gemini", "delete_all") is False

    def test_get_allowed_commands_returns_list(self):
        """ต้อง return list ของ command names สำหรับ luma."""
        import app.services.command_queue_service as svc

        with patch("builtins.open", mock_open(read_data=SAMPLE_WHITELIST_YAML)):
            with patch("os.path.exists", return_value=True):
                svc._whitelist_cache = None
                result = svc.get_allowed_commands("luma")

        assert result == ["list_issues"]

    def test_get_allowed_commands_unknown_tool_returns_empty(self):
        """tool ที่ไม่มี ต้อง return []."""
        import app.services.command_queue_service as svc

        with patch("builtins.open", mock_open(read_data=SAMPLE_WHITELIST_YAML)):
            with patch("os.path.exists", return_value=True):
                svc._whitelist_cache = None
                assert svc.get_allowed_commands("nope") == []

    def test_reload_whitelist_clears_cache(self):
        """reload_whitelist() ต้อง clear cache และ reload."""
        import app.services.command_queue_service as svc

        svc._whitelist_cache = {"cached": ["data"]}
        svc._whitelist_raw_cache = {"cached": {"allowed_commands": []}}
        with patch("builtins.open", mock_open(read_data=SAMPLE_WHITELIST_YAML)):
            with patch("os.path.exists", return_value=True):
                svc.reload_whitelist()

        assert "gemini" in svc._whitelist_cache
        assert "cached" not in svc._whitelist_cache

    def test_get_command_whitelist_entry_merges_execution_defaults(self):
        """Entry-specific execution should override defaults while inheriting base config."""
        import app.services.command_queue_service as svc

        with patch(
            "builtins.open", mock_open(read_data=SAMPLE_WHITELIST_WITH_EXECUTION)
        ):
            with patch("os.path.exists", return_value=True):
                svc._whitelist_cache = None
                svc._whitelist_raw_cache = None

                open_file = svc.get_command_whitelist_entry("zed", "open_file")
                run_task = svc.get_command_whitelist_entry("zed", "run_task")

        assert open_file is not None
        assert open_file["allowed_args"] == ["path"]
        assert open_file["execution"]["include_command_name"] is False
        assert open_file["execution"]["path_arg_keys"] == ["path"]

        assert run_task is not None
        assert run_task["allowed_args"] == ["task_name"]
        assert run_task["execution"]["include_command_name"] is True
        assert run_task["execution"]["path_arg_keys"] == []


# ---------------------------------------------------------------------------
# Enqueue tests
# ---------------------------------------------------------------------------


class TestEnqueueCommand:
    """Verify enqueue_command() behavior."""

    @pytest.mark.asyncio
    async def test_enqueue_success(self, mock_redis):
        """Happy path — valid tool + command → queued successfully."""
        import app.services.command_queue_service as svc

        with patch("builtins.open", mock_open(read_data=SAMPLE_WHITELIST_YAML)):
            with patch("os.path.exists", return_value=True):
                svc._whitelist_cache = None

                request = CommandQueueRequest(
                    tool="gemini", command="run_task", args={"task": "summarize"}
                )
                result = await svc.enqueue_command(request, user_id=123, chat_id=456)

        assert isinstance(result, CommandQueueResponse)
        assert result.status == "queued"
        assert result.tool == "gemini"
        assert result.command == "run_task"
        assert result.command_id.startswith("cmd_")
        mock_redis.rpush.assert_called_once()
        mock_redis.set.assert_called_once()  # meta key
        mock_redis.hset.assert_called_once()  # status hash

    @pytest.mark.asyncio
    async def test_enqueue_unknown_tool_raises(self, mock_redis):
        """Unknown tool ต้อง raise ValueError."""
        import app.services.command_queue_service as svc

        with patch("builtins.open", mock_open(read_data=SAMPLE_WHITELIST_YAML)):
            with patch("os.path.exists", return_value=True):
                svc._whitelist_cache = None

                request = CommandQueueRequest(
                    tool="unknown", command="anything"
                )
                with pytest.raises(ValueError, match="Unknown tool"):
                    await svc.enqueue_command(request, user_id=123, chat_id=456)

        mock_redis.rpush.assert_not_called()

    @pytest.mark.asyncio
    async def test_enqueue_non_whitelisted_command_raises(self, mock_redis):
        """Non-whitelisted command ต้อง raise ValueError."""
        import app.services.command_queue_service as svc

        with patch("builtins.open", mock_open(read_data=SAMPLE_WHITELIST_YAML)):
            with patch("os.path.exists", return_value=True):
                svc._whitelist_cache = None

                request = CommandQueueRequest(
                    tool="gemini", command="delete_all"
                )
                with pytest.raises(ValueError, match="not in the whitelist"):
                    await svc.enqueue_command(request, user_id=123, chat_id=456)

        mock_redis.rpush.assert_not_called()

    @pytest.mark.asyncio
    async def test_enqueue_redis_error_propagates(self, mock_redis):
        """Redis error ต้อง propagate ไม่ swallow."""
        import app.services.command_queue_service as svc

        mock_redis.rpush = AsyncMock(side_effect=ConnectionError("Redis down"))

        with patch("builtins.open", mock_open(read_data=SAMPLE_WHITELIST_YAML)):
            with patch("os.path.exists", return_value=True):
                svc._whitelist_cache = None

                request = CommandQueueRequest(
                    tool="gemini", command="run_task"
                )
                with pytest.raises(ConnectionError, match="Redis down"):
                    await svc.enqueue_command(request, user_id=123, chat_id=456)

    @pytest.mark.asyncio
    async def test_enqueue_uses_custom_ttl(self, mock_redis):
        """Custom TTL ต้องถูกส่งไปใน meta key."""
        import app.services.command_queue_service as svc

        with patch("builtins.open", mock_open(read_data=SAMPLE_WHITELIST_YAML)):
            with patch("os.path.exists", return_value=True):
                svc._whitelist_cache = None

                request = CommandQueueRequest(
                    tool="gemini", command="run_task", ttl_seconds=60
                )
                result = await svc.enqueue_command(request, user_id=123, chat_id=456)

        # meta key SET called with ex=60
        mock_redis.set.assert_called_once()
        call_kwargs = mock_redis.set.call_args
        assert call_kwargs.kwargs.get("ex") == 60 or call_kwargs[1].get("ex") == 60


# ---------------------------------------------------------------------------
# Dequeue tests
# ---------------------------------------------------------------------------


class TestDequeueCommand:
    """Verify dequeue_command() behavior."""

    @pytest.mark.asyncio
    async def test_dequeue_returns_payload(self, mock_redis):
        """BLPOP returns data → parsed into CommandPayload."""
        import app.services.command_queue_service as svc

        payload = {
            "command_id": "cmd_abc123",
            "tool": "gemini",
            "command": "run_task",
            "args": {},
            "user_id": 123,
            "chat_id": 456,
            "queued_at": "2026-01-01T00:00:00Z",
            "ttl_seconds": 300,
        }
        mock_redis.blpop = AsyncMock(
            return_value=("akasa:commands:gemini", json.dumps(payload))
        )

        result = await svc.dequeue_command("gemini", timeout=5)

        assert isinstance(result, CommandPayload)
        assert result.command_id == "cmd_abc123"
        assert result.tool == "gemini"

    @pytest.mark.asyncio
    async def test_dequeue_timeout_returns_none(self, mock_redis):
        """BLPOP timeout → returns None."""
        import app.services.command_queue_service as svc

        mock_redis.blpop = AsyncMock(return_value=None)
        result = await svc.dequeue_command("gemini", timeout=5)
        assert result is None

    @pytest.mark.asyncio
    async def test_dequeue_malformed_json_returns_none(self, mock_redis):
        """Invalid JSON ใน queue → returns None (ไม่ crash)."""
        import app.services.command_queue_service as svc

        mock_redis.blpop = AsyncMock(
            return_value=("akasa:commands:gemini", "not-valid-json")
        )
        result = await svc.dequeue_command("gemini")
        assert result is None


# ---------------------------------------------------------------------------
# Rate limiting tests
# ---------------------------------------------------------------------------


class TestRateLimit:
    """Verify per-user rate limiting."""

    @pytest.mark.asyncio
    async def test_rate_limit_first_call_allowed(self, mock_redis):
        """First call → allowed=True, retry_after=0."""
        import app.services.command_queue_service as svc

        mock_redis.get = AsyncMock(return_value=None)  # no existing counter
        allowed, retry = await svc.check_rate_limit(user_id=123)
        assert allowed is True
        assert retry == 0

    @pytest.mark.asyncio
    async def test_rate_limit_within_limit(self, mock_redis):
        """Counter < limit → allowed=True."""
        import app.services.command_queue_service as svc

        mock_redis.get = AsyncMock(return_value="5")  # 5 out of 10 default
        allowed, retry = await svc.check_rate_limit(user_id=123)
        assert allowed is True

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, mock_redis):
        """Counter >= limit → allowed=False with retry_after > 0."""
        import app.services.command_queue_service as svc

        mock_redis.get = AsyncMock(return_value="10")  # at limit
        mock_redis.ttl = AsyncMock(return_value=42)
        allowed, retry = await svc.check_rate_limit(user_id=123)
        assert allowed is False
        assert retry == 42


# ---------------------------------------------------------------------------
# Meta key / TTL tests
# ---------------------------------------------------------------------------


class TestMetaKey:
    """Verify TTL meta key checks."""

    @pytest.mark.asyncio
    async def test_meta_key_alive(self, mock_redis):
        """Meta key exists → True."""
        import app.services.command_queue_service as svc

        mock_redis.exists = AsyncMock(return_value=1)
        assert await svc.is_meta_key_alive("cmd_123") is True

    @pytest.mark.asyncio
    async def test_meta_key_expired(self, mock_redis):
        """Meta key does not exist → False."""
        import app.services.command_queue_service as svc

        mock_redis.exists = AsyncMock(return_value=0)
        assert await svc.is_meta_key_alive("cmd_123") is False


# ---------------------------------------------------------------------------
# Status management tests
# ---------------------------------------------------------------------------


class TestCommandStatus:
    """Verify status get/update operations."""

    @pytest.mark.asyncio
    async def test_get_status_found(self, mock_redis):
        """Known command_id → CommandStatusResponse."""
        import app.services.command_queue_service as svc

        mock_redis.hgetall = AsyncMock(return_value={
            "command_id": "cmd_abc",
            "status": "queued",
            "tool": "gemini",
            "command": "run_task",
            "queued_at": "2026-01-01T00:00:00Z",
            "picked_up_at": "",
            "completed_at": "",
            "result": "",
            "error": "",
        })

        result = await svc.get_command_status("cmd_abc")
        assert isinstance(result, CommandStatusResponse)
        assert result.status == "queued"
        assert result.tool == "gemini"

    @pytest.mark.asyncio
    async def test_get_status_not_found(self, mock_redis):
        """Unknown command_id → None."""
        import app.services.command_queue_service as svc

        mock_redis.hgetall = AsyncMock(return_value={})
        result = await svc.get_command_status("cmd_unknown")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_status_success(self, mock_redis):
        """Update existing command status → True."""
        import app.services.command_queue_service as svc

        mock_redis.exists = AsyncMock(return_value=1)
        result = await svc.update_command_status("cmd_abc", "success", result="done")
        assert result is True
        mock_redis.hset.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_status_not_found(self, mock_redis):
        """Update non-existing command → False."""
        import app.services.command_queue_service as svc

        mock_redis.exists = AsyncMock(return_value=0)
        result = await svc.update_command_status("cmd_nope", "success")
        assert result is False

    @pytest.mark.asyncio
    async def test_update_status_sets_picked_up_at(self, mock_redis):
        """status='picked_up' → picked_up_at ถูก set."""
        import app.services.command_queue_service as svc

        mock_redis.exists = AsyncMock(return_value=1)
        await svc.update_command_status("cmd_abc", "picked_up")

        call_kwargs = mock_redis.hset.call_args.kwargs
        assert "picked_up_at" in call_kwargs["mapping"]

    @pytest.mark.asyncio
    async def test_update_status_sets_completed_at_on_success(self, mock_redis):
        """status='success' → completed_at ถูก set."""
        import app.services.command_queue_service as svc

        mock_redis.exists = AsyncMock(return_value=1)
        await svc.update_command_status("cmd_abc", "success")

        call_kwargs = mock_redis.hset.call_args.kwargs
        assert "completed_at" in call_kwargs["mapping"]

    @pytest.mark.asyncio
    async def test_update_status_truncates_long_result(self, mock_redis):
        """result > 3000 chars ต้องถูก truncate."""
        import app.services.command_queue_service as svc

        mock_redis.exists = AsyncMock(return_value=1)
        long_result = "x" * 5000
        await svc.update_command_status("cmd_abc", "success", result=long_result)

        call_kwargs = mock_redis.hset.call_args.kwargs
        assert len(call_kwargs["mapping"]["result"]) == 3000

    @pytest.mark.asyncio
    async def test_mark_expired(self, mock_redis):
        """mark_command_expired() → status='expired' + meta key deleted."""
        import app.services.command_queue_service as svc

        mock_redis.exists = AsyncMock(return_value=1)
        await svc.mark_command_expired("cmd_abc")

        mock_redis.delete.assert_called_once()


# ---------------------------------------------------------------------------
# Queue monitoring tests
# ---------------------------------------------------------------------------


class TestQueueMonitoring:
    """Verify queue monitoring functions."""

    @pytest.mark.asyncio
    async def test_get_pending_count(self, mock_redis):
        """get_pending_count() → llen return value."""
        import app.services.command_queue_service as svc

        mock_redis.llen = AsyncMock(return_value=5)
        count = await svc.get_pending_count("gemini")
        assert count == 5
        mock_redis.llen.assert_called_once_with("akasa:commands:gemini")
