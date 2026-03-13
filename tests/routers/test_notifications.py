from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.exceptions import BotBlockedException, UserChatIdNotFoundException
from app.main import app
from app.routers.notifications import verify_api_key

client = TestClient(app)


@pytest.fixture(autouse=True)
def cleanup_overrides():
    yield
    app.dependency_overrides = {}


@pytest.fixture
def mock_tg_service():
    with patch("app.routers.notifications.tg_service") as mock:
        yield mock


@pytest.fixture
def mock_redis_service():
    with patch("app.services.redis_service.get_chat_id_for_user") as mock:
        yield mock


def test_send_notification_unauthorized():
    """ต้องคืนค่า 401 ถ้า API Key ไม่ถูกต้องหรือหายไป"""
    response = client.post(
        "/api/v1/notifications/send",
        json={"user_id": "123", "message": "hello"},
        headers={"X-Akasa-API-Key": "wrong-key"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"


def test_send_notification_bad_request_invalid_payload():
    """ต้องคืนค่า 422 ถ้า Payload ไม่ครบถ้วน (ขาด message)"""
    app.dependency_overrides[verify_api_key] = lambda: True
    response = client.post(
        "/api/v1/notifications/send",
        json={"user_id": "123"},
        headers={"X-Akasa-API-Key": "any-key"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_send_notification_success(mock_tg_service):
    """ต้องคืนค่า 200 และเรียกใช้ TelegramService เมื่อข้อมูลถูกต้อง"""
    mock_tg_service.send_proactive_message = AsyncMock(return_value=None)
    app.dependency_overrides[verify_api_key] = lambda: True

    payload = {
        "user_id": "123456789",
        "message": "Test notification",
        "priority": "high",
    }

    response = client.post(
        "/api/v1/notifications/send",
        json=payload,
        headers={"X-Akasa-API-Key": "valid-key"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    mock_tg_service.send_proactive_message.assert_called_once()


@pytest.mark.asyncio
async def test_send_notification_user_not_found(mock_tg_service):
    """ต้องคืนค่า 400 เมื่อไม่พบ User ใน Redis Mapping"""
    mock_tg_service.send_proactive_message = AsyncMock(
        side_effect=UserChatIdNotFoundException("Not found")
    )
    app.dependency_overrides[verify_api_key] = lambda: True

    response = client.post(
        "/api/v1/notifications/send",
        json={"user_id": "999", "message": "hello"},
        headers={"X-Akasa-API-Key": "valid-key"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "User not found for notification"


@pytest.mark.asyncio
async def test_send_notification_bot_blocked(mock_tg_service):
    """ต้องคืนค่า 500 เมื่อ Bot ถูก User Blocked"""
    mock_tg_service.send_proactive_message = AsyncMock(
        side_effect=BotBlockedException("Blocked")
    )
    app.dependency_overrides[verify_api_key] = lambda: True

    response = client.post(
        "/api/v1/notifications/send",
        json={"user_id": "123", "message": "hello"},
        headers={"X-Akasa-API-Key": "valid-key"},
    )

    assert response.status_code == 500
    assert "Bot blocked by user" in response.json()["detail"]


def test_notification_payload_formatting():
    """ตรวจสอบว่าการจัดรูปแบบข้อความตาม Priority ทำงานถูกต้อง"""
    from app.models.notification import NotificationPayload

    payload_normal = NotificationPayload(user_id="1", message="test", priority="normal")
    assert payload_normal.get_formatted_message() == "test"

    payload_high = NotificationPayload(user_id="1", message="test", priority="high")
    assert "🚨 *IMPORTANT NOTIFICATION* 🚨" in payload_high.get_formatted_message()


# === Task Completion Notifications — /task-complete (Issue #61) ===

TASK_COMPLETE_URL = "/api/v1/notifications/task-complete"

VALID_TASK_PAYLOAD = {
    "project": "Akasa",
    "task": "Refactor Redis Service",
    "status": "success",
    "duration": "5m 20s",
    "source": "Gemini CLI",
}


def test_task_complete_unauthorized_missing_key(mock_tg_service):
    """ต้องคืนค่า 401 ถ้าไม่มี API Key ใน Header"""
    response = client.post(TASK_COMPLETE_URL, json=VALID_TASK_PAYLOAD)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"


def test_task_complete_unauthorized_wrong_key(mock_tg_service):
    """ต้องคืนค่า 401 ถ้า API Key ไม่ถูกต้อง"""
    response = client.post(
        TASK_COMPLETE_URL,
        json=VALID_TASK_PAYLOAD,
        headers={"X-Akasa-API-Key": "totally-wrong-key"},
    )
    assert response.status_code == 401


def test_task_complete_invalid_payload_missing_task(mock_tg_service):
    """ต้องคืนค่า 422 เมื่อ payload ขาด required field 'task'"""
    app.dependency_overrides[verify_api_key] = lambda: True
    response = client.post(
        TASK_COMPLETE_URL,
        json={"project": "Akasa", "status": "success"},
        headers={"X-Akasa-API-Key": "any-key"},
    )
    assert response.status_code == 422


def test_task_complete_invalid_payload_missing_status(mock_tg_service):
    """ต้องคืนค่า 422 เมื่อ payload ขาด required field 'status'"""
    app.dependency_overrides[verify_api_key] = lambda: True
    response = client.post(
        TASK_COMPLETE_URL,
        json={"project": "Akasa", "task": "Do something"},
        headers={"X-Akasa-API-Key": "any-key"},
    )
    assert response.status_code == 422


def test_task_complete_invalid_status_value(mock_tg_service):
    """ต้องคืนค่า 422 เมื่อ status ไม่ใช่ค่าที่กำหนด (success/failure/partial)"""
    app.dependency_overrides[verify_api_key] = lambda: True
    response = client.post(
        TASK_COMPLETE_URL,
        json={"project": "Akasa", "task": "Do something", "status": "done"},
        headers={"X-Akasa-API-Key": "any-key"},
    )
    assert response.status_code == 422


def test_task_complete_invalid_empty_task(mock_tg_service):
    """ต้องคืนค่า 422 เมื่อ task เป็น empty string"""
    app.dependency_overrides[verify_api_key] = lambda: True
    response = client.post(
        TASK_COMPLETE_URL,
        json={"project": "Akasa", "task": "   ", "status": "success"},
        headers={"X-Akasa-API-Key": "any-key"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_task_complete_success_with_chat_id_in_payload(mock_tg_service):
    """Happy path: chat_id ใน payload → ส่ง notification และคืน delivered=True"""
    mock_tg_service.send_task_notification = AsyncMock(return_value=None)
    app.dependency_overrides[verify_api_key] = lambda: True

    payload = {**VALID_TASK_PAYLOAD, "chat_id": "6346467495"}

    response = client.post(
        TASK_COMPLETE_URL,
        json=payload,
        headers={"X-Akasa-API-Key": "valid-key"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["delivered"] is True
    assert "timestamp" in body
    mock_tg_service.send_task_notification.assert_called_once()
    call_kwargs = mock_tg_service.send_task_notification.call_args.kwargs
    assert call_kwargs["chat_id"] == 6346467495


@pytest.mark.asyncio
async def test_task_complete_success_fallback_to_akasa_chat_id(
    mock_tg_service, monkeypatch
):
    """chat_id ไม่ได้ระบุใน payload → fallback ไปใช้ settings.AKASA_CHAT_ID"""
    mock_tg_service.send_task_notification = AsyncMock(return_value=None)
    app.dependency_overrides[verify_api_key] = lambda: True
    monkeypatch.setattr(settings, "AKASA_CHAT_ID", "6346467495")

    # payload ไม่มี chat_id
    payload = {
        "project": "Akasa",
        "task": "Analyze codebase",
        "status": "success",
    }

    response = client.post(
        TASK_COMPLETE_URL,
        json=payload,
        headers={"X-Akasa-API-Key": "valid-key"},
    )

    assert response.status_code == 200
    assert response.json()["delivered"] is True
    call_kwargs = mock_tg_service.send_task_notification.call_args.kwargs
    assert call_kwargs["chat_id"] == 6346467495


def test_task_complete_no_chat_id_and_no_server_default(mock_tg_service, monkeypatch):
    """ต้องคืนค่า 400 ถ้าไม่มี chat_id ใน payload และ AKASA_CHAT_ID ก็ไม่ได้ตั้งค่า"""
    app.dependency_overrides[verify_api_key] = lambda: True
    monkeypatch.setattr(settings, "AKASA_CHAT_ID", "")

    payload = {"project": "Akasa", "task": "Do something", "status": "success"}

    response = client.post(
        TASK_COMPLETE_URL,
        json=payload,
        headers={"X-Akasa-API-Key": "valid-key"},
    )

    assert response.status_code == 400
    assert "chat_id" in response.json()["detail"].lower()


def test_task_complete_invalid_chat_id_format(mock_tg_service, monkeypatch):
    """ต้องคืนค่า 400 ถ้า chat_id ไม่ใช่ตัวเลข"""
    app.dependency_overrides[verify_api_key] = lambda: True
    monkeypatch.setattr(settings, "AKASA_CHAT_ID", "")

    payload = {**VALID_TASK_PAYLOAD, "chat_id": "not-a-number"}

    response = client.post(
        TASK_COMPLETE_URL,
        json=payload,
        headers={"X-Akasa-API-Key": "valid-key"},
    )

    assert response.status_code == 400
    assert "chat_id" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_task_complete_failure_status(mock_tg_service, monkeypatch):
    """status='failure' ต้องผ่าน validation และ notify ได้ปกติ"""
    mock_tg_service.send_task_notification = AsyncMock(return_value=None)
    app.dependency_overrides[verify_api_key] = lambda: True
    monkeypatch.setattr(settings, "AKASA_CHAT_ID", "6346467495")

    response = client.post(
        TASK_COMPLETE_URL,
        json={"project": "Akasa", "task": "Deploy to prod", "status": "failure"},
        headers={"X-Akasa-API-Key": "valid-key"},
    )

    assert response.status_code == 200
    assert response.json()["delivered"] is True
    call_kwargs = mock_tg_service.send_task_notification.call_args.kwargs
    assert call_kwargs["request"].status == "failure"


@pytest.mark.asyncio
async def test_task_complete_partial_status(mock_tg_service, monkeypatch):
    """status='partial' ต้องผ่าน validation และ notify ได้ปกติ"""
    mock_tg_service.send_task_notification = AsyncMock(return_value=None)
    app.dependency_overrides[verify_api_key] = lambda: True
    monkeypatch.setattr(settings, "AKASA_CHAT_ID", "6346467495")

    response = client.post(
        TASK_COMPLETE_URL,
        json={"project": "Akasa", "task": "Run tests", "status": "partial"},
        headers={"X-Akasa-API-Key": "valid-key"},
    )

    assert response.status_code == 200
    assert response.json()["delivered"] is True


@pytest.mark.asyncio
async def test_task_complete_telegram_429_returns_429(mock_tg_service, monkeypatch):
    """Telegram rate limit (429) → router ต้องคืนค่า 429 พร้อม detail ที่เหมาะสม"""
    monkeypatch.setattr(settings, "AKASA_CHAT_ID", "6346467495")
    app.dependency_overrides[verify_api_key] = lambda: True

    error_response = httpx.Response(
        429, json={"description": "Too Many Requests: retry after 30"}
    )
    mock_tg_service.send_task_notification = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "Too Many Requests", request=AsyncMock(), response=error_response
        )
    )

    response = client.post(
        TASK_COMPLETE_URL,
        json={"project": "Akasa", "task": "Flood test", "status": "success"},
        headers={"X-Akasa-API-Key": "valid-key"},
    )

    assert response.status_code == 429
    assert "rate limit" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_task_complete_telegram_other_error_returns_delivered_false(
    mock_tg_service, monkeypatch
):
    """Non-429 Telegram HTTP error → delivered=False (ไม่ raise 500)"""
    monkeypatch.setattr(settings, "AKASA_CHAT_ID", "6346467495")
    app.dependency_overrides[verify_api_key] = lambda: True

    error_response = httpx.Response(400, json={"description": "Bad Request"})
    mock_tg_service.send_task_notification = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "Bad Request", request=AsyncMock(), response=error_response
        )
    )

    response = client.post(
        TASK_COMPLETE_URL,
        json={"project": "Akasa", "task": "Some task", "status": "success"},
        headers={"X-Akasa-API-Key": "valid-key"},
    )

    assert response.status_code == 200
    assert response.json()["delivered"] is False
    assert "timestamp" in response.json()


@pytest.mark.asyncio
async def test_task_complete_unexpected_exception_returns_500(
    mock_tg_service, monkeypatch
):
    """Unexpected exception → 500 Internal Server Error"""
    monkeypatch.setattr(settings, "AKASA_CHAT_ID", "6346467495")
    app.dependency_overrides[verify_api_key] = lambda: True

    mock_tg_service.send_task_notification = AsyncMock(
        side_effect=RuntimeError("Unexpected crash")
    )

    response = client.post(
        TASK_COMPLETE_URL,
        json={"project": "Akasa", "task": "Some task", "status": "success"},
        headers={"X-Akasa-API-Key": "valid-key"},
    )

    assert response.status_code == 500


@pytest.mark.asyncio
async def test_task_complete_payload_chat_id_takes_precedence_over_server_default(
    mock_tg_service, monkeypatch
):
    """chat_id ใน payload ต้องมีความสำคัญเหนือกว่า AKASA_CHAT_ID ของ server"""
    mock_tg_service.send_task_notification = AsyncMock(return_value=None)
    app.dependency_overrides[verify_api_key] = lambda: True
    monkeypatch.setattr(settings, "AKASA_CHAT_ID", "9999999999")  # server default

    payload = {**VALID_TASK_PAYLOAD, "chat_id": "1111111111"}  # caller-specified

    response = client.post(
        TASK_COMPLETE_URL,
        json=payload,
        headers={"X-Akasa-API-Key": "valid-key"},
    )

    assert response.status_code == 200
    call_kwargs = mock_tg_service.send_task_notification.call_args.kwargs
    # Must use caller's chat_id, not the server default
    assert call_kwargs["chat_id"] == 1111111111


def test_task_complete_status_is_case_insensitive(mock_tg_service, monkeypatch):
    """status field ต้องรองรับตัวพิมพ์ใหญ่ (เช่น 'SUCCESS') ผ่าน validator"""
    app.dependency_overrides[verify_api_key] = lambda: True
    monkeypatch.setattr(settings, "AKASA_CHAT_ID", "6346467495")
    mock_tg_service.send_task_notification = AsyncMock(return_value=None)

    response = client.post(
        TASK_COMPLETE_URL,
        json={"project": "Akasa", "task": "Deploy", "status": "SUCCESS"},
        headers={"X-Akasa-API-Key": "valid-key"},
    )

    assert response.status_code == 200


# === Retry Statuses (Issue #61 extension) ===


@pytest.mark.asyncio
async def test_task_complete_retrying_status_with_counts(mock_tg_service, monkeypatch):
    """status='retrying' พร้อม retry_count/max_retries → delivered=True"""
    mock_tg_service.send_task_notification = AsyncMock(return_value=None)
    app.dependency_overrides[verify_api_key] = lambda: True
    monkeypatch.setattr(settings, "AKASA_CHAT_ID", "6346467495")

    response = client.post(
        TASK_COMPLETE_URL,
        json={
            "project": "Akasa",
            "task": "Deploy to production",
            "status": "retrying",
            "retry_count": 2,
            "max_retries": 3,
            "message": "Docker daemon not responding",
        },
        headers={"X-Akasa-API-Key": "valid-key"},
    )

    assert response.status_code == 200
    assert response.json()["delivered"] is True
    call_kwargs = mock_tg_service.send_task_notification.call_args.kwargs
    assert call_kwargs["request"].status == "retrying"
    assert call_kwargs["request"].retry_count == 2
    assert call_kwargs["request"].max_retries == 3


@pytest.mark.asyncio
async def test_task_complete_retrying_status_without_counts(
    mock_tg_service, monkeypatch
):
    """status='retrying' ไม่มี retry_count/max_retries → delivered=True เช่นกัน"""
    mock_tg_service.send_task_notification = AsyncMock(return_value=None)
    app.dependency_overrides[verify_api_key] = lambda: True
    monkeypatch.setattr(settings, "AKASA_CHAT_ID", "6346467495")

    response = client.post(
        TASK_COMPLETE_URL,
        json={
            "project": "Akasa",
            "task": "Run tests",
            "status": "retrying",
        },
        headers={"X-Akasa-API-Key": "valid-key"},
    )

    assert response.status_code == 200
    assert response.json()["delivered"] is True
    call_kwargs = mock_tg_service.send_task_notification.call_args.kwargs
    assert call_kwargs["request"].retry_count is None
    assert call_kwargs["request"].max_retries is None


@pytest.mark.asyncio
async def test_task_complete_limit_reached_status(mock_tg_service, monkeypatch):
    """status='limit_reached' + max_retries → delivered=True"""
    mock_tg_service.send_task_notification = AsyncMock(return_value=None)
    app.dependency_overrides[verify_api_key] = lambda: True
    monkeypatch.setattr(settings, "AKASA_CHAT_ID", "6346467495")

    response = client.post(
        TASK_COMPLETE_URL,
        json={
            "project": "Akasa",
            "task": "Deploy to production",
            "status": "limit_reached",
            "max_retries": 3,
            "message": "Gave up after 3 attempts. Last error: timeout",
        },
        headers={"X-Akasa-API-Key": "valid-key"},
    )

    assert response.status_code == 200
    assert response.json()["delivered"] is True
    call_kwargs = mock_tg_service.send_task_notification.call_args.kwargs
    assert call_kwargs["request"].status == "limit_reached"
    assert call_kwargs["request"].max_retries == 3


def test_task_complete_invalid_retry_status(mock_tg_service, monkeypatch):
    """status ที่ไม่ใช่ค่าใน Literal ต้องคืนค่า 422 เสมอ"""
    app.dependency_overrides[verify_api_key] = lambda: True
    monkeypatch.setattr(settings, "AKASA_CHAT_ID", "6346467495")

    response = client.post(
        TASK_COMPLETE_URL,
        json={"project": "Akasa", "task": "Test", "status": "retry"},  # typo
        headers={"X-Akasa-API-Key": "valid-key"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_task_complete_success_after_retries_passes_counts(
    mock_tg_service, monkeypatch
):
    """success พร้อม retry_count/max_retries → service ได้รับ counts ครบ"""
    mock_tg_service.send_task_notification = AsyncMock(return_value=None)
    app.dependency_overrides[verify_api_key] = lambda: True
    monkeypatch.setattr(settings, "AKASA_CHAT_ID", "6346467495")

    response = client.post(
        TASK_COMPLETE_URL,
        json={
            "project": "Akasa",
            "task": "Deploy to production",
            "status": "success",
            "retry_count": 2,
            "max_retries": 3,
        },
        headers={"X-Akasa-API-Key": "valid-key"},
    )

    assert response.status_code == 200
    call_kwargs = mock_tg_service.send_task_notification.call_args.kwargs
    assert call_kwargs["request"].retry_count == 2
    assert call_kwargs["request"].max_retries == 3


def test_task_complete_all_valid_statuses_pass_validation(mock_tg_service, monkeypatch):
    """ทุก status ที่ถูกต้องต้องผ่าน validation ทั้งหมด 5 ค่า"""
    app.dependency_overrides[verify_api_key] = lambda: True
    monkeypatch.setattr(settings, "AKASA_CHAT_ID", "6346467495")
    mock_tg_service.send_task_notification = AsyncMock(return_value=None)

    valid_statuses = ["success", "failure", "partial", "retrying", "limit_reached"]
    for status in valid_statuses:
        response = client.post(
            TASK_COMPLETE_URL,
            json={"project": "Akasa", "task": "Test task", "status": status},
            headers={"X-Akasa-API-Key": "valid-key"},
        )
        assert response.status_code == 200, (
            f"Expected 200 for status='{status}', got {response.status_code}"
        )
