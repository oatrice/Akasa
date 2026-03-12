import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.models.notification import ActionRequestState

@pytest.fixture
def valid_headers():
    return {"X-Akasa-API-Key": settings.AKASA_API_KEY}

@pytest.mark.asyncio
async def test_create_action_request_success(valid_headers):
    """ทดสอบสร้าง Action Request สำเร็จ"""
    payload = {
        "chat_id": "12345",
        "message": "Action Required: rm -rf /tmp",
        "metadata": {
            "request_id": "req-1",
            "command": "rm -rf /tmp",
            "cwd": "/tmp",
            "session_id": "sess-1"
        }
    }
    
    with patch("app.routers.actions.settings.ALLOWED_TELEGRAM_CHAT_IDS", "12345"), \
         patch("app.routers.actions.has_session_permission", new_callable=AsyncMock) as mock_session, \
         patch("app.routers.actions.set_action_request", new_callable=AsyncMock) as mock_set, \
         patch("app.routers.actions.tg_service.send_confirmation_message", new_callable=AsyncMock) as mock_tg:
        
        mock_session.return_value = False
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/v1/actions/request", json=payload, headers=valid_headers)
        
        assert response.status_code == 200
        assert response.json()["request_id"] == "req-1"
        assert response.json()["status"] == "pending"
        assert mock_set.called
        assert mock_tg.called

@pytest.mark.asyncio
async def test_create_action_request_session_allowed(valid_headers):
    """ทดสอบสร้าง Action Request กรณีมี Session Permission อยู่แล้ว (ต้องมีการแจ้งเตือนเป็น Log)"""
    payload = {
        "chat_id": "12345",
        "message": "Action Required: rm -rf /tmp",
        "metadata": {
            "request_id": "req-1",
            "command": "rm -rf /tmp",
            "cwd": "/tmp",
            "session_id": "sess-1"
        }
    }
    
    with patch("app.routers.actions.settings.ALLOWED_TELEGRAM_CHAT_IDS", "12345"), \
         patch("app.routers.actions.has_session_permission", new_callable=AsyncMock) as mock_session, \
         patch("app.routers.actions.tg_service.send_message", new_callable=AsyncMock) as mock_send:
        
        mock_session.return_value = True # มีสิทธิ์ session แล้ว
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/v1/actions/request", json=payload, headers=valid_headers)
        
        assert response.status_code == 200
        assert response.json()["status"] == "allowed"
        assert response.json()["session_permission"] is True
        
        # ตรวจสอบว่ามีการส่งข้อความแจ้งเตือน (Auto-allowed log)
        assert mock_send.called
        _, kwargs = mock_send.call_args
        assert "Auto-allowed" in kwargs["text"]

@pytest.mark.asyncio
async def test_create_action_request_unauthorized_chat(valid_headers):
    """ทดสอบสร้าง Action Request กรณี Chat ID ไม่ได้รับอนุญาต"""
    payload = {
        "chat_id": "99999",
        "message": "Spam",
        "metadata": {"request_id": "r", "command": "c", "cwd": "."}
    }
    
    with patch("app.routers.actions.settings.ALLOWED_TELEGRAM_CHAT_IDS", "123,456"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/v1/actions/request", json=payload, headers=valid_headers)
        assert response.status_code == 403
        assert "not allowed" in response.json()["detail"]

@pytest.mark.asyncio
async def test_get_action_request_status(valid_headers):
    """ทดสอบเช็คสถานะ Action Request"""
    req_id = "req-123"
    
    with patch("app.routers.actions.get_action_request", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = ActionRequestState(
            command="ls", cwd=".", status="allowed"
        )
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get(f"/api/v1/actions/requests/{req_id}", headers=valid_headers)
        
        assert response.status_code == 200
        assert response.json()["status"] == "allowed"
