import pytest
import httpx
from unittest.mock import patch, AsyncMock
from app.config import settings
import json

# Import the instance, not the class or old function
from app.services.telegram_service import telegram_service 

@pytest.mark.asyncio
async def test_send_message_success(monkeypatch):
    # Use monkeypatch to control the API URL for the test
    test_api_url = "https://api.telegram.org/bot_test_bot_token"
    monkeypatch.setattr(telegram_service, 'api_url', test_api_url)

    chat_id = 12345
    text = "Hello from AI (v1.0)"
    
    expected_text = r"Hello from AI \(v1\.0\)"

    # Directly patch the 'post' method on the service's client instance
    with patch.object(telegram_service.client, 'post', new_callable=AsyncMock) as mock_post:
        # Configure the mock to return a successful response
        mock_response = AsyncMock()
        mock_response.raise_for_status = AsyncMock()
        mock_post.return_value = mock_response

        # Call the method we are testing
        await telegram_service.send_message(chat_id, text)

        # Assert that the 'post' method was called correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        
        # Check the URL it was called with
        assert f"{test_api_url}/sendMessage" in call_args.args
        
        # Check the JSON payload
        request_data = call_args.kwargs['json']
        assert request_data["chat_id"] == chat_id
        assert request_data["text"] == expected_text
        assert request_data.get("parse_mode") == "MarkdownV2"



@pytest.mark.asyncio
async def test_send_message_error(monkeypatch):
    # Use monkeypatch to control the API URL for the test
    test_api_url = "https://api.telegram.org/bot_test_bot_token"
    monkeypatch.setattr(telegram_service, 'api_url', test_api_url)

    chat_id = 12345
    text = "Hello from AI"

    # Directly patch the 'post' method on the service's client instance
    with patch.object(telegram_service.client, 'post', new_callable=AsyncMock) as mock_post:
        # This setup is a bit complex, let's simplify by having the mock itself raise the error
        mock_post.side_effect = httpx.HTTPStatusError(
            "Bad Request", 
            request=AsyncMock(), 
            response=httpx.Response(400, json={"ok": False, "description": "Bad Request: chat not found"})
        )

        # Calling the service method should now raise the exception
        with pytest.raises(httpx.HTTPStatusError):
            await telegram_service.send_message(chat_id, text)

        # Verify the call was made to the correct URL
        mock_post.assert_called_once_with(
            f"{test_api_url}/sendMessage",
            json={'chat_id': 12345, 'text': 'Hello from AI', 'parse_mode': 'MarkdownV2'},
            timeout=10.0
        )


# === Proactive Messaging (Issue #30) ===

@pytest.mark.asyncio
@patch("app.services.telegram_service.redis_service")
async def test_send_proactive_message_success(mock_redis):
    """Happy path: send_proactive_message should find user and send message."""
    user_id = 123
    chat_id = 456
    text = "Your report is ready."
    
    mock_redis.get_chat_id_for_user = AsyncMock(return_value=str(chat_id))
    
    with patch.object(telegram_service, 'send_message', new_callable=AsyncMock) as mock_send_message:
        await telegram_service.send_proactive_message(user_id, text)
        
        mock_redis.get_chat_id_for_user.assert_called_once_with(user_id)
        mock_send_message.assert_called_once_with(chat_id=chat_id, text=text)


@pytest.mark.asyncio
@patch("app.services.telegram_service.redis_service")
async def test_send_proactive_message_user_not_found(mock_redis):
    """Should raise UserChatIdNotFoundException if chat_id is not in Redis."""
    from app.exceptions import UserChatIdNotFoundException

    user_id = 999
    
    mock_redis.get_chat_id_for_user = AsyncMock(return_value=None)
    
    with patch.object(telegram_service, 'send_message', new_callable=AsyncMock) as mock_send_message:
        with pytest.raises(UserChatIdNotFoundException):
            await telegram_service.send_proactive_message(user_id, "This should fail.")
        
        mock_send_message.assert_not_called()


@pytest.mark.asyncio
@patch("app.services.telegram_service.redis_service")
async def test_send_proactive_message_bot_blocked(mock_redis):
    """Should raise BotBlockedException on 403 Forbidden error."""
    from app.exceptions import BotBlockedException
    
    user_id = 123
    chat_id = 456
    
    mock_redis.get_chat_id_for_user = AsyncMock(return_value=str(chat_id))
    
    # Simulate a 403 Forbidden error
    error_response = httpx.Response(403, json={"description": "Forbidden: bot was blocked by the user"})
    side_effect = httpx.HTTPStatusError("Forbidden", request=AsyncMock(), response=error_response)

    with patch.object(telegram_service, 'send_message', new_callable=AsyncMock, side_effect=side_effect) as mock_send_message:
        with pytest.raises(BotBlockedException):
            await telegram_service.send_proactive_message(user_id, "This will also fail.")
        
        mock_send_message.assert_called_once()
