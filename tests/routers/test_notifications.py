import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from app.main import app
from app.config import settings
from app.routers.notifications import verify_api_key
from app.exceptions import UserChatIdNotFoundException, BotBlockedException

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
        headers={"X-Akasa-API-Key": "wrong-key"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"

def test_send_notification_bad_request_invalid_payload():
    """ต้องคืนค่า 422 ถ้า Payload ไม่ครบถ้วน (ขาด message)"""
    app.dependency_overrides[verify_api_key] = lambda: True
    response = client.post(
        "/api/v1/notifications/send",
        json={"user_id": "123"},
        headers={"X-Akasa-API-Key": "any-key"}
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
        "priority": "high"
    }
    
    response = client.post(
        "/api/v1/notifications/send",
        json=payload,
        headers={"X-Akasa-API-Key": "valid-key"}
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    mock_tg_service.send_proactive_message.assert_called_once()

@pytest.mark.asyncio
async def test_send_notification_user_not_found(mock_tg_service):
    """ต้องคืนค่า 400 เมื่อไม่พบ User ใน Redis Mapping"""
    mock_tg_service.send_proactive_message = AsyncMock(side_effect=UserChatIdNotFoundException("Not found"))
    app.dependency_overrides[verify_api_key] = lambda: True
    
    response = client.post(
        "/api/v1/notifications/send",
        json={"user_id": "999", "message": "hello"},
        headers={"X-Akasa-API-Key": "valid-key"}
    )
    
    assert response.status_code == 400
    assert response.json()["detail"] == "User not found for notification"

@pytest.mark.asyncio
async def test_send_notification_bot_blocked(mock_tg_service):
    """ต้องคืนค่า 500 เมื่อ Bot ถูก User Blocked"""
    mock_tg_service.send_proactive_message = AsyncMock(side_effect=BotBlockedException("Blocked"))
    app.dependency_overrides[verify_api_key] = lambda: True
    
    response = client.post(
        "/api/v1/notifications/send",
        json={"user_id": "123", "message": "hello"},
        headers={"X-Akasa-API-Key": "valid-key"}
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
