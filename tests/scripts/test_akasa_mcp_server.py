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

        with patch("scripts.akasa_mcp_server.httpx.AsyncClient", return_value=mock_client), \
             patch("scripts.akasa_mcp_server.AKASA_CHAT_ID", "12345"):
            result = await request_remote_approval(
                command="npm install",
                cwd="/Users/dev/project",
                description="Installing dependencies"
            )

        assert result["status"] == "allowed"
        assert result["request_id"] == "req-123"
        
        # Verify that session_id was sent in the metadata payload
        post_kwargs = mock_client.post.call_args.kwargs
        metadata = post_kwargs["json"]["metadata"]
        assert "session_id" in metadata
        assert metadata["session_id"] is not None

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

        with patch("scripts.akasa_mcp_server.httpx.AsyncClient", return_value=mock_client), \
             patch("scripts.akasa_mcp_server.AKASA_CHAT_ID", "12345"):
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
             patch("scripts.akasa_mcp_server.AKASA_CHAT_ID", "12345"), \
             patch("scripts.akasa_mcp_server.MAX_POLL_ATTEMPTS", 2), \
             patch("scripts.akasa_mcp_server.POLL_INTERVAL", 0.01):
            result = await request_remote_approval(
                command="deploy --prod",
                cwd="/app"
            )

        assert result["status"] == "timeout"


class TestHandleRpc:
    """ทดสอบ handle_rpc JSON-RPC protocol"""

    @pytest.mark.asyncio
    async def test_handle_rpc_initialize(self):
        """ทดสอบ initialize method คืน server info"""
        from scripts.akasa_mcp_server import handle_rpc
        result = await handle_rpc({"id": 1, "method": "initialize", "params": {}})
        data = json.loads(result)
        assert data["id"] == 1
        assert data["result"]["protocolVersion"] == "2024-11-05"
        assert data["result"]["serverInfo"]["name"] == "akasa-remote-approval"

    @pytest.mark.asyncio
    async def test_handle_rpc_tools_list(self):
        """ทดสอบ tools/list คืน tool definitions"""
        from scripts.akasa_mcp_server import handle_rpc
        result = await handle_rpc({"id": 2, "method": "tools/list", "params": {}})
        data = json.loads(result)
        assert len(data["result"]["tools"]) == 1
        assert data["result"]["tools"][0]["name"] == "request_remote_approval"

    @pytest.mark.asyncio
    async def test_handle_rpc_unknown_method(self):
        """ทดสอบ unknown method คืน JSON-RPC error"""
        from scripts.akasa_mcp_server import handle_rpc
        result = await handle_rpc({"id": 3, "method": "nonexistent", "params": {}})
        data = json.loads(result)
        assert "error" in data
        assert data["error"]["code"] == -32601

    @pytest.mark.asyncio
    async def test_handle_rpc_tool_call_error(self):
        """ทดสอบ tool call ที่เกิด exception คืน isError=True (MCP spec)"""
        from scripts.akasa_mcp_server import handle_rpc
        with patch("scripts.akasa_mcp_server.request_remote_approval",
                    side_effect=Exception("Connection failed")):
            result = await handle_rpc({
                "id": 4, "method": "tools/call",
                "params": {"name": "request_remote_approval",
                           "arguments": {"command": "ls", "cwd": "."}}
            })
        data = json.loads(result)
        assert data["result"]["isError"] is True
        assert "Connection failed" in data["result"]["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_handle_rpc_unknown_tool(self):
        """ทดสอบ unknown tool คืน JSON-RPC error"""
        from scripts.akasa_mcp_server import handle_rpc
        result = await handle_rpc({
            "id": 5, "method": "tools/call",
            "params": {"name": "nonexistent_tool", "arguments": {}}
        })
        data = json.loads(result)
        assert "error" in data
        assert data["error"]["code"] == -32601

    @pytest.mark.asyncio
    async def test_handle_rpc_notifications_initialized(self):
        """ทดสอบ notifications/initialized คืน None (ไม่ต้อง response)"""
        from scripts.akasa_mcp_server import handle_rpc
        result = await handle_rpc({"method": "notifications/initialized", "params": {}})
        assert result is None


class TestChatIdValidation:
    """ทดสอบ AKASA_CHAT_ID validation"""

    @pytest.mark.asyncio
    async def test_request_remote_approval_no_chat_id(self):
        """ถ้า AKASA_CHAT_ID ว่าง ต้อง raise ValueError"""
        from scripts.akasa_mcp_server import request_remote_approval
        with patch("scripts.akasa_mcp_server.AKASA_CHAT_ID", ""):
            with pytest.raises(ValueError, match="AKASA_CHAT_ID"):
                await request_remote_approval(command="ls", cwd=".")
