import pytest
from unittest.mock import patch, AsyncMock
from app.services.chat_service import handle_chat_message
from app.models.telegram import Update, Message, Chat
from app.config import settings
import httpx

@pytest.fixture(autouse=True)
def set_production_env():
    """บังคับให้ทุก test รันใน environment = production ยกเว้น test ที่ระบุเป็นอย่างอื่นชัดเจน"""
    original_env = getattr(settings, "ENVIRONMENT", "production")
    settings.ENVIRONMENT = "production"
    yield
    settings.ENVIRONMENT = original_env

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

@pytest.fixture
def setup_mock_redis(mock_redis):
    """Helper สำหรับ setup พื้นฐานของ Redis Mock เพื่อให้รองรับ Multi-Project"""
    mock_redis.get_current_project = AsyncMock(return_value="default")
    mock_redis.get_user_model_preference = AsyncMock(return_value=None)
    mock_redis.get_chat_history = AsyncMock(return_value=[])
    mock_redis.add_message_to_history = AsyncMock()
    mock_redis.get_project_list = AsyncMock(return_value=["default"])
    mock_redis.set_current_project = AsyncMock()
    return mock_redis


# === Success path (with Redis history) ===

@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
@patch("app.services.chat_service.llm_service")
async def test_handle_chat_message_success_with_history(mock_llm, mock_telegram, mock_redis, mock_update):
    """ส่ง prompt พร้อม history ที่ดึงจาก Redis ไปให้ LLM โดยแยกตามโปรเจ็กต์"""
    # Setup
    mock_redis.get_current_project = AsyncMock(return_value="default")
    mock_redis.get_user_model_preference = AsyncMock(return_value=None)
    mock_redis.get_chat_history = AsyncMock(return_value=[
        {"role": "user", "content": "What is Python?"},
        {"role": "assistant", "content": "Python is a programming language."},
    ])
    mock_redis.add_message_to_history = AsyncMock()
    mock_llm.get_llm_reply = AsyncMock(return_value="Reply from AI")
    mock_telegram.send_message = AsyncMock()

    await handle_chat_message(mock_update)

    # LLM should receive history + new message (with project context in system prompt)
    call_args = mock_llm.get_llm_reply.call_args[0][0]
    assert call_args[0]["role"] == "system"
    assert "default" in call_args[0]["content"]
    assert call_args[1] == {"role": "user", "content": "What is Python?"}
    assert call_args[2] == {"role": "assistant", "content": "Python is a programming language."}
    assert call_args[3] == {"role": "user", "content": "Hello Bot"}

    mock_telegram.send_message.assert_called_once_with(12345, "Reply from AI")

    # ต้องบันทึก user message + assistant reply กลับ Redis (ต้องระบุ project_name)
    assert mock_redis.add_message_to_history.call_count == 2
    mock_redis.add_message_to_history.assert_any_call(12345, "user", "Hello Bot", project_name="default")
    mock_redis.add_message_to_history.assert_any_call(12345, "assistant", "Reply from AI", project_name="default")

@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
@patch("app.services.chat_service.llm_service")
async def test_handle_chat_message_no_history(mock_llm, mock_telegram, mock_redis, mock_update):
    """ถ้าไม่มี history ต้องส่งแค่ message เดียว"""
    mock_redis.get_current_project = AsyncMock(return_value="default")
    mock_redis.get_user_model_preference = AsyncMock(return_value=None)
    mock_redis.get_chat_history = AsyncMock(return_value=[])
    mock_redis.add_message_to_history = AsyncMock()
    mock_llm.get_llm_reply = AsyncMock(return_value="Reply from AI")
    mock_telegram.send_message = AsyncMock()

    await handle_chat_message(mock_update)

    call_args = mock_llm.get_llm_reply.call_args[0][0]
    assert len(call_args) == 2  # system + user
    assert call_args[0]["role"] == "system"
    assert call_args[1] == {"role": "user", "content": "Hello Bot"}


# === Redis failure (Graceful Degradation) ===

@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
@patch("app.services.chat_service.llm_service")
async def test_handle_chat_message_redis_get_failure(mock_llm, mock_telegram, mock_redis, mock_update):
    """ถ้า Redis ล่ม ตอนดึง history → ยังทำงานได้ (ส่งแค่ prompt เดียว)"""
    mock_redis.get_current_project = AsyncMock(return_value="default")
    mock_redis.get_user_model_preference = AsyncMock(return_value=None)
    mock_redis.get_chat_history = AsyncMock(side_effect=Exception("Redis connection failed"))
    mock_redis.add_message_to_history = AsyncMock()
    mock_llm.get_llm_reply = AsyncMock(return_value="Reply without context")
    mock_telegram.send_message = AsyncMock()

    await handle_chat_message(mock_update)

    # ต้องส่งแค่ message เดียว (ไม่มี history แต่มี system prompt)
    call_args = mock_llm.get_llm_reply.call_args[0][0]
    assert call_args[0]["role"] == "system"
    assert call_args[1] == {"role": "user", "content": "Hello Bot"}
    mock_telegram.send_message.assert_called_once_with(12345, "Reply without context")


@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
@patch("app.services.chat_service.llm_service")
async def test_handle_chat_message_redis_save_failure(mock_llm, mock_telegram, mock_redis, mock_update):
    """ถ้า Redis ล่ม ตอนบันทึก history → ยังส่ง response ไป Telegram ได้ปกติ"""
    mock_redis.get_current_project = AsyncMock(return_value="default")
    mock_redis.get_user_model_preference = AsyncMock(return_value=None)
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
@patch("app.services.chat_service.tg_service")
@patch("app.services.chat_service.llm_service")
async def test_handle_chat_message_no_text(mock_llm, mock_telegram, mock_redis, mock_update_no_text):
    """Ignore updates ที่ไม่มี text"""
    await handle_chat_message(mock_update_no_text)
    mock_llm.get_llm_reply.assert_not_called()
    mock_telegram.send_message.assert_not_called()


@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
@patch("app.services.chat_service.llm_service")
async def test_handle_chat_message_llm_error(mock_llm, mock_telegram, mock_redis, mock_update):
    """ถ้า LLM error → จะส่งข้อความแจ้งเตือนกลับไปให้ user แทนการตอบปกติ"""
    mock_redis.get_current_project = AsyncMock(return_value="default")
    mock_redis.get_user_model_preference = AsyncMock(return_value=None)
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
@patch("app.services.chat_service.tg_service")
@patch("app.services.chat_service.llm_service")
async def test_handle_chat_message_telegram_error(mock_llm, mock_telegram, mock_redis, mock_update):
    """ถ้า Telegram error → ไม่ crash"""
    mock_redis.get_current_project = AsyncMock(return_value="default")
    mock_redis.get_user_model_preference = AsyncMock(return_value=None)
    mock_redis.get_chat_history = AsyncMock(return_value=[])
    mock_redis.add_message_to_history = AsyncMock()
    mock_llm.get_llm_reply = AsyncMock(return_value="Reply from AI")
    mock_telegram.send_message = AsyncMock(side_effect=httpx.HTTPStatusError("400 Bad Request", request=None, response=None))

    await handle_chat_message(mock_update)
    mock_llm.get_llm_reply.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
@patch("app.services.chat_service.llm_service")
async def test_handle_chat_message_timeout(mock_llm, mock_telegram, mock_redis, mock_update):
    """ถ้า LLM timeout → จะส่งข้อความแจ้งเตือนกลับไป"""
    mock_redis.get_current_project = AsyncMock(return_value="default")
    mock_redis.get_user_model_preference = AsyncMock(return_value=None)
    mock_redis.get_chat_history = AsyncMock(return_value=[])
    mock_redis.add_message_to_history = AsyncMock()
    mock_llm.get_llm_reply = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
    mock_telegram.send_message = AsyncMock()

    await handle_chat_message(mock_update)
    mock_telegram.send_message.assert_called_once_with(12345, "ขออภัย ระบบขัดข้องชั่วคราวในการตอบสนอง 🙇‍♂️")
    mock_redis.add_message_to_history.assert_not_called()

@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
@patch("app.services.chat_service.llm_service")
async def test_handle_chat_message_llm_malformed_data(mock_llm, mock_telegram, mock_redis, mock_update):
    """ถ้า LLM ตอบกลับมาผิดฟอร์ม (ValueError/KeyError) → จะส่งข้อความแจ้งเตือน"""
    mock_redis.get_current_project = AsyncMock(return_value="default")
    mock_redis.get_user_model_preference = AsyncMock(return_value=None)
    mock_redis.get_chat_history = AsyncMock(return_value=[])
    mock_redis.add_message_to_history = AsyncMock()
    mock_llm.get_llm_reply = AsyncMock(side_effect=KeyError("choices"))
    mock_telegram.send_message = AsyncMock()

    await handle_chat_message(mock_update)
    mock_telegram.send_message.assert_called_once_with(12345, "ขออภัย ระบบไม่สามารถประมวลผลคำตอบได้ 🙇‍♂️")
    mock_redis.add_message_to_history.assert_not_called()


@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
@patch("app.services.chat_service.llm_service")
async def test_handle_chat_message_llm_unexpected_error(mock_llm, mock_telegram, mock_redis, mock_update):
    """ถ้าเกิด Error ที่ไม่คาดคิดตอนเรียก LLM → จะส่งข้อความแจ้งเตือน generic กลับไป"""
    mock_redis.get_current_project = AsyncMock(return_value="default")
    mock_redis.get_user_model_preference = AsyncMock(return_value=None)
    mock_redis.get_chat_history = AsyncMock(return_value=[])
    mock_redis.add_message_to_history = AsyncMock()
    mock_llm.get_llm_reply = AsyncMock(side_effect=RuntimeError("Some terrible weird error"))
    mock_telegram.send_message = AsyncMock()

    await handle_chat_message(mock_update)
    mock_telegram.send_message.assert_called_once_with(12345, "ขออภัย เกิดข้อผิดพลาดที่ไม่คาดคิด โปรดลองอีกครั้งในภายหลัง")
    mock_redis.add_message_to_history.assert_not_called()


# === System Prompt Tests (Issue #8) ===

@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
@patch("app.services.chat_service.llm_service")
async def test_system_prompt_prepended_with_history(mock_llm, mock_telegram, mock_redis, mock_update):
    """System prompt ต้องถูกวางเป็นข้อความแรกใน messages ที่ส่งให้ LLM (มี history)"""
    mock_redis.get_current_project = AsyncMock(return_value="default")
    mock_redis.get_user_model_preference = AsyncMock(return_value=None)
    mock_redis.get_chat_history = AsyncMock(return_value=[
        {"role": "user", "content": "What is Python?"},
        {"role": "assistant", "content": "A programming language."},
    ])
    mock_redis.add_message_to_history = AsyncMock()
    mock_llm.get_llm_reply = AsyncMock(return_value="Reply from AI")
    mock_telegram.send_message = AsyncMock()

    await handle_chat_message(mock_update)

    call_args = mock_llm.get_llm_reply.call_args[0][0]
    # ข้อความแรกต้องเป็น system prompt
    assert call_args[0]["role"] == "system"
    assert settings.SYSTEM_PROMPT in call_args[0]["content"]
    # ตามด้วย history
    assert call_args[1] == {"role": "user", "content": "What is Python?"}
    assert call_args[2] == {"role": "assistant", "content": "A programming language."}
    # ปิดท้ายด้วย user message ใหม่
    assert call_args[-1] == {"role": "user", "content": "Hello Bot"}


@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
@patch("app.services.chat_service.llm_service")
async def test_system_prompt_prepended_no_history(mock_llm, mock_telegram, mock_redis, mock_update):
    """System prompt ต้องถูกวางเป็นข้อความแรกแม้ไม่มี history"""
    mock_redis.get_current_project = AsyncMock(return_value="default")
    mock_redis.get_user_model_preference = AsyncMock(return_value=None)
    mock_redis.get_chat_history = AsyncMock(return_value=[])
    mock_redis.add_message_to_history = AsyncMock()
    mock_llm.get_llm_reply = AsyncMock(return_value="Reply")
    mock_telegram.send_message = AsyncMock()

    await handle_chat_message(mock_update)

    call_args = mock_llm.get_llm_reply.call_args[0][0]
    assert len(call_args) == 2  # system + user
    assert call_args[0]["role"] == "system"
    assert settings.SYSTEM_PROMPT in call_args[0]["content"]
    assert call_args[1] == {"role": "user", "content": "Hello Bot"}


@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
@patch("app.services.chat_service.llm_service")
async def test_system_prompt_not_saved_to_redis(mock_llm, mock_telegram, mock_redis, mock_update):
    """System prompt ต้องไม่ถูกบันทึกลง Redis"""
    mock_redis.get_current_project = AsyncMock(return_value="default")
    mock_redis.get_user_model_preference = AsyncMock(return_value=None)
    mock_redis.get_chat_history = AsyncMock(return_value=[])
    mock_redis.add_message_to_history = AsyncMock()
    mock_llm.get_llm_reply = AsyncMock(return_value="Reply")
    mock_telegram.send_message = AsyncMock()

    await handle_chat_message(mock_update)

    # ต้องบันทึกแค่ user + assistant (ไม่มี system)
    assert mock_redis.add_message_to_history.call_count == 2
    mock_redis.add_message_to_history.assert_any_call(12345, "user", "Hello Bot", project_name="default")
    mock_redis.add_message_to_history.assert_any_call(12345, "assistant", "Reply", project_name="default")
    # ตรวจว่าไม่มี call ไหนที่ส่ง "system" เข้าไป
    for call in mock_redis.add_message_to_history.call_args_list:
        assert call[0][1] != "system", "System prompt must NOT be saved to Redis"

# === Local Build Info Tests (Issue #25) ===

@pytest.mark.asyncio
@patch("app.services.chat_service.get_build_info")
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
@patch("app.services.chat_service.llm_service")
async def test_build_info_appended_in_local_dev(
    mock_llm, mock_telegram, mock_redis, mock_get_build_info, mock_update
):
    """ทดสอบกรณีรันแบบ Local Dev (ENVIRONMENT=development) LLM reply ต้องมี Build Info ต่อท้าย และไม่บันทึกลง Redis"""
    original_env = getattr(settings, "ENVIRONMENT", "production")
    settings.ENVIRONMENT = "development"
    try:
        mock_redis.get_current_project = AsyncMock(return_value="default")
        mock_redis.get_user_model_preference = AsyncMock(return_value=None)
        mock_redis.get_chat_history = AsyncMock(return_value=[])
        mock_redis.add_message_to_history = AsyncMock()
        mock_llm.get_llm_reply = AsyncMock(return_value="Reply from AI")
        mock_get_build_info.return_value = "🤖 Version 0.1.0\n🌍 Env development\n🏗️ Built at 2026-03-08T04:49:51+07:00\n🔗 Commit abcdef1"
        mock_telegram.send_message = AsyncMock()

        await handle_chat_message(mock_update)

        expected_reply_with_footer = "Reply from AI\n\n---\n*Local Dev Info*\n🤖 Version 0.1.0\n🌍 Env development\n🏗️ Built at 2026-03-08T04:49:51+07:00\n🔗 Commit abcdef1"
        mock_telegram.send_message.assert_called_once_with(12345, expected_reply_with_footer)
        
        # Redis should only save the original reply without the footer to avoid context pollution
        mock_redis.add_message_to_history.assert_any_call(12345, "assistant", "Reply from AI", project_name="default")
    finally:
        settings.ENVIRONMENT = original_env

@pytest.mark.asyncio
@patch("app.services.chat_service.get_build_info")
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
@patch("app.services.chat_service.llm_service")
async def test_build_info_not_appended_in_prod(
    mock_llm, mock_telegram, mock_redis, mock_get_build_info, mock_update
):
    """ทดสอบกรณีรันแบบ Production จะไม่มีการเติม Local Build Info"""
    original_env = getattr(settings, "ENVIRONMENT", "development")
    settings.ENVIRONMENT = "production"
    try:
        mock_redis.get_current_project = AsyncMock(return_value="default")
        mock_redis.get_user_model_preference = AsyncMock(return_value=None)
        mock_redis.get_chat_history = AsyncMock(return_value=[])
        mock_redis.add_message_to_history = AsyncMock()
        mock_llm.get_llm_reply = AsyncMock(return_value="Reply from AI")
        mock_telegram.send_message = AsyncMock()
        mock_get_build_info.return_value = "Should not be called"

        await handle_chat_message(mock_update)

        mock_telegram.send_message.assert_called_once_with(12345, "Reply from AI")
        mock_get_build_info.assert_not_called()
    finally:
        settings.ENVIRONMENT = original_env


# === Model Selection (/model) Tests ===

@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
async def test_handle_model_command_show_current(mock_telegram, mock_redis):
    """ส่ง /model (ไม่มี argument) เพื่อดูโมเดลปัจจุบัน"""
    mock_redis.get_user_model_preference = AsyncMock(return_value="anthropic/claude-3.5-sonnet")
    mock_telegram.send_message = AsyncMock()
    
    update = Update(
        update_id=10,
        message=Message(
            message_id=10,
            date=1612345678,
            chat=Chat(id=123, type="private"),
            text="/model"
        )
    )
    
    await handle_chat_message(update)
    
    # ควรบอกว่าใช้ Claude อยู่
    args = mock_telegram.send_message.call_args[0]
    assert "Claude 3.5 Sonnet" in args[1]
    assert "claude" in args[1]
    assert "gemini" in args[1]


@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
async def test_handle_model_command_show_default_from_settings(mock_telegram, mock_redis, monkeypatch):
    """ส่ง /model (ไม่มี pref) เพื่อดูโมเดลปัจจุบัน โดยต้องดึงค่า default จาก settings จริงๆ"""
    # Setup: ไม่มีการตั้งค่าส่วนตัว
    mock_redis.get_user_model_preference = AsyncMock(return_value=None)
    mock_telegram.send_message = AsyncMock()
    
    # เปลี่ยนค่า default ใน settings เป็น Llama3
    monkeypatch.setattr(settings, "LLM_MODEL", "meta-llama/llama-3.3-70b-instruct")
    
    update = Update(
        update_id=100,
        message=Message(
            message_id=100,
            date=1612345678,
            chat=Chat(id=999, type="private"),
            text="/model"
        )
    )
    
    await handle_chat_message(update)
    
    # ผลลัพธ์ต้องแสดงชื่อ Llama 3.3 70B ไม่ใช่ Gemini ในส่วนของ Current model
    args = mock_telegram.send_message.call_args[0]
    first_line = args[1].split("\n")[0]
    assert "Meta Llama 3.3 70B" in first_line
    assert "(default)" in first_line.lower()
    assert "Gemini 2.5 Flash" not in first_line


@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
async def test_handle_model_command_update_success(mock_telegram, mock_redis):
    """ส่ง /model <alias> เพื่อเปลี่ยนโมเดล"""
    mock_redis.set_user_model_preference = AsyncMock()
    mock_telegram.send_message = AsyncMock()
    
    update = Update(
        update_id=11,
        message=Message(
            message_id=11,
            date=1612345678,
            chat=Chat(id=123, type="private"),
            text="/model gemini"
        )
    )
    
    await handle_chat_message(update)
    
    # ต้องบันทึกลง Redis
    mock_redis.set_user_model_preference.assert_called_once_with(123, "google/gemini-2.5-flash")
    # ต้องแจ้งยืนยัน
    args = mock_telegram.send_message.call_args[0]
    assert "updated" in args[1].lower()
    assert "Google Gemini 2.5 Flash" in args[1]


@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
async def test_handle_model_command_invalid_alias(mock_telegram, mock_redis):
    """ส่ง /model <alias> ที่ไม่มีอยู่จริง"""
    mock_redis.set_user_model_preference = AsyncMock()
    mock_telegram.send_message = AsyncMock()
    
    update = Update(
        update_id=12,
        message=Message(
            message_id=12,
            date=1612345678,
            chat=Chat(id=123, type="private"),
            text="/model invalid_alias"
        )
    )
    
    await handle_chat_message(update)
    
    # ต้องไม่บันทึกลง Redis
    mock_redis.set_user_model_preference.assert_not_called()
    # ต้องแจ้ง Error และบอกรายการที่ถูกต้อง
    args = mock_telegram.send_message.call_args[0]
    assert "Invalid model" in args[1]
    assert "claude" in args[1]


@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
@patch("app.services.chat_service.llm_service")
async def test_standard_message_uses_preferred_model(mock_llm, mock_telegram, mock_redis, mock_update):
    """ข้อความปกติควรใช้โมเดลที่ผู้ใช้เลือกไว้ใน Redis"""
    # Setup: ผู้ใช้เลือก Claude ไว้
    mock_redis.get_current_project = AsyncMock(return_value="default")
    mock_redis.get_user_model_preference = AsyncMock(return_value="anthropic/claude-3.5-sonnet")
    mock_redis.get_chat_history = AsyncMock(return_value=[])
    mock_redis.add_message_to_history = AsyncMock()
    mock_llm.get_llm_reply = AsyncMock(return_value="Claude reply")
    mock_telegram.send_message = AsyncMock()

    await handle_chat_message(mock_update)

    # get_llm_reply ต้องถูกเรียกพร้อม model="anthropic/claude-3.5-sonnet"
    mock_llm.get_llm_reply.assert_called_once()
    assert mock_llm.get_llm_reply.call_args.kwargs["model"] == "anthropic/claude-3.5-sonnet"


# === Project Context Restoration (/project) Tests - Issue #38 ===

@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
async def test_project_switch_with_saved_context_shows_summary(mock_telegram, mock_redis):
    """ทดสอบ /project select <name> เมื่อมี AgentState บันทึกไว้ ต้องแสดง Welcome back summary"""
    from app.models.agent_state import AgentState
    import datetime

    chat_id = 2000
    project_name = "akasa"
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # 1. Setup Mock: จำลองว่า Redis มี AgentState ของโปรเจ็กต์นี้อยู่
    saved_state = AgentState(
        current_task="Fixing the Redis migration bug.",
        focus_file="app/services/redis_service.py",
        last_activity_timestamp=now
    )
    # redis_service.get_agent_state ต้องคืนค่า state นี้เมื่อถูกเรียก
    mock_redis.get_agent_state = AsyncMock(return_value=saved_state)
    mock_redis.get_project_list = AsyncMock(return_value=["default", "akasa"])
    mock_redis.set_current_project = AsyncMock()
    mock_telegram.send_message = AsyncMock()
    
    # 2. สร้าง Update object สำหรับคำสั่ง /project select
    update = Update(
        update_id=20,
        message=Message(
            message_id=20,
            date=int(now.timestamp()),
            chat=Chat(id=chat_id, type="private"),
            text=f"/project select {project_name}"
        )
    )

    # 3. รัน handle_chat_message
    await handle_chat_message(update)

    # 4. ตรวจสอบ:
    # - ต้องมีการ set project ใหม่ใน Redis
    mock_redis.set_current_project.assert_called_once_with(chat_id, project_name)
    # - ต้องมีการส่งข้อความกลับไป
    mock_telegram.send_message.assert_called_once()
    # - ข้อความต้องเป็น Welcome Back summary ที่ถูกต้อง (ใช้ Template)
    sent_message = mock_telegram.send_message.call_args[0][1]
    assert "Welcome back" in sent_message
    assert f"Switched to project: `{project_name}`" in sent_message
    assert "Last known task:" in sent_message
    assert saved_state.current_task in sent_message


@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
async def test_handle_note_command_saves_agent_state(mock_telegram, mock_redis):
    """ทดสอบ /note <task> ต้องบันทึก AgentState ลง Redis"""
    from app.models.agent_state import AgentState
    import datetime

    chat_id = 2001
    project_name = "akasa"
    note_text = "Working on the new /note command feature."
    
    # 1. Setup Mock
    mock_redis.get_current_project = AsyncMock(return_value=project_name)
    # get_agent_state คืนค่า None เพื่อจำลองว่ายังไม่มี state เดิม
    mock_redis.get_agent_state = AsyncMock(return_value=None) 
    mock_redis.set_agent_state = AsyncMock()
    mock_telegram.send_message = AsyncMock()
    
    # 2. สร้าง Update สำหรับ /note command
    update = Update(
        update_id=21,
        message=Message(
            message_id=21,
            date=int(datetime.datetime.now().timestamp()),
            chat=Chat(id=chat_id, type="private"),
            text=f"/note {note_text}"
        )
    )

    # 3. รัน handle_chat_message
    await handle_chat_message(update)

    # 4. ตรวจสอบ
    # - ต้องมีการเรียก set_agent_state
    mock_redis.set_agent_state.assert_called_once()
    # - ตรวจสอบ object ที่ส่งไปให้ set_agent_state
    call_args = mock_redis.set_agent_state.call_args[0]
    assert call_args[0] == chat_id
    assert call_args[1] == project_name
    saved_state: AgentState = call_args[2]
    assert isinstance(saved_state, AgentState)
    assert saved_state.current_task == note_text
    
    # - ต้องส่งข้อความยืนยันกลับมา
    mock_telegram.send_message.assert_called_once()
    sent_message = mock_telegram.send_message.call_args[0][1]
    assert "✅ Note saved for project" in sent_message
    assert f"`{project_name}`" in sent_message


# === Proactive Messaging Support (Issue #30) ===

@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service.set_user_chat_id_mapping", new_callable=AsyncMock)
@patch("app.services.chat_service.redis_service.get_current_project", new_callable=AsyncMock)
@patch("app.services.chat_service.redis_service.get_chat_history", new_callable=AsyncMock)
@patch("app.services.chat_service.redis_service.get_user_model_preference", new_callable=AsyncMock)
@patch("app.services.chat_service.redis_service.add_message_to_history", new_callable=AsyncMock)
@patch("app.services.chat_service.tg_service.send_message", new_callable=AsyncMock)
@patch("app.services.chat_service.llm_service.get_llm_reply", new_callable=AsyncMock)
async def test_handle_chat_message_saves_user_chat_id_mapping(
    mock_get_llm_reply,
    mock_send_message,
    mock_add_history,
    mock_get_model_pref,
    mock_get_history,
    mock_get_project,
    mock_set_mapping,
):
    """
    Verifies that handle_chat_message calls redis_service.set_user_chat_id_mapping.
    This version uses "patch where it's used" with full, correct paths.
    """
    from app.models.telegram import Update, Message, Chat, TelegramUser

    # 1. Setup mock return values
    mock_get_project.return_value = "default"
    mock_get_history.return_value = []
    mock_get_model_pref.return_value = None
    mock_get_llm_reply.return_value = "Some reply"

    # 2. Create a valid Update object
    user_id = 98765
    chat_id = 12345
    update_with_user = Update(
        update_id=1,
        message=Message(
            message_id=1,
            date=1612345678,
            chat=Chat(id=chat_id, type="private"),
            text="Hello Bot",
            from_user=TelegramUser(id=user_id, is_bot=False, first_name="Test User")
        )
    )

    # 3. Call the function under test
    await handle_chat_message(update_with_user)

    # 4. Assert that the target mock was called correctly
    mock_set_mapping.assert_called_once_with(
        user_id=user_id,
        chat_id=chat_id
    )
    mock_send_message.assert_called_once()
