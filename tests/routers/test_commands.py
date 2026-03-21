"""
Tests for Commands API Router — Feature #66
TDD: Red → Green → Refactor

Tests cover:
  - POST /api/v1/commands — enqueue command
  - GET /api/v1/commands/{command_id} — get status
  - POST /api/v1/commands/{command_id}/result — daemon reports result
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.models.command import (
    CommandQueueResponse,
    CommandResultRequest,
    CommandStatusResponse,
)
from app.routers.notifications import verify_api_key

client = TestClient(app)

COMMANDS_URL = "/api/v1/commands"


@pytest.fixture(autouse=True)
def cleanup_overrides():
    yield
    app.dependency_overrides = {}


@pytest.fixture
def auth_override():
    """Skip auth for most tests."""
    app.dependency_overrides[verify_api_key] = lambda: True
    yield
    app.dependency_overrides = {}


@pytest.fixture
def mock_tg_service():
    with patch("app.routers.commands.tg_service") as mock:
        mock.send_message = AsyncMock(return_value=None)
        yield mock


# ---------------------------------------------------------------------------
# POST /api/v1/commands — Enqueue
# ---------------------------------------------------------------------------


class TestEnqueueEndpoint:
    """POST /api/v1/commands tests."""

    def test_enqueue_unauthorized_missing_key(self):
        """ไม่มี API Key → 401."""
        response = client.post(
            COMMANDS_URL,
            json={"tool": "gemini", "command": "run_task"},
        )
        assert response.status_code == 401

    def test_enqueue_unauthorized_wrong_key(self):
        """API Key ผิด → 401."""
        response = client.post(
            COMMANDS_URL,
            json={"tool": "gemini", "command": "run_task"},
            headers={"X-Akasa-API-Key": "wrong-key"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_enqueue_success(self, auth_override):
        """Happy path — valid tool + command → 200 with command_id."""
        mock_response = CommandQueueResponse(
            command_id="cmd_abc123",
            status="queued",
            tool="gemini",
            command="run_task",
            queued_at="2026-01-01T00:00:00Z",
            expires_at="2026-01-01T00:05:00Z",
        )
        with patch(
            "app.routers.commands.command_queue_service.enqueue_command",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            with patch(
                "app.routers.commands.command_queue_service.check_rate_limit",
                new_callable=AsyncMock,
                return_value=(True, 0),
            ):
                response = client.post(
                    COMMANDS_URL,
                    json={
                        "tool": "gemini",
                        "command": "run_task",
                        "args": {"task": "summarize"},
                        "user_id": 123,
                        "chat_id": 456,
                    },
                    headers={"X-Akasa-API-Key": "valid-key"},
                )

        assert response.status_code == 200
        body = response.json()
        assert body["command_id"] == "cmd_abc123"
        assert body["status"] == "queued"

    @pytest.mark.asyncio
    async def test_enqueue_whitelist_rejection(self, auth_override):
        """Non-whitelisted command → 400."""
        with patch(
            "app.routers.commands.command_queue_service.enqueue_command",
            new_callable=AsyncMock,
            side_effect=ValueError("Command 'delete_all' is not in the whitelist"),
        ):
            with patch(
                "app.routers.commands.command_queue_service.check_rate_limit",
                new_callable=AsyncMock,
                return_value=(True, 0),
            ):
                response = client.post(
                    COMMANDS_URL,
                    json={
                        "tool": "gemini",
                        "command": "delete_all",
                        "user_id": 123,
                        "chat_id": 456,
                    },
                    headers={"X-Akasa-API-Key": "valid-key"},
                )

        assert response.status_code == 400
        assert "whitelist" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_enqueue_rate_limit_exceeded(self, auth_override):
        """Rate limit exceeded → 429."""
        with patch(
            "app.routers.commands.command_queue_service.check_rate_limit",
            new_callable=AsyncMock,
            return_value=(False, 42),
        ):
            response = client.post(
                COMMANDS_URL,
                json={
                    "tool": "gemini",
                    "command": "run_task",
                    "user_id": 123,
                    "chat_id": 456,
                },
                headers={"X-Akasa-API-Key": "valid-key"},
            )

        assert response.status_code == 429
        assert "rate limit" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_enqueue_redis_unavailable(self, auth_override):
        """Redis down → 503."""
        with patch(
            "app.routers.commands.command_queue_service.enqueue_command",
            new_callable=AsyncMock,
            side_effect=ConnectionError("Redis down"),
        ):
            with patch(
                "app.routers.commands.command_queue_service.check_rate_limit",
                new_callable=AsyncMock,
                return_value=(True, 0),
            ):
                response = client.post(
                    COMMANDS_URL,
                    json={
                        "tool": "gemini",
                        "command": "run_task",
                        "user_id": 123,
                        "chat_id": 456,
                    },
                    headers={"X-Akasa-API-Key": "valid-key"},
                )

        assert response.status_code == 503

    def test_enqueue_missing_required_fields(self, auth_override):
        """Missing tool/command → 422."""
        response = client.post(
            COMMANDS_URL,
            json={"tool": "gemini"},
            headers={"X-Akasa-API-Key": "valid-key"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_enqueue_uses_default_user_id_and_chat_id(self, auth_override, monkeypatch):
        """user_id/chat_id ไม่ส่ง → ใช้ default จาก settings."""
        monkeypatch.setattr(settings, "AKASA_CHAT_ID", "456")
        monkeypatch.setattr(settings, "ALLOWED_TELEGRAM_USER_IDS", "123")

        mock_response = CommandQueueResponse(
            command_id="cmd_xyz",
            status="queued",
            tool="gemini",
            command="run_task",
            queued_at="2026-01-01T00:00:00Z",
            expires_at="2026-01-01T00:05:00Z",
        )
        with patch(
            "app.routers.commands.command_queue_service.enqueue_command",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_enqueue:
            with patch(
                "app.routers.commands.command_queue_service.check_rate_limit",
                new_callable=AsyncMock,
                return_value=(True, 0),
            ):
                response = client.post(
                    COMMANDS_URL,
                    json={"tool": "gemini", "command": "run_task"},
                    headers={"X-Akasa-API-Key": "valid-key"},
                )

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/v1/commands/{command_id} — Status
# ---------------------------------------------------------------------------


class TestGetStatusEndpoint:
    """GET /api/v1/commands/{command_id} tests."""

    @pytest.mark.asyncio
    async def test_get_status_found(self, auth_override):
        """Known command → 200 with status."""
        mock_status = CommandStatusResponse(
            command_id="cmd_abc",
            status="queued",
            tool="gemini",
            command="run_task",
            queued_at="2026-01-01T00:00:00Z",
        )
        with patch(
            "app.routers.commands.command_queue_service.get_command_status",
            new_callable=AsyncMock,
            return_value=mock_status,
        ):
            response = client.get(
                f"{COMMANDS_URL}/cmd_abc",
                headers={"X-Akasa-API-Key": "valid-key"},
            )

        assert response.status_code == 200
        assert response.json()["command_id"] == "cmd_abc"
        assert response.json()["status"] == "queued"

    @pytest.mark.asyncio
    async def test_get_status_not_found(self, auth_override):
        """Unknown command_id → 404."""
        with patch(
            "app.routers.commands.command_queue_service.get_command_status",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = client.get(
                f"{COMMANDS_URL}/cmd_unknown",
                headers={"X-Akasa-API-Key": "valid-key"},
            )

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/v1/commands/{command_id}/result — Daemon Reports Result
# ---------------------------------------------------------------------------


class TestResultEndpoint:
    """POST /api/v1/commands/{command_id}/result tests."""

    @pytest.mark.asyncio
    async def test_report_result_success(self, auth_override, mock_tg_service):
        """Daemon reports success → 200 + notification sent."""
        mock_status = CommandStatusResponse(
            command_id="cmd_abc",
            status="queued",
            tool="gemini",
            command="run_task",
            cwd="/tmp/project",
            queued_at="2026-01-01T00:00:00Z",
            chat_id=12345,
        )
        with patch(
            "app.routers.commands.command_queue_service.get_command_status",
            new_callable=AsyncMock,
            return_value=mock_status,
        ):
            with patch(
                "app.routers.commands.command_queue_service.update_command_status",
                new_callable=AsyncMock,
                return_value=True,
            ):
                response = client.post(
                    f"{COMMANDS_URL}/cmd_abc/result",
                    json={
                        "status": "success",
                        "output": "Task completed",
                        "cwd": "/tmp/project",
                        "exit_code": 0,
                        "duration_seconds": 5.0,
                    },
                    headers={"X-Daemon-Secret": settings.AKASA_DAEMON_SECRET},
                )

        assert response.status_code == 200
        body = response.json()
        assert body["command_id"] == "cmd_abc"
        assert body["notification_sent"] is True

    @pytest.mark.asyncio
    async def test_report_result_includes_cwd_in_notification(self, auth_override, mock_tg_service):
        """Telegram result notification should show the execution cwd when provided."""
        mock_status = CommandStatusResponse(
            command_id="cmd_cwd",
            status="queued",
            tool="gemini",
            command="run_task",
            queued_at="2026-01-01T00:00:00Z",
            chat_id=12345,
        )
        with patch(
            "app.routers.commands.command_queue_service.get_command_status",
            new_callable=AsyncMock,
            return_value=mock_status,
        ):
            with patch(
                "app.routers.commands.command_queue_service.update_command_status",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_update:
                response = client.post(
                    f"{COMMANDS_URL}/cmd_cwd/result",
                    json={
                        "status": "success",
                        "output": "done",
                        "cwd": "/tmp/project",
                    },
                    headers={"X-Daemon-Secret": settings.AKASA_DAEMON_SECRET},
                )

        assert response.status_code == 200
        mock_update.assert_awaited_once()
        assert mock_update.await_args.kwargs["cwd"] == "/tmp/project"
        sent_text = mock_tg_service.send_message.await_args.kwargs["text"]
        assert "CWD" in sent_text

    @pytest.mark.asyncio
    async def test_report_result_invalid_daemon_secret(self):
        """Wrong daemon secret → 401."""
        response = client.post(
            f"{COMMANDS_URL}/cmd_abc/result",
            json={"status": "success", "output": "done"},
            headers={"X-Daemon-Secret": "wrong-secret"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_report_result_missing_daemon_secret(self):
        """No daemon secret header → 401."""
        response = client.post(
            f"{COMMANDS_URL}/cmd_abc/result",
            json={"status": "success", "output": "done"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_report_result_unknown_command(self, mock_tg_service):
        """Unknown command_id → 404."""
        with patch(
            "app.routers.commands.command_queue_service.get_command_status",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = client.post(
                f"{COMMANDS_URL}/cmd_unknown/result",
                json={"status": "success", "output": "done"},
                headers={"X-Daemon-Secret": settings.AKASA_DAEMON_SECRET},
            )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_report_result_failure_sends_notification(self, auth_override, mock_tg_service):
        """Daemon reports failure → notification includes error."""
        mock_status = CommandStatusResponse(
            command_id="cmd_abc",
            status="queued",
            tool="gemini",
            command="run_task",
            queued_at="2026-01-01T00:00:00Z",
            chat_id=12345,
        )
        with patch(
            "app.routers.commands.command_queue_service.get_command_status",
            new_callable=AsyncMock,
            return_value=mock_status,
        ):
            with patch(
                "app.routers.commands.command_queue_service.update_command_status",
                new_callable=AsyncMock,
                return_value=True,
            ):
                response = client.post(
                    f"{COMMANDS_URL}/cmd_abc/result",
                    json={
                        "status": "failed",
                        "output": "Error: connection refused",
                        "exit_code": 1,
                    },
                    headers={"X-Daemon-Secret": settings.AKASA_DAEMON_SECRET},
                )

        assert response.status_code == 200
        assert response.json()["notification_sent"] is True

    @pytest.mark.asyncio
    async def test_report_result_gemini_quota_error_adds_human_summary(
        self, auth_override, mock_tg_service
    ):
        """Gemini quota failures should include a short human-readable summary."""
        mock_status = CommandStatusResponse(
            command_id="cmd_quota",
            status="queued",
            tool="gemini",
            command="check_status",
            queued_at="2026-01-01T00:00:00Z",
            chat_id=12345,
        )
        quota_output = (
            "Loaded cached credentials.\n"
            "TerminalQuotaError: You have exhausted your capacity on this model. "
            "Your quota will reset after 18m30s."
        )
        with patch(
            "app.routers.commands.command_queue_service.get_command_status",
            new_callable=AsyncMock,
            return_value=mock_status,
        ):
            with patch(
                "app.routers.commands.command_queue_service.update_command_status",
                new_callable=AsyncMock,
                return_value=True,
            ):
                response = client.post(
                    f"{COMMANDS_URL}/cmd_quota/result",
                    json={
                        "status": "failed",
                        "output": quota_output,
                        "exit_code": 1,
                        "duration_seconds": 11.4,
                    },
                    headers={"X-Daemon-Secret": settings.AKASA_DAEMON_SECRET},
                )

        assert response.status_code == 200
        assert response.json()["notification_sent"] is True
        sent_text = mock_tg_service.send_message.await_args.kwargs["text"]
        assert "Gemini quota หมดชั่วคราว รีเซ็ตอีกประมาณ 18 นาที 30 วินาที" in sent_text

    @pytest.mark.asyncio
    async def test_report_result_gemini_fallback_success_adds_summary(
        self, auth_override, mock_tg_service
    ):
        """Successful fallback should produce a concise Thai summary."""
        mock_status = CommandStatusResponse(
            command_id="cmd_fallback",
            status="queued",
            tool="gemini",
            command="check_status",
            queued_at="2026-01-01T00:00:00Z",
            chat_id=12345,
        )
        fallback_output = (
            "Gemini quota reached on the primary model.\n"
            "Primary model: gemini-2.5-pro\n"
            "Retried with fallback model: gemini-2.5-flash\n\n"
            "fallback command succeeded"
        )
        with patch(
            "app.routers.commands.command_queue_service.get_command_status",
            new_callable=AsyncMock,
            return_value=mock_status,
        ):
            with patch(
                "app.routers.commands.command_queue_service.update_command_status",
                new_callable=AsyncMock,
                return_value=True,
            ):
                response = client.post(
                    f"{COMMANDS_URL}/cmd_fallback/result",
                    json={
                        "status": "success",
                        "output": fallback_output,
                        "exit_code": 0,
                        "duration_seconds": 7.2,
                    },
                    headers={"X-Daemon-Secret": settings.AKASA_DAEMON_SECRET},
                )

        assert response.status_code == 200
        sent_text = mock_tg_service.send_message.await_args.kwargs["text"]
        assert "Gemini quota บนโมเดลหลัก จึงสลับไปใช้ gemini\\-2\\.5\\-flash และรันต่อสำเร็จ" in sent_text
