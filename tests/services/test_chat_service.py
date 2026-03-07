import pytest
from unittest.mock import patch, AsyncMock
from app.services.chat_service import handle_chat_message
from app.models.telegram import Update, Message, Chat
import httpx

@pytest.fixture
def mock_update():
    return Update(
        update_id=1,
        message=Message(
            message_id=1,
            date=1612345678,
            chat=Chat(id=12345, type="private"),
            text="Hello Bot"
        )
    )

@pytest.fixture
def mock_update_no_text():
    return Update(
        update_id=2,
        message=Message(
            message_id=2,
            date=1612345678,
            chat=Chat(id=12345, type="private"),
            text=None # e.g., a sticker
        )
    )

@pytest.mark.asyncio
@patch("app.services.chat_service.telegram_service")
@patch("app.services.chat_service.llm_service")
async def test_handle_chat_message_success(mock_llm, mock_telegram, mock_update):
    # Setup mocks
    mock_llm.get_llm_reply = AsyncMock(return_value="Reply from AI")
    mock_telegram.send_message = AsyncMock()

    # Call service
    await handle_chat_message(mock_update)

    # Assertions
    mock_llm.get_llm_reply.assert_called_once_with("Hello Bot")
    mock_telegram.send_message.assert_called_once_with(12345, "Reply from AI")

@pytest.mark.asyncio
@patch("app.services.chat_service.telegram_service")
@patch("app.services.chat_service.llm_service")
async def test_handle_chat_message_no_text(mock_llm, mock_telegram, mock_update_no_text):
    # Call service with an update that has no text
    await handle_chat_message(mock_update_no_text)

    # Assertions
    mock_llm.get_llm_reply.assert_not_called()
    mock_telegram.send_message.assert_not_called()

@pytest.mark.asyncio
@patch("app.services.chat_service.telegram_service")
@patch("app.services.chat_service.llm_service")
async def test_handle_chat_message_llm_error(mock_llm, mock_telegram, mock_update):
    # Setup mock to raise an exception
    mock_llm.get_llm_reply = AsyncMock(side_effect=httpx.HTTPStatusError("500 Error", request=None, response=None))
    mock_telegram.send_message = AsyncMock()

    # Call service (should handle the error gracefully without crashing)
    await handle_chat_message(mock_update)

    # Assertions
    mock_llm.get_llm_reply.assert_called_once_with("Hello Bot")
    mock_telegram.send_message.assert_not_called() # Should not send a message if LLM fails

@pytest.mark.asyncio
@patch("app.services.chat_service.telegram_service")
@patch("app.services.chat_service.llm_service")
async def test_handle_chat_message_telegram_error(mock_llm, mock_telegram, mock_update):
    # Setup mocks: LLM succeeds, but Telegram throws HTTPStatusError
    mock_llm.get_llm_reply = AsyncMock(return_value="Reply from AI")
    mock_telegram.send_message = AsyncMock(side_effect=httpx.HTTPStatusError("400 Bad Request", request=None, response=None))

    # Call service (should handle the error gracefully without crashing)
    await handle_chat_message(mock_update)

    # Assertions
    mock_llm.get_llm_reply.assert_called_once_with("Hello Bot")
    mock_telegram.send_message.assert_called_once_with(12345, "Reply from AI")

@pytest.mark.asyncio
@patch("app.services.chat_service.telegram_service")
@patch("app.services.chat_service.llm_service")
async def test_handle_chat_message_llm_malformed(mock_llm, mock_telegram, mock_update):
    # Setup mocks: LLM raises TypeError/KeyError simulating unexpected JSON
    mock_llm.get_llm_reply = AsyncMock(side_effect=KeyError("choices"))
    mock_telegram.send_message = AsyncMock()

    # Call service
    await handle_chat_message(mock_update)

    # Assertions
    mock_llm.get_llm_reply.assert_called_once_with("Hello Bot")
    mock_telegram.send_message.assert_not_called()

@pytest.mark.asyncio
@patch("app.services.chat_service.telegram_service")
@patch("app.services.chat_service.llm_service")
async def test_handle_chat_message_timeout(mock_llm, mock_telegram, mock_update):
    # Setup mocks: LLM call times out
    mock_llm.get_llm_reply = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
    mock_telegram.send_message = AsyncMock()

    # Call service
    await handle_chat_message(mock_update)

    # Assertions
    mock_llm.get_llm_reply.assert_called_once_with("Hello Bot")
    mock_telegram.send_message.assert_not_called()
