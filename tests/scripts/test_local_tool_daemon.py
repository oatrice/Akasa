"""
Tests for scripts/local_tool_daemon.py
"""

import asyncio
import json
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
    assert mock_subprocess.call_args[0][0] == "gemini"
    assert mock_subprocess.call_args[0][1] == "run_task"

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
