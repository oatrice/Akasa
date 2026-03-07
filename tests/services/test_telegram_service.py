import pytest
import httpx
from app.services.telegram_service import send_message
from app.config import settings
import json

@pytest.mark.asyncio
async def test_send_message_success(respx_mock):
    # Mock settings
    settings.TELEGRAM_BOT_TOKEN = "test_bot_token"
    chat_id = 12345
    text = "Hello from AI (v1.0)"
    
    # Expected escaped text
    expected_text = r"Hello from AI \(v1\.0\)"

    # Intercept Telegram API call
    api_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    route = respx_mock.post(api_url).mock(
        return_value=httpx.Response(200, json={"ok": True})
    )

    # Call the service
    await send_message(chat_id, text)

    # Assertions
    assert route.called
    request_data = json.loads(route.calls[0].request.content)
    assert request_data["chat_id"] == chat_id
    assert request_data["text"] == expected_text
    assert request_data.get("parse_mode") == "MarkdownV2"

@pytest.mark.asyncio
async def test_send_message_error(respx_mock):
    # Mock settings
    settings.TELEGRAM_BOT_TOKEN = "test_bot_token"
    chat_id = 12345
    text = "Hello from AI"

    # Intercept Telegram API call and simulate a 400 error (e.g., chat not found)
    api_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    respx_mock.post(api_url).mock(
        return_value=httpx.Response(400, json={"ok": False, "description": "Bad Request: chat not found"})
    )

    # Calling the service should raise an exception
    with pytest.raises(httpx.HTTPStatusError):
        await send_message(chat_id, text)
