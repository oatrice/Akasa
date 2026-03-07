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


# === Success path (with Redis history) ===

@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.telegram_service")
@patch("app.services.chat_service.llm_service")
async def test_handle_chat_message_success_with_history(mock_llm, mock_telegram, mock_redis, mock_update):
    """ส่ง prompt พร้อม history ที่ดึงจาก Redis ไปให้ LLM"""
    # Setup: Redis returns existing history
    mock_redis.get_chat_history = AsyncMock(return_value=[
        {"role": "user", "content": "What is Python?"},
        {"role": "assistant", "content": "Python is a programming language."},
    ])
    mock_redis.add_message_to_history = AsyncMock()
    mock_llm.get_llm_reply = AsyncMock(return_value="Reply from AI")
    mock_telegram.send_message = AsyncMock()

    await handle_chat_message(mock_update)

    # LLM should receive history + new message
    expected_messages = [
        {"role": "user", "content": "What is Python?"},
        {"role": "assistant", "content": "Python is a programming language."},
        {"role": "user", "content": "Hello Bot"},
    ]
    mock_llm.get_llm_reply.assert_called_once_with(expected_messages)
    mock_telegram.send_message.assert_called_once_with(12345, "Reply from AI")

    # ต้องบันทึก user message + assistant reply กลับ Redis
    assert mock_redis.add_message_to_history.call_count == 2
    mock_redis.add_message_to_history.assert_any_call(12345, "user", "Hello Bot")
    mock_redis.add_message_to_history.assert_any_call(12345, "assistant", "Reply from AI")


@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.telegram_service")
@patch("app.services.chat_service.llm_service")
async def test_handle_chat_message_no_history(mock_llm, mock_telegram, mock_redis, mock_update):
    """ถ้าไม่มี history ต้องส่งแค่ message เดียว"""
    mock_redis.get_chat_history = AsyncMock(return_value=[])
    mock_redis.add_message_to_history = AsyncMock()
    mock_llm.get_llm_reply = AsyncMock(return_value="Reply from AI")
    mock_telegram.send_message = AsyncMock()

    await handle_chat_message(mock_update)

    expected_messages = [{"role": "user", "content": "Hello Bot"}]
    mock_llm.get_llm_reply.assert_called_once_with(expected_messages)


# === Redis failure (Graceful Degradation) ===

@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.telegram_service")
@patch("app.services.chat_service.llm_service")
async def test_handle_chat_message_redis_get_failure(mock_llm, mock_telegram, mock_redis, mock_update):
    """ถ้า Redis ล่ม ตอนดึง history → ยังทำงานได้ (ส่งแค่ prompt เดียว)"""
    mock_redis.get_chat_history = AsyncMock(side_effect=Exception("Redis connection failed"))
    mock_redis.add_message_to_history = AsyncMock()
    mock_llm.get_llm_reply = AsyncMock(return_value="Reply without context")
    mock_telegram.send_message = AsyncMock()

    await handle_chat_message(mock_update)

    # ต้องส่งแค่ message เดียว (ไม่มี history)
    expected_messages = [{"role": "user", "content": "Hello Bot"}]
    mock_llm.get_llm_reply.assert_called_once_with(expected_messages)
    mock_telegram.send_message.assert_called_once_with(12345, "Reply without context")


@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.telegram_service")
@patch("app.services.chat_service.llm_service")
async def test_handle_chat_message_redis_save_failure(mock_llm, mock_telegram, mock_redis, mock_update):
    """ถ้า Redis ล่ม ตอนบันทึก history → ยังส่ง response ไป Telegram ได้ปกติ"""
    mock_redis.get_chat_history = AsyncMock(return_value=[])
    mock_redis.add_message_to_history = AsyncMock(side_effect=Exception("Redis write failed"))
    mock_llm.get_llm_reply = AsyncMock(return_value="Reply from AI")
    mock_telegram.send_message = AsyncMock()

    # ต้องไม่ crash แม้ Redis save จะ fail
    await handle_chat_message(mock_update)

    mock_telegram.send_message.assert_called_once_with(12345, "Reply from AI")


# === Edge cases (keep existing behavior) ===

@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.telegram_service")
@patch("app.services.chat_service.llm_service")
async def test_handle_chat_message_no_text(mock_llm, mock_telegram, mock_redis, mock_update_no_text):
    """Ignore updates ที่ไม่มี text"""
    await handle_chat_message(mock_update_no_text)
    mock_llm.get_llm_reply.assert_not_called()
    mock_telegram.send_message.assert_not_called()


@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.telegram_service")
@patch("app.services.chat_service.llm_service")
async def test_handle_chat_message_llm_error(mock_llm, mock_telegram, mock_redis, mock_update):
    """ถ้า LLM error → จะส่งข้อความแจ้งเตือนกลับไปให้ user แทนการตอบปกติ"""
    mock_redis.get_chat_history = AsyncMock(return_value=[])
    mock_redis.add_message_to_history = AsyncMock()
    mock_llm.get_llm_reply = AsyncMock(side_effect=httpx.HTTPStatusError("500 Error", request=None, response=None))
    mock_telegram.send_message = AsyncMock()

    await handle_chat_message(mock_update)
    # ควรส่งข้อความบอกว่าระบบขัดข้อง
    mock_telegram.send_message.assert_called_once_with(12345, "ขออภัย ระบบขัดข้องชั่วคราวในการตอบสนอง 🙇‍♂️")
    # ไม่ควรบันทึก history ถ้า LLM fail (ยกเว้นเราจะเก็บ error log แต่ปัจจุบันคือไม่เก็บ)
    mock_redis.add_message_to_history.assert_not_called()


@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.telegram_service")
@patch("app.services.chat_service.llm_service")
async def test_handle_chat_message_telegram_error(mock_llm, mock_telegram, mock_redis, mock_update):
    """ถ้า Telegram error → ไม่ crash"""
    mock_redis.get_chat_history = AsyncMock(return_value=[])
    mock_redis.add_message_to_history = AsyncMock()
    mock_llm.get_llm_reply = AsyncMock(return_value="Reply from AI")
    mock_telegram.send_message = AsyncMock(side_effect=httpx.HTTPStatusError("400 Bad Request", request=None, response=None))

    await handle_chat_message(mock_update)
    mock_llm.get_llm_reply.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.telegram_service")
@patch("app.services.chat_service.llm_service")
async def test_handle_chat_message_timeout(mock_llm, mock_telegram, mock_redis, mock_update):
    """ถ้า LLM timeout → จะส่งข้อความแจ้งเตือนกลับไป"""
    mock_redis.get_chat_history = AsyncMock(return_value=[])
    mock_redis.add_message_to_history = AsyncMock()
    mock_llm.get_llm_reply = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
    mock_telegram.send_message = AsyncMock()

    await handle_chat_message(mock_update)
    mock_telegram.send_message.assert_called_once_with(12345, "ขออภัย ระบบขัดข้องชั่วคราวในการตอบสนอง 🙇‍♂️")
    mock_redis.add_message_to_history.assert_not_called()

@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.telegram_service")
@patch("app.services.chat_service.llm_service")
async def test_handle_chat_message_llm_malformed_data(mock_llm, mock_telegram, mock_redis, mock_update):
    """ถ้า LLM ตอบกลับมาผิดฟอร์ม (ValueError/KeyError) → จะส่งข้อความแจ้งเตือน"""
    mock_redis.get_chat_history = AsyncMock(return_value=[])
    mock_redis.add_message_to_history = AsyncMock()
    mock_llm.get_llm_reply = AsyncMock(side_effect=KeyError("choices"))
    mock_telegram.send_message = AsyncMock()

    await handle_chat_message(mock_update)
    mock_telegram.send_message.assert_called_once_with(12345, "ขออภัย ระบบไม่สามารถประมวลผลคำตอบได้ 🙇‍♂️")
    mock_redis.add_message_to_history.assert_not_called()
