import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.models.notification import ActionRequestState

client = TestClient(app)

@pytest.mark.asyncio
async def test_webhook_callback_query_confirmation():
    """ทดสอบว่า Webhook รับ callback_query และอัปเดตสถานะได้ถูกต้อง"""
    request_id = "req-999"
    callback_data = f"confirm:{request_id}:allow"
    
    # Mock update payload
    payload = {
        "update_id": 10001,
        "callback_query": {
            "id": "cb-123",
            "from": {"id": 555, "first_name": "TestUser", "is_bot": False},
            "message": {
                "message_id": 2002,
                "chat": {"id": 12345, "type": "private"},
                "text": "Action Required: rm -rf /tmp"
            },
            "data": callback_data
        }
    }
    
    headers = {"X-Telegram-Bot-Api-Secret-Token": settings.WEBHOOK_SECRET_TOKEN}
    
    # Mock Redis และ Telegram Service
    with patch("app.services.redis_service.get_action_request", new_callable=AsyncMock) as mock_get, \
         patch("app.services.redis_service.set_action_request", new_callable=AsyncMock) as mock_set, \
         patch("app.services.telegram_service.tg_service.edit_message_text", new_callable=AsyncMock) as mock_edit:
        
        # จำลองสถานะปัจจุบันใน Redis
        mock_get.return_value = ActionRequestState(
            command="rm -rf /tmp",
            cwd="/tmp",
            status="pending"
        )
        
        response = client.post("/api/v1/telegram/webhook", json=payload, headers=headers)
        
        assert response.status_code == 200
        
        # เนื่องจาก handle_chat_message รันใน BackgroundTask 
        # เราอาจต้องรอสักครู่ หรือใน Unit Test เราจะ patch handle_chat_message โดยตรง
        # แต่เพื่อความสมจริง เราจะเช็คว่า BackgroundTask ถูกเรียกใช้ (ถ้าเป็นไปได้)
        # หรือในเคสนี้ ผมจะรอให้ BackgroundTask รันจบ (pytest-asyncio อาจจะช่วย)
        
        # หมายเหตุ: ใน FastAPI TestClient, BackgroundTasks จะรันแบบ synchronous 
        # ดังนั้นเราสามารถเช็คผลได้ทันทีหลังเรียก post
        
        assert mock_set.called
        updated_state = mock_set.call_args[0][1]
        assert updated_state.status == "allowed"
        assert updated_state.decided_by == "TestUser"
        
        assert mock_edit.called
        # ตรวจสอบว่าแก้ไขข้อความเพื่อเอาปุ่มออก
        edit_args = mock_edit.call_args[1]
        assert "Allowed" in edit_args["text"]
        assert edit_args["reply_markup"] is None
