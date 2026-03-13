"""
🟥 RED: ทดสอบ AkasaRemoteApproval client ที่ใช้สำหรับ MCP Server
ทดสอบ flow: send request → poll for result → return status
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json


class TestAkasaRemoteApproval:
    """ทดสอบ core logic ของ MCP Server (request_remote_approval)"""

    @pytest.mark.asyncio
    async def test_request_remote_approval_allowed(self):
        """ส่ง request → user กด Allow → คืน allowed"""
        from scripts.akasa_mcp_server import request_remote_approval

        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {
            "request_id": "req-123",
            "status": "pending"
        }
        mock_post_response.raise_for_status = MagicMock()

        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "request_id": "req-123",
            "status": "allowed",
            "session_permission": False
        }
        mock_get_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_post_response
        mock_client.get.return_value = mock_get_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("scripts.akasa_mcp_server.httpx.AsyncClient", return_value=mock_client):
            result = await request_remote_approval(
                command="npm install",
                cwd="/Users/dev/project",
                description="Installing dependencies"
            )

        assert result["status"] == "allowed"
        assert result["request_id"] == "req-123"

    @pytest.mark.asyncio
    async def test_request_remote_approval_denied(self):
        """ส่ง request → user กด Deny → คืน denied"""
        from scripts.akasa_mcp_server import request_remote_approval

        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {
            "request_id": "req-456",
            "status": "pending"
        }
        mock_post_response.raise_for_status = MagicMock()

        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "request_id": "req-456",
            "status": "denied",
            "session_permission": False
        }
        mock_get_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_post_response
        mock_client.get.return_value = mock_get_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("scripts.akasa_mcp_server.httpx.AsyncClient", return_value=mock_client):
            result = await request_remote_approval(
                command="rm -rf /tmp/data",
                cwd="/tmp"
            )

        assert result["status"] == "denied"

    @pytest.mark.asyncio
    async def test_request_remote_approval_timeout(self):
        """ส่ง request → user ไม่ตอบ → timeout → คืน timeout"""
        from scripts.akasa_mcp_server import request_remote_approval

        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {
            "request_id": "req-789",
            "status": "pending"
        }
        mock_post_response.raise_for_status = MagicMock()

        # GET ยังคง pending ตลอด
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "request_id": "req-789",
            "status": "pending",
            "session_permission": False
        }
        mock_get_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_post_response
        mock_client.get.return_value = mock_get_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("scripts.akasa_mcp_server.httpx.AsyncClient", return_value=mock_client), \
             patch("scripts.akasa_mcp_server.MAX_POLL_ATTEMPTS", 2), \
             patch("scripts.akasa_mcp_server.POLL_INTERVAL", 0.01):
            result = await request_remote_approval(
                command="deploy --prod",
                cwd="/app"
            )

        assert result["status"] == "timeout"
