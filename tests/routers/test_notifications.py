import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from app.main import app
from app.config import settings

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

def test_send_notification_unauthorized():
    """ต้องคืนค่า 401 ถ้า API Key ไม่ถูกต้องหรือหายไป"""
    # ตรวจสอบว่าไม่ได้ใส่ override และใช้ key ผิด
    response = client.post(
        "/api/v1/notifications/send",
        json={"user_id": "123", "message": "hello"},
        headers={"X-Akasa-API-Key": "wrong-key"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"

def test_send_notification_bad_request_invalid_payload():
    """ต้องคืนค่า 422 ถ้า Payload ไม่ครบถ้วน (ขาด message)"""
    # Override ให้ผ่านการตรวจสอบ API Key เสมอ
    app.dependency_overrides[verify_api_key] = lambda: True
    
    response = client.post(
        "/api/v1/notifications/send",
        json={"user_id": "123"}, # ขาด message
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
        "priority": "high",
        "metadata": {"source": "unit-test"}
    }
    
    response = client.post(
        "/api/v1/notifications/send",
        json=payload,
        headers={"X-Akasa-API-Key": "valid-key"}
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    mock_tg_service.send_proactive_message.assert_called_once()

def test_notification_payload_formatting():
    """ตรวจสอบว่าการจัดรูปแบบข้อความตาม Priority ทำงานถูกต้อง"""
    from app.models.notification import NotificationPayload
    
    # กรณี Normal
    payload_normal = NotificationPayload(user_id="1", message="test", priority="normal")
    assert payload_normal.get_formatted_message() == "test"
    
    # กรณี High (B)
    payload_high = NotificationPayload(user_id="1", message="test", priority="high")
    assert "🚨 *IMPORTANT NOTIFICATION* 🚨" in payload_high.get_formatted_message()
    assert "test" in payload_high.get_formatted_message()
