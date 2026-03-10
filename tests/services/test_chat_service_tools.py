import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.services.chat_service import handle_chat_message
from app.models.telegram import Update, Message, Chat
from app.config import settings

@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
@patch("app.services.chat_service.llm_service")
@patch("app.services.chat_service.github_service")
async def test_handle_chat_message_with_github_tool_call(mock_github, mock_llm, mock_telegram, mock_redis):
    """
    Test Case: User requests to create a GitHub issue.
    LLM returns a tool call -> ChatService executes it via GithubService -> LLM summarizes result.
    """
    # 1. Setup Mock Data
    chat_id = 12345
    mock_update = Update(
        update_id=1,
        message=Message(
            message_id=1,
            date=1612345678,
            chat=Chat(id=chat_id, type="private"),
            text="ช่วยสร้าง issue ใน oatrice/Akasa หัวข้อ 'Test Issue' เนื้อหา 'Test Body' หน่อย"
        )
    )

    mock_redis.get_current_project = AsyncMock(return_value="oatrice/Akasa")
    mock_redis.get_user_model_preference = AsyncMock(return_value=None)
    mock_redis.get_chat_history = AsyncMock(return_value=[])
    mock_redis.add_message_to_history = AsyncMock()
    mock_redis.set_user_chat_id_mapping = AsyncMock()
    
    # จำลอง LLM คืนค่า Tool Call ในรอบแรก
    tool_call = {
        "id": "call_123",
        "type": "function",
        "function": {
            "name": "create_github_issue",
            "arguments": '{"repo": "oatrice/Akasa", "title": "Test Issue", "body": "Test Body"}'
        }
    }
    
    # รอบแรกคืน Tool Call, รอบสองคืนคำตอบสรุป
    mock_llm.get_llm_reply = AsyncMock(side_effect=[
        {"role": "assistant", "content": None, "tool_calls": [tool_call]}, # รอบที่ 1: ตรวจเจอ Intent
        "สร้าง Issue ให้เรียบร้อยแล้วครับที่ https://github.com/oatrice/Akasa/issues/1" # รอบที่ 2: สรุปผล
    ])

    # Mock GithubService
    mock_github.create_issue = MagicMock(return_value="https://github.com/oatrice/Akasa/issues/1")
    
    # Mock Telegram Service
    mock_telegram.send_message = AsyncMock()

    # 2. Execute
    await handle_chat_message(mock_update)

    # 3. Assertions
    # ตรวจสอบว่า GithubService.create_issue ถูกเรียกจริง
    mock_github.create_issue.assert_called_once_with(
        repo="oatrice/Akasa",
        title="Test Issue",
        body="Test Body"
    )

    # ตรวจสอบว่ามีการเรียก LLM 2 ครั้ง
    assert mock_llm.get_llm_reply.call_count == 2
    
    # ตรวจสอบว่ามีการส่งผลลัพธ์ Tool กลับไปให้ LLM ในรอบที่ 2
    second_call_messages = mock_llm.get_llm_reply.call_args_list[1][0][0]
    assert any(msg["role"] == "tool" for msg in second_call_messages)
    assert "https://github.com/oatrice/Akasa/issues/1" in str(second_call_messages)

    # ตรวจสอบว่ามีการส่งข้อความสุดท้ายให้ User (ตรวจสอบแค่เนื้อหาหลัก เพราะอาจมี Dev Info ต่อท้าย)
    sent_text = mock_telegram.send_message.call_args[0][1]
    assert "สร้าง Issue ให้เรียบร้อยแล้วครับที่ https://github.com/oatrice/Akasa/issues/1" in sent_text
