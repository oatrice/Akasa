import pytest
import respx
import httpx
from app.services.telegram_service import tg_service

@pytest.mark.asyncio
async def test_send_confirmation_message_with_keyboard():
    """ทดสอบว่า TelegramService ส่งข้อความพร้อม Inline Keyboard ได้ถูกต้อง"""
    chat_id = 12345
    message = "Action Required: Execute rm -rf /tmp"
    request_id = "req-789"
    
    with respx.mock:
        # Mock Telegram API endpoint
        route = respx.post(f"{tg_service.api_url}/sendMessage").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        
        await tg_service.send_confirmation_message(
            chat_id=chat_id,
            text=message,
            request_id=request_id
        )
        
        # ตรวจสอบ Payload
        assert route.called
        request_data = route.calls[0].request.read()
        import json
        payload = json.loads(request_data)
        
        assert payload["chat_id"] == chat_id
        assert "reply_markup" in payload
        
        reply_markup = payload["reply_markup"]
        assert "inline_keyboard" in reply_markup
        
        buttons = reply_markup["inline_keyboard"][0]
        assert len(buttons) == 3
        
        # เช็คปุ่มและ callback_data
        assert buttons[0]["text"] == "✅ Allow Once"
        assert buttons[0]["callback_data"] == f"confirm:{request_id}:allow"
        
        assert buttons[1]["text"] == "🛡️ Allow Session"
        assert buttons[1]["callback_data"] == f"confirm:{request_id}:session"
        
        assert buttons[2]["text"] == "❌ Deny"
        assert buttons[2]["callback_data"] == f"confirm:{request_id}:deny"
