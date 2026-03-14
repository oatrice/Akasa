"""
Tests for scripts/local_tool_daemon.py
"""

import asyncio
import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

# Import the daemon script
import scripts.local_tool_daemon as daemon


@pytest.fixture
def mock_httpx_post():
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
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
    with patch("scripts.local_tool_daemon.get_redis", new_callable=MagicMock) as mock_get_redis:
        mock_redis_client = AsyncMock()
        mock_get_redis.return_value = mock_redis_client
        yield mock_redis_client


@pytest.mark.asyncio
async def test_daemon_success_flow(mock_redis, mock_subprocess, mock_httpx_post):
    """Test full flow: Poll -> Check TTL -> Execute -> Report Result"""
    # 1. Setup mock data
    command_payload = {
        "command_id": "cmd_123",
        "tool": "gemini",
        "command": "run_task",
        "args": {"task": "test it"},
        "user_id": 1
    }
    
    # Mock BRPOP to return our item on first call, then block forever or return None
    # returning None will break the loop if handled
    mock_redis.brpop.side_effect = [
        (b"akasa:commands:gemini", json.dumps(command_payload).encode("utf-8")),
        None # to break the loop for testing
    ]
    
    # Mock TTL check to be alive
    mock_redis.exists.return_value = 1
    
    # 2. Run the daemon poll loop for a single iteration (or run and then cancel)
    task = asyncio.create_task(daemon.poll_queue("gemini", timeout=1))
    
    # Let it run briefly
    await asyncio.sleep(0.1)
    task.cancel()
    
    # 3. Assertions
    # It should have checked the meta key
    mock_redis.exists.assert_called_with("akasa:commands:meta:cmd_123")
    
    # It should have executed the command based on the whitelist config
    mock_subprocess.assert_called_once()
    assert "run_task" in mock_subprocess.call_args[0][0] # checking the executable
    
    # It should have reported the result back
    mock_httpx_post.assert_called_once()
    url = mock_httpx_post.call_args[0][0]
    payload = mock_httpx_post.call_args[1]["json"]
    
    assert "cmd_123/result" in url
    assert payload["status"] == "success"
    assert "mock stdout" in payload["output"]


@pytest.mark.asyncio
async def test_daemon_expired_command_skip(mock_redis, mock_subprocess, mock_httpx_post):
    """If the TTL meta key is gone, skip execution entirely."""
    command_payload = {
        "command_id": "cmd_expired",
        "tool": "gemini",
        "command": "run_task",
        "args": {},
        "user_id": 1
    }
    
    mock_redis.brpop.side_effect = [
        (b"akasa:commands:gemini", json.dumps(command_payload).encode("utf-8")),
        None
    ]
    
    # Mock TTL check to be expired (0)
    mock_redis.exists.return_value = 0
    
    task = asyncio.create_task(daemon.poll_queue("gemini", timeout=1))
    await asyncio.sleep(0.1)
    task.cancel()
    
    # Should NOT have executed or reported anything
    mock_subprocess.assert_not_called()
    mock_httpx_post.assert_not_called()


@pytest.mark.asyncio
async def test_daemon_execution_failure(mock_redis, mock_subprocess, mock_httpx_post):
    """If subprocess returns non-zero, report error."""
    command_payload = {
        "command_id": "cmd_fail",
        "tool": "gemini",
        "command": "run_task",
        "args": {},
        "user_id": 1
    }
    
    mock_redis.brpop.side_effect = [
        (b"akasa:commands:gemini", json.dumps(command_payload).encode("utf-8")),
        None
    ]
    mock_redis.exists.return_value = 1
    
    # Make subprocess fail
    mock_subprocess.return_value.returncode = 1
    mock_subprocess.return_value.communicate.return_value = (b"", b"Something went wrong")
    
    task = asyncio.create_task(daemon.poll_queue("gemini", timeout=1))
    await asyncio.sleep(0.1)
    task.cancel()
    
    # Should report failed
    mock_httpx_post.assert_called_once()
    payload = mock_httpx_post.call_args[1]["json"]
    
    assert payload["status"] == "failed"
    assert "Something went wrong" in payload["output"]
    assert payload["exit_code"] == 1
