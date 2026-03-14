"""
🟥 RED: ทดสอบ AkasaRemoteApproval client ที่ใช้สำหรับ MCP Server
ทดสอบ flow: send request → poll for result → return status
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


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
            "status": "pending",
        }
        mock_post_response.raise_for_status = MagicMock()

        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "request_id": "req-123",
            "status": "allowed",
            "session_permission": False,
        }
        mock_get_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_post_response
        mock_client.get.return_value = mock_get_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "scripts.akasa_mcp_server.httpx.AsyncClient", return_value=mock_client
            ),
            patch("scripts.akasa_mcp_server.AKASA_CHAT_ID", "12345"),
        ):
            result = await request_remote_approval(
                command="npm install",
                cwd="/Users/dev/project",
                description="Installing dependencies",
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
            "status": "pending",
        }
        mock_post_response.raise_for_status = MagicMock()

        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "request_id": "req-456",
            "status": "denied",
            "session_permission": False,
        }
        mock_get_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_post_response
        mock_client.get.return_value = mock_get_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "scripts.akasa_mcp_server.httpx.AsyncClient", return_value=mock_client
            ),
            patch("scripts.akasa_mcp_server.AKASA_CHAT_ID", "12345"),
        ):
            result = await request_remote_approval(
                command="rm -rf /tmp/data", cwd="/tmp"
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
            "status": "pending",
        }
        mock_post_response.raise_for_status = MagicMock()

        # GET ยังคง pending ตลอด
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "request_id": "req-789",
            "status": "pending",
            "session_permission": False,
        }
        mock_get_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_post_response
        mock_client.get.return_value = mock_get_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "scripts.akasa_mcp_server.httpx.AsyncClient", return_value=mock_client
            ),
            patch("scripts.akasa_mcp_server.AKASA_CHAT_ID", "12345"),
            patch("scripts.akasa_mcp_server.MAX_POLL_ATTEMPTS", 2),
            patch("scripts.akasa_mcp_server.POLL_INTERVAL", 0.01),
        ):
            result = await request_remote_approval(command="deploy --prod", cwd="/app")

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
        """ทดสอบ tools/list คืน tool definitions ทั้งหมด 3 tools"""
        from scripts.akasa_mcp_server import handle_rpc

        result = await handle_rpc({"id": 2, "method": "tools/list", "params": {}})
        data = json.loads(result)
        assert len(data["result"]["tools"]) == 3
        tool_names = [t["name"] for t in data["result"]["tools"]]
        assert "request_remote_approval" in tool_names
        assert "notify_task_complete" in tool_names
        assert "notify_pending_review" in tool_names

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

        with patch(
            "scripts.akasa_mcp_server.request_remote_approval",
            side_effect=Exception("Connection failed"),
        ):
            result = await handle_rpc(
                {
                    "id": 4,
                    "method": "tools/call",
                    "params": {
                        "name": "request_remote_approval",
                        "arguments": {"command": "ls", "cwd": "."},
                    },
                }
            )
        data = json.loads(result)
        assert data["result"]["isError"] is True
        assert "Connection failed" in data["result"]["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_handle_rpc_unknown_tool(self):
        """ทดสอบ unknown tool คืน JSON-RPC error"""
        from scripts.akasa_mcp_server import handle_rpc

        result = await handle_rpc(
            {
                "id": 5,
                "method": "tools/call",
                "params": {"name": "nonexistent_tool", "arguments": {}},
            }
        )
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

    @pytest.mark.asyncio
    async def test_notify_task_complete_no_chat_id(self):
        """notify_task_complete ต้อง raise ValueError ถ้า AKASA_CHAT_ID ว่าง"""
        from scripts.akasa_mcp_server import notify_task_complete

        with patch("scripts.akasa_mcp_server.AKASA_CHAT_ID", ""):
            with pytest.raises(ValueError, match="AKASA_CHAT_ID"):
                await notify_task_complete(
                    project="Akasa",
                    task="Refactor Redis",
                    status="success",
                )


class TestNotifyTaskComplete:
    """ทดสอบ notify_task_complete function และ MCP tool handler"""

    @pytest.mark.asyncio
    async def test_notify_task_complete_success(self):
        """Happy path: ส่ง POST ไปยัง /api/v1/notifications/task-complete และคืน delivered=True"""
        from scripts.akasa_mcp_server import notify_task_complete

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "delivered": True,
            "timestamp": "2026-03-13T10:00:00+00:00",
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "scripts.akasa_mcp_server.httpx.AsyncClient", return_value=mock_client
            ),
            patch("scripts.akasa_mcp_server.AKASA_CHAT_ID", "6346467495"),
            patch("scripts.akasa_mcp_server.AKASA_API_KEY", "test-key"),
            patch("scripts.akasa_mcp_server.AKASA_API_URL", "http://localhost:8000"),
        ):
            result = await notify_task_complete(
                project="Akasa",
                task="Refactor Redis Service",
                status="success",
                duration="5m 20s",
            )

        assert result["delivered"] is True

        # Verify correct endpoint and payload were used
        post_kwargs = mock_client.post.call_args.kwargs
        assert post_kwargs["json"]["project"] == "Akasa"
        assert post_kwargs["json"]["task"] == "Refactor Redis Service"
        assert post_kwargs["json"]["status"] == "success"
        assert post_kwargs["json"]["duration"] == "5m 20s"
        assert post_kwargs["json"]["chat_id"] == "6346467495"
        assert post_kwargs["headers"]["X-Akasa-API-Key"] == "test-key"
        assert (
            "api/v1/notifications/task-complete" in mock_client.post.call_args.args[0]
        )

    @pytest.mark.asyncio
    async def test_notify_task_complete_optional_fields_excluded_when_none(self):
        """Fields ที่ไม่ได้ระบุ (duration, message, link) ต้องไม่ปรากฏใน payload"""
        from scripts.akasa_mcp_server import notify_task_complete

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "delivered": True,
            "timestamp": "2026-03-13T10:00:00+00:00",
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "scripts.akasa_mcp_server.httpx.AsyncClient", return_value=mock_client
            ),
            patch("scripts.akasa_mcp_server.AKASA_CHAT_ID", "6346467495"),
        ):
            await notify_task_complete(
                project="Akasa",
                task="Minimal task",
                status="failure",
                # No duration, message, or link
            )

        payload = mock_client.post.call_args.kwargs["json"]
        assert "duration" not in payload
        assert "message" not in payload
        assert "link" not in payload

    @pytest.mark.asyncio
    async def test_notify_task_complete_includes_optional_fields(self):
        """Fields ที่ระบุ (message, link) ต้องถูกรวมใน payload"""
        from scripts.akasa_mcp_server import notify_task_complete

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "delivered": True,
            "timestamp": "2026-03-13T10:00:00+00:00",
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "scripts.akasa_mcp_server.httpx.AsyncClient", return_value=mock_client
            ),
            patch("scripts.akasa_mcp_server.AKASA_CHAT_ID", "6346467495"),
        ):
            await notify_task_complete(
                project="Akasa",
                task="Create PR",
                status="success",
                message="PR #42 created with 3 commits",
                link="https://github.com/oatrice/Akasa/pull/42",
            )

        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["message"] == "PR #42 created with 3 commits"
        assert payload["link"] == "https://github.com/oatrice/Akasa/pull/42"

    @pytest.mark.asyncio
    async def test_handle_rpc_notify_task_complete_delivered(self):
        """tools/call notify_task_complete → delivered=True → ข้อความสำเร็จ"""
        from scripts.akasa_mcp_server import handle_rpc

        with patch(
            "scripts.akasa_mcp_server.notify_task_complete",
            new_callable=AsyncMock,
            return_value={"delivered": True, "timestamp": "2026-03-13T10:00:00+00:00"},
        ):
            result = await handle_rpc(
                {
                    "id": 10,
                    "method": "tools/call",
                    "params": {
                        "name": "notify_task_complete",
                        "arguments": {
                            "project": "Akasa",
                            "task": "Refactor Redis",
                            "status": "success",
                            "duration": "3m 10s",
                        },
                    },
                }
            )

        data = json.loads(result)
        assert (
            "isError" not in data["result"] or data["result"].get("isError") is not True
        )
        assert "sent successfully" in data["result"]["content"][0]["text"].lower()

    @pytest.mark.asyncio
    async def test_handle_rpc_notify_task_complete_not_delivered(self):
        """tools/call notify_task_complete → delivered=False → ข้อความเตือน"""
        from scripts.akasa_mcp_server import handle_rpc

        with patch(
            "scripts.akasa_mcp_server.notify_task_complete",
            new_callable=AsyncMock,
            return_value={"delivered": False, "timestamp": "2026-03-13T10:00:00+00:00"},
        ):
            result = await handle_rpc(
                {
                    "id": 11,
                    "method": "tools/call",
                    "params": {
                        "name": "notify_task_complete",
                        "arguments": {
                            "project": "Akasa",
                            "task": "Deploy",
                            "status": "failure",
                        },
                    },
                }
            )

        data = json.loads(result)
        assert (
            "isError" not in data["result"] or data["result"].get("isError") is not True
        )
        assert "could not be confirmed" in data["result"]["content"][0]["text"].lower()

    @pytest.mark.asyncio
    async def test_handle_rpc_notify_task_complete_error(self):
        """tools/call notify_task_complete → exception → isError=True"""
        from scripts.akasa_mcp_server import handle_rpc

        with patch(
            "scripts.akasa_mcp_server.notify_task_complete",
            new_callable=AsyncMock,
            side_effect=Exception("Backend unreachable"),
        ):
            result = await handle_rpc(
                {
                    "id": 12,
                    "method": "tools/call",
                    "params": {
                        "name": "notify_task_complete",
                        "arguments": {
                            "project": "Akasa",
                            "task": "Some task",
                            "status": "success",
                        },
                    },
                }
            )

        data = json.loads(result)
        assert data["result"]["isError"] is True
        assert "Backend unreachable" in data["result"]["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_handle_rpc_notify_task_complete_tool_schema(self):
        """ตรวจสอบว่า notify_task_complete tool มี schema ที่ถูกต้อง"""
        from scripts.akasa_mcp_server import handle_rpc

        result = await handle_rpc({"id": 20, "method": "tools/list", "params": {}})
        data = json.loads(result)

        notify_tool = next(
            (t for t in data["result"]["tools"] if t["name"] == "notify_task_complete"),
            None,
        )
        assert notify_tool is not None, (
            "notify_task_complete tool not found in tools/list"
        )

        schema = notify_tool["inputSchema"]
        required_fields = schema["required"]
        assert "project" in required_fields
        assert "task" in required_fields
        assert "status" in required_fields

        properties = schema["properties"]
        assert "duration" in properties
        assert "message" in properties
        assert "link" in properties
        assert "retry_count" in properties
        assert "max_retries" in properties

        # status field ต้องมี enum ครบ 5 ค่า
        status_enum = properties["status"].get("enum", [])
        assert "success" in status_enum
        assert "failure" in status_enum
        assert "partial" in status_enum
        assert "retrying" in status_enum
        assert "limit_reached" in status_enum


class TestNotifyTaskCompleteRetry:
    """ทดสอบ retry statuses: retrying และ limit_reached"""

    @pytest.mark.asyncio
    async def test_notify_task_complete_retrying_with_counts(self):
        """notify_task_complete ส่ง retry_count/max_retries ไปใน payload เมื่อ status=retrying"""
        from scripts.akasa_mcp_server import notify_task_complete

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "delivered": True,
            "timestamp": "2026-03-13T10:00:00+00:00",
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "scripts.akasa_mcp_server.httpx.AsyncClient", return_value=mock_client
            ),
            patch("scripts.akasa_mcp_server.AKASA_CHAT_ID", "6346467495"),
        ):
            result = await notify_task_complete(
                project="Akasa",
                task="Deploy to production",
                status="retrying",
                message="Docker daemon not responding",
                retry_count=2,
                max_retries=3,
            )

        assert result["delivered"] is True
        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["status"] == "retrying"
        assert payload["retry_count"] == 2
        assert payload["max_retries"] == 3
        assert payload["message"] == "Docker daemon not responding"

    @pytest.mark.asyncio
    async def test_notify_task_complete_limit_reached_with_max(self):
        """notify_task_complete ส่ง max_retries ไปใน payload เมื่อ status=limit_reached"""
        from scripts.akasa_mcp_server import notify_task_complete

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "delivered": True,
            "timestamp": "2026-03-13T10:00:00+00:00",
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "scripts.akasa_mcp_server.httpx.AsyncClient", return_value=mock_client
            ),
            patch("scripts.akasa_mcp_server.AKASA_CHAT_ID", "6346467495"),
        ):
            result = await notify_task_complete(
                project="Akasa",
                task="Deploy to production",
                status="limit_reached",
                message="Gave up after 3 attempts",
                max_retries=3,
            )

        assert result["delivered"] is True
        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["status"] == "limit_reached"
        assert payload["max_retries"] == 3
        assert "retry_count" not in payload  # ไม่ได้ส่ง → ไม่ปรากฏใน payload

    @pytest.mark.asyncio
    async def test_notify_task_complete_retry_fields_excluded_when_none(self):
        """retry_count/max_retries ต้องไม่ปรากฏใน payload เมื่อไม่ได้ระบุ"""
        from scripts.akasa_mcp_server import notify_task_complete

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "delivered": True,
            "timestamp": "2026-03-13T10:00:00+00:00",
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "scripts.akasa_mcp_server.httpx.AsyncClient", return_value=mock_client
            ),
            patch("scripts.akasa_mcp_server.AKASA_CHAT_ID", "6346467495"),
        ):
            await notify_task_complete(
                project="Akasa",
                task="Some task",
                status="retrying",
            )

        payload = mock_client.post.call_args.kwargs["json"]
        assert "retry_count" not in payload
        assert "max_retries" not in payload

    @pytest.mark.asyncio
    async def test_handle_rpc_notify_task_complete_retrying(self):
        """tools/call notify_task_complete status=retrying → response ปกติ (ไม่ใช่ error)"""
        from scripts.akasa_mcp_server import handle_rpc

        with patch(
            "scripts.akasa_mcp_server.notify_task_complete",
            new_callable=AsyncMock,
            return_value={"delivered": True, "timestamp": "2026-03-13T10:00:00+00:00"},
        ) as mock_notify:
            result = await handle_rpc(
                {
                    "id": 30,
                    "method": "tools/call",
                    "params": {
                        "name": "notify_task_complete",
                        "arguments": {
                            "project": "Akasa",
                            "task": "Deploy to production",
                            "status": "retrying",
                            "retry_count": 2,
                            "max_retries": 3,
                            "message": "Docker daemon not responding",
                        },
                    },
                }
            )

        data = json.loads(result)
        assert (
            "isError" not in data["result"] or data["result"].get("isError") is not True
        )
        assert "sent successfully" in data["result"]["content"][0]["text"].lower()

        # ตรวจว่า notify_task_complete ได้รับ retry args ถูกต้อง
        call_kwargs = mock_notify.call_args.kwargs
        assert call_kwargs["retry_count"] == 2
        assert call_kwargs["max_retries"] == 3

    @pytest.mark.asyncio
    async def test_handle_rpc_notify_task_complete_limit_reached(self):
        """tools/call notify_task_complete status=limit_reached → response ปกติ"""
        from scripts.akasa_mcp_server import handle_rpc

        with patch(
            "scripts.akasa_mcp_server.notify_task_complete",
            new_callable=AsyncMock,
            return_value={"delivered": True, "timestamp": "2026-03-13T10:00:00+00:00"},
        ) as mock_notify:
            result = await handle_rpc(
                {
                    "id": 31,
                    "method": "tools/call",
                    "params": {
                        "name": "notify_task_complete",
                        "arguments": {
                            "project": "Akasa",
                            "task": "Deploy to production",
                            "status": "limit_reached",
                            "max_retries": 3,
                        },
                    },
                }
            )

        data = json.loads(result)
        assert (
            "isError" not in data["result"] or data["result"].get("isError") is not True
        )

        call_kwargs = mock_notify.call_args.kwargs
        assert call_kwargs["max_retries"] == 3


class TestNotifyPendingReview:
    """ทดสอบ notify_pending_review function และ MCP tool handler"""

    @pytest.mark.asyncio
    async def test_notify_pending_review_success(self):
        """notify_pending_review ส่ง POST ไปที่ /api/v1/notifications/review-ready"""
        from scripts.akasa_mcp_server import notify_pending_review

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "delivered": True,
            "timestamp": "2025-01-01T00:00:00Z",
        }

        with patch("scripts.akasa_mcp_server.AKASA_CHAT_ID", "123456"):
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client_cls.return_value = mock_client

                result = await notify_pending_review(
                    project="Akasa",
                    task="Implement command queue service",
                    files_changed=["app/services/command_queue_service.py"],
                    summary="Added Redis-backed queue",
                )

        assert result["delivered"] is True
        call_args = mock_client.post.call_args
        assert "/api/v1/notifications/review-ready" in call_args[0][0]
        payload = call_args[1]["json"]
        assert payload["project"] == "Akasa"
        assert payload["task"] == "Implement command queue service"
        assert payload["files_changed"] == ["app/services/command_queue_service.py"]
        assert payload["summary"] == "Added Redis-backed queue"
        assert payload["chat_id"] == "123456"

    @pytest.mark.asyncio
    async def test_notify_pending_review_no_chat_id(self):
        """notify_pending_review ต้อง raise ValueError ถ้า AKASA_CHAT_ID ว่าง"""
        from scripts.akasa_mcp_server import notify_pending_review

        with patch("scripts.akasa_mcp_server.AKASA_CHAT_ID", ""):
            with pytest.raises(ValueError, match="AKASA_CHAT_ID"):
                await notify_pending_review(
                    project="Akasa",
                    task="Fix something",
                )

    @pytest.mark.asyncio
    async def test_notify_pending_review_minimal(self):
        """notify_pending_review ทำงานได้โดยไม่ต้องระบุ files_changed หรือ summary"""
        from scripts.akasa_mcp_server import notify_pending_review

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "delivered": True,
            "timestamp": "2025-01-01T00:00:00Z",
        }

        with patch("scripts.akasa_mcp_server.AKASA_CHAT_ID", "123456"):
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client_cls.return_value = mock_client

                result = await notify_pending_review(
                    project="Akasa",
                    task="Quick fix",
                )

        payload = mock_client.post.call_args[1]["json"]
        assert "files_changed" not in payload
        assert "summary" not in payload
        assert payload["task"] == "Quick fix"

    @pytest.mark.asyncio
    async def test_handle_rpc_notify_pending_review_delivered(self):
        """MCP tool handler notify_pending_review — delivered=True คืนข้อความ success"""
        from scripts.akasa_mcp_server import handle_rpc

        with patch(
            "scripts.akasa_mcp_server.notify_pending_review",
            new_callable=AsyncMock,
            return_value={"delivered": True, "timestamp": "2025-01-01T00:00:00Z"},
        ) as mock_notify:
            result = await handle_rpc(
                {
                    "id": 10,
                    "method": "tools/call",
                    "params": {
                        "name": "notify_pending_review",
                        "arguments": {
                            "project": "Akasa",
                            "task": "Implement feature #66",
                            "files_changed": ["app/services/command_queue_service.py"],
                        },
                    },
                }
            )

        data = json.loads(result)
        assert (
            "isError" not in data["result"] or data["result"].get("isError") is not True
        )
        assert "sent to Telegram" in data["result"]["content"][0]["text"]
        mock_notify.assert_called_once_with(
            project="Akasa",
            task="Implement feature #66",
            files_changed=["app/services/command_queue_service.py"],
            summary=None,
        )

    @pytest.mark.asyncio
    async def test_handle_rpc_notify_pending_review_not_delivered(self):
        """MCP tool handler — delivered=False คืนข้อความ warning"""
        from scripts.akasa_mcp_server import handle_rpc

        with patch(
            "scripts.akasa_mcp_server.notify_pending_review",
            new_callable=AsyncMock,
            return_value={"delivered": False, "timestamp": "2025-01-01T00:00:00Z"},
        ):
            result = await handle_rpc(
                {
                    "id": 11,
                    "method": "tools/call",
                    "params": {
                        "name": "notify_pending_review",
                        "arguments": {"project": "Akasa", "task": "Fix bug"},
                    },
                }
            )

        data = json.loads(result)
        assert "could not be confirmed" in data["result"]["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_handle_rpc_notify_pending_review_error(self):
        """MCP tool handler — exception คืน isError=True"""
        from scripts.akasa_mcp_server import handle_rpc

        with patch(
            "scripts.akasa_mcp_server.notify_pending_review",
            side_effect=Exception("Backend unavailable"),
        ):
            result = await handle_rpc(
                {
                    "id": 12,
                    "method": "tools/call",
                    "params": {
                        "name": "notify_pending_review",
                        "arguments": {"project": "Akasa", "task": "Fix bug"},
                    },
                }
            )

        data = json.loads(result)
        assert data["result"]["isError"] is True
        assert "Backend unavailable" in data["result"]["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_notify_pending_review_tool_schema(self):
        """ทดสอบ schema ของ notify_pending_review tool — required fields = [project, task]"""
        from scripts.akasa_mcp_server import TOOL_DEFINITIONS

        tool = next(t for t in TOOL_DEFINITIONS if t["name"] == "notify_pending_review")
        schema = tool["inputSchema"]
        assert schema["required"] == ["project", "task"]
        props = schema["properties"]
        assert "project" in props
        assert "task" in props
        assert "files_changed" in props
        assert props["files_changed"]["type"] == "array"
        assert "summary" in props
