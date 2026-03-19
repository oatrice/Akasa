"""
Tests for scripts/local_tool_daemon.py
"""

import asyncio
import json
from contextlib import suppress
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import scripts.local_tool_daemon as daemon


@pytest.fixture
def mock_httpx_post():
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_subprocess():
    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"mock stdout", b"mock stderr")
        mock_process.returncode = 0
        mock_exec.return_value = mock_process
        yield mock_exec


@pytest.fixture
def mock_redis():
    with patch("scripts.local_tool_daemon.get_redis", new_callable=MagicMock) as mock_get:
        redis_client = AsyncMock()
        mock_get.return_value = redis_client
        yield redis_client


@pytest.fixture
def mock_status_tracking():
    with patch(
        "scripts.local_tool_daemon.update_command_status", new_callable=AsyncMock
    ) as mock_update:
        with patch(
            "scripts.local_tool_daemon.mark_command_expired", new_callable=AsyncMock
        ) as mock_expire:
            yield mock_update, mock_expire


@pytest.mark.asyncio
async def test_daemon_success_flow(
    mock_redis, mock_subprocess, mock_httpx_post, mock_status_tracking
):
    """Poll -> check TTL -> execute -> report success with duration_seconds."""
    mock_update, _ = mock_status_tracking
    command_payload = {
        "command_id": "cmd_123",
        "tool": "gemini",
        "command": "run_task",
        "args": {"task": "test it"},
        "user_id": 1,
    }

    mock_redis.brpop.side_effect = [
        (b"akasa:commands:gemini", json.dumps(command_payload).encode("utf-8")),
        None,
    ]
    mock_redis.exists.return_value = 1

    task = asyncio.create_task(daemon.poll_queue("gemini", timeout=1))
    await asyncio.sleep(0.1)
    task.cancel()

    mock_redis.exists.assert_called_with("akasa:cmd_meta:cmd_123")

    mock_subprocess.assert_called_once()
    cli_args = mock_subprocess.call_args[0]
    assert cli_args[0] == "gemini"
    assert "-p" in cli_args
    assert "test it" in cli_args[-1]

    mock_httpx_post.assert_called_once()
    payload = mock_httpx_post.call_args[1]["json"]
    assert payload["status"] == "success"
    assert "mock stdout" in payload["output"]
    assert "duration_seconds" in payload

    status_updates = []
    for call in mock_update.call_args_list:
        if "status" in call.kwargs:
            status_updates.append(call.kwargs["status"])
        elif len(call.args) >= 2:
            status_updates.append(call.args[1])

    assert status_updates[:2] == ["picked_up", "running"]


@pytest.mark.asyncio
async def test_daemon_logs_dequeued_command(
    mock_redis, mock_subprocess, mock_httpx_post, mock_status_tracking, caplog
):
    """Daemon should log each command as soon as it is popped from Redis."""
    command_payload = {
        "command_id": "cmd_log_me",
        "tool": "gemini",
        "command": "check_status",
        "args": {},
        "user_id": 1,
        "queued_at": "1970-01-01T00:01:39.500000Z",
    }

    mock_redis.brpop.side_effect = [
        (b"akasa:commands:gemini", json.dumps(command_payload).encode("utf-8")),
        None,
    ]
    mock_redis.exists.return_value = 1

    with caplog.at_level("INFO"):
        task = asyncio.create_task(daemon.poll_queue("gemini", timeout=1))
        await asyncio.sleep(0.1)
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

    assert "DEQUEUED cmd_log_me" in caplog.text
    assert "tool=gemini" in caplog.text
    assert "command=check_status" in caplog.text
    assert "queue_wait_ms=" in caplog.text
    assert "COMPLETED cmd_log_me" in caplog.text
    assert "run_duration_ms=" in caplog.text
    assert "total_latency_ms=" in caplog.text


@pytest.mark.asyncio
async def test_daemon_expired_command_marks_expired(
    mock_redis, mock_subprocess, mock_httpx_post, mock_status_tracking
):
    """Missing TTL meta key should mark command expired and skip execution."""
    _, mock_expire = mock_status_tracking
    command_payload = {
        "command_id": "cmd_expired",
        "tool": "gemini",
        "command": "run_task",
        "args": {"task": "noop"},
        "user_id": 1,
    }

    mock_redis.brpop.side_effect = [
        (b"akasa:commands:gemini", json.dumps(command_payload).encode("utf-8")),
        None,
    ]
    mock_redis.exists.return_value = 0

    task = asyncio.create_task(daemon.poll_queue("gemini", timeout=1))
    await asyncio.sleep(0.1)
    task.cancel()

    mock_subprocess.assert_not_called()
    mock_httpx_post.assert_not_called()
    mock_expire.assert_awaited_once_with("cmd_expired")


@pytest.mark.asyncio
async def test_daemon_execution_failure_reports_failed(
    mock_redis, mock_subprocess, mock_httpx_post, mock_status_tracking
):
    """Non-zero CLI exit code should report failed with stderr output."""
    command_payload = {
        "command_id": "cmd_fail",
        "tool": "gemini",
        "command": "run_task",
        "args": {"task": "bad"},
        "user_id": 1,
    }

    mock_redis.brpop.side_effect = [
        (b"akasa:commands:gemini", json.dumps(command_payload).encode("utf-8")),
        None,
    ]
    mock_redis.exists.return_value = 1

    mock_subprocess.return_value.returncode = 1
    mock_subprocess.return_value.communicate.return_value = (
        b"",
        b"Something went wrong",
    )

    task = asyncio.create_task(daemon.poll_queue("gemini", timeout=1))
    await asyncio.sleep(0.1)
    task.cancel()

    payload = mock_httpx_post.call_args[1]["json"]
    assert payload["status"] == "failed"
    assert "Something went wrong" in payload["output"]
    assert payload["exit_code"] == 1


@pytest.mark.asyncio
async def test_open_file_accepts_line_col_path():
    """Path validation should accept file:line:column for allowed roots."""
    entry = {
        "tool": "zed",
        "command": "open_file",
        "allowed_args": ["path"],
        "execution": {
            "path_arg_keys": ["path"],
            "allowed_paths": [str(daemon._PROJECT_ROOT)],
        },
    }
    args = {"path": "docs/plan.md:10:5"}
    assert daemon._validate_args(entry, args) is None


def test_build_cli_command_places_global_flags_before_command():
    """Global flags should be rendered before command and internal args skipped."""
    cmd = daemon._build_cli_command(
        executable="gemini",
        command="check_status",
        args={
            "model": "gemini-2.5-flash",
            "fallback_model": "gemini-2.5-flash-lite",
        },
        execution_cfg={
            "prompt_template": "Status check only.",
            "global_flag_args": ["model"],
            "internal_args": ["fallback_model"],
            "flag_aliases": {"model": "-m"},
        },
    )

    assert cmd == ["gemini", "-m", "gemini-2.5-flash", "-p", "Status check only."]


def test_build_cli_command_uses_task_as_headless_prompt():
    """run_task should invoke Gemini in headless prompt mode instead of subcommands."""
    cmd = daemon._build_cli_command(
        executable="gemini",
        command="run_task",
        args={
            "task": "Summarize this repository.",
            "pr_number": 42,
            "branch": "main",
            "model": "gemini-2.5-pro",
        },
        execution_cfg={
            "prompt_arg_key": "task",
            "prompt_context_keys": ["pr_number", "branch"],
            "global_flag_args": ["model"],
            "flag_aliases": {"model": "-m"},
        },
    )

    assert cmd[0:3] == ["gemini", "-m", "gemini-2.5-pro"]
    assert cmd[3] == "-p"
    assert "Summarize this repository." in cmd[4]
    assert "PR Number: 42" in cmd[4]
    assert "Branch: main" in cmd[4]


@pytest.mark.asyncio
async def test_execute_command_retries_gemini_with_fallback_on_quota_error():
    """Gemini CLI should retry once with fallback_model when quota is exhausted."""
    quota_output = (
        "Loaded cached credentials.\n"
        "TerminalQuotaError: You have exhausted your capacity on this model. "
        "Your quota will reset after 18m30s."
    )
    whitelist_entry = {
        "tool": "gemini",
        "command": "check_status",
        "allowed_args": ["model", "fallback_model"],
        "execution": {
            "type": "cli",
            "executable": "gemini",
            "prompt_template": "Status check only.",
            "global_flag_args": ["model"],
            "internal_args": ["fallback_model"],
            "flag_aliases": {"model": "-m"},
        },
    }

    with patch(
        "scripts.local_tool_daemon.get_command_whitelist_entry",
        return_value=whitelist_entry,
    ):
        with patch(
            "scripts.local_tool_daemon._execute_cli",
            new_callable=AsyncMock,
            side_effect=[
                (1, quota_output),
                (0, "fallback command succeeded"),
            ],
        ) as mock_exec:
            exit_code, output = await daemon.execute_command(
                command_id="cmd_retry",
                tool="gemini",
                command="check_status",
                args={"model": "pro", "fallback_model": "flash"},
            )

    assert exit_code == 0
    assert "Primary model: gemini-2.5-pro" in output
    assert "Retried with fallback model: gemini-2.5-flash" in output
    assert "fallback command succeeded" in output

    first_call = mock_exec.await_args_list[0]
    second_call = mock_exec.await_args_list[1]
    assert first_call.args[2]["model"] == "gemini-2.5-pro"
    assert first_call.args[2]["fallback_model"] == "gemini-2.5-flash"
    assert second_call.args[2]["model"] == "gemini-2.5-flash"
    assert "fallback_model" not in second_call.args[2]


@pytest.mark.asyncio
async def test_http_handler_retries_then_succeeds():
    """HTTP handler should retry retryable statuses and eventually succeed."""
    retry_response = MagicMock(status_code=503, text="Service unavailable")
    success_response = MagicMock(status_code=200, text='{"ok": true}')

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_request.side_effect = [retry_response, success_response]

        status, output = await daemon._execute_http(
            command_id="cmd_http_1",
            tool="windsurf",
            command="execute_code",
            args={"code": "print('hello')"},
            execution_cfg={
                "endpoint": "http://localhost:9999/execute",
                "method": "POST",
                "retries": 1,
                "backoff_seconds": 0.0,
                "retry_statuses": [503],
                "allowed_hosts": ["localhost"],
                "payload_mode": "envelope",
                "timeout_seconds": 5,
            },
        )

    assert status == 0
    assert '"ok": true' in output
    assert mock_request.await_count == 2


@pytest.mark.asyncio
async def test_http_handler_rejects_non_local_host():
    """HTTP handler should reject endpoints that are outside allowed hosts."""
    status, output = await daemon._execute_http(
        command_id="cmd_http_2",
        tool="windsurf",
        command="open_file",
        args={"path": "README.md"},
        execution_cfg={
            "endpoint": "http://example.com/execute",
            "method": "POST",
            "retries": 1,
            "allowed_hosts": ["localhost", "127.0.0.1", "::1"],
        },
    )

    assert status == -1
    assert "not in allowed_hosts" in output


@pytest.mark.asyncio
async def test_mcp_handler_returns_not_found_for_missing_server():
    """MCP handler should return a clear error when server command is missing."""
    status, output = await daemon._execute_mcp(
        command="notify_task_complete",
        args={"project": "Akasa", "task": "demo", "status": "success"},
        execution_cfg={
            "server_command": ["/definitely/not/found/python3"],
            "retries": 0,
            "timeout_seconds": 3,
        },
    )

    assert status == -1
    assert "not found" in output.lower()


@pytest.mark.asyncio
async def test_poll_queue_falls_back_to_redis_status_when_report_fails(
    mock_redis, mock_status_tracking
):
    """If API reporting fails, daemon should still update status in Redis."""
    mock_update, _ = mock_status_tracking
    payload = {
        "command_id": "cmd_status_fallback",
        "tool": "gemini",
        "command": "run_task",
        "args": {"task": "x"},
        "user_id": 1,
    }

    async def brpop_side_effect(*_args, **_kwargs):
        if not hasattr(brpop_side_effect, "done"):
            brpop_side_effect.done = True
            return (b"akasa:commands:gemini", json.dumps(payload).encode("utf-8"))
        await asyncio.sleep(0.01)
        return None

    mock_redis.brpop.side_effect = brpop_side_effect
    mock_redis.exists.return_value = 1

    with patch("scripts.local_tool_daemon.execute_command", new_callable=AsyncMock) as mock_exec:
        with patch("scripts.local_tool_daemon.report_result", new_callable=AsyncMock) as mock_report:
            mock_exec.return_value = (0, "ok")
            mock_report.return_value = False

            task = asyncio.create_task(daemon.poll_queue("gemini", timeout=1))
            await asyncio.sleep(0.1)
            task.cancel()

    success_updates = [
        call
        for call in mock_update.call_args_list
        if (
            ("status" in call.kwargs and call.kwargs["status"] == "success")
            or (len(call.args) >= 2 and call.args[1] == "success")
        )
    ]
    assert len(success_updates) >= 1
