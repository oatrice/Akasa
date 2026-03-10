import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.services.chat_service import handle_chat_message
from app.models.telegram import Update, Message, Chat
from app.models.github import GitHubPR
from app.config import settings

@pytest.fixture
def mock_update_base():
    return Update(
        update_id=1,
        message=Message(
            message_id=1,
            date=1612345678,
            chat=Chat(id=12345, type="private"),
            text="dummy text"
        )
    )

@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
@patch("app.services.chat_service.llm_service")
@patch("app.services.chat_service.github_service")
async def test_handle_chat_message_with_create_issue_tool_call(mock_github, mock_llm, mock_telegram, mock_redis, mock_update_base):
    """Test creating a GitHub issue via tool call."""
    chat_id = 12345
    mock_update = mock_update_base
    mock_update.message.text = "สร้าง issue ใน oatrice/Akasa"

    mock_redis.get_current_project = AsyncMock(return_value="oatrice/Akasa")
    mock_redis.get_user_model_preference = AsyncMock(return_value=None)
    mock_redis.get_chat_history = AsyncMock(return_value=[])
    mock_redis.add_message_to_history = AsyncMock()
    mock_redis.set_user_chat_id_mapping = AsyncMock()
    
    tool_call = {
        "id": "call_1",
        "type": "function",
        "function": {
            "name": "create_github_issue",
            "arguments": '{"repo": "oatrice/Akasa", "title": "Test Issue", "body": "Test Body"}'
        }
    }
    
    mock_llm.get_llm_reply = AsyncMock(side_effect=[
        {"role": "assistant", "content": None, "tool_calls": [tool_call]},
        "สร้าง Issue ให้เรียบร้อยแล้วค่ะ"
    ])

    mock_github.create_issue = MagicMock(return_value="https://github.com/oatrice/Akasa/issues/1")
    mock_telegram.send_message = AsyncMock()

    await handle_chat_message(mock_update)

    mock_github.create_issue.assert_called_once_with(
        repo="oatrice/Akasa", title="Test Issue", body="Test Body"
    )
    assert "สร้าง Issue ให้เรียบร้อยแล้วค่ะ" in mock_telegram.send_message.call_args[0][1]


@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
@patch("app.services.chat_service.llm_service")
@patch("app.services.chat_service.github_service")
async def test_handle_chat_message_with_list_prs_tool_call(mock_github, mock_llm, mock_telegram, mock_redis, mock_update_base):
    """Test listing PRs via tool call, ensuring author is displayed."""
    chat_id = 12345
    mock_update = mock_update_base
    mock_update.message.text = "ขอดู PR ของ oatrice/Akasa"

    mock_redis.get_current_project = AsyncMock(return_value="oatrice/Akasa")
    mock_redis.get_user_model_preference = AsyncMock(return_value=None)
    mock_redis.get_chat_history = AsyncMock(return_value=[])
    mock_redis.add_message_to_history = AsyncMock()
    mock_redis.set_user_chat_id_mapping = AsyncMock()
    
    tool_call = {
        "id": "call_2",
        "type": "function",
        "function": {
            "name": "list_github_open_prs",
            "arguments": '{"repo": "oatrice/Akasa"}'
        }
    }
    
    mock_llm.get_llm_reply = AsyncMock(side_effect=[
        {"role": "assistant", "content": None, "tool_calls": [tool_call]},
        "นี่คือรายการ PR ค่ะ"
    ])

    # Mock PR with author
    sample_pr = GitHubPR(
        number=10, 
        title="New Feature", 
        state="open", 
        url="https://github.com/oatrice/Akasa/pull/10",
        author={"login": "developer_chan"}
    )
    mock_github.get_pr_status = MagicMock(return_value=[sample_pr])
    mock_telegram.send_message = AsyncMock()

    await handle_chat_message(mock_update)

    # Verify tool results sent back to LLM contains author
    second_call_msgs = mock_llm.get_llm_reply.call_args_list[1][0][0]
    tool_msg = next(msg for msg in second_call_msgs if msg["role"] == "tool")
    assert "developer_chan" in tool_msg["content"]
    assert "#10: New Feature" in tool_msg["content"]


@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
@patch("app.services.chat_service.llm_service")
@patch("app.services.chat_service.github_service")
async def test_handle_chat_message_with_create_comment_tool_call(mock_github, mock_llm, mock_telegram, mock_redis, mock_update_base):
    """Test creating a GitHub comment via tool call."""
    chat_id = 12345
    mock_update = mock_update_base
    mock_update.message.text = "คอมเมนต์ใน PR #10 ว่า 'Good job'"

    mock_redis.get_current_project = AsyncMock(return_value="oatrice/Akasa")
    mock_redis.get_user_model_preference = AsyncMock(return_value=None)
    mock_redis.get_chat_history = AsyncMock(return_value=[])
    mock_redis.add_message_to_history = AsyncMock()
    mock_redis.set_user_chat_id_mapping = AsyncMock()
    
    tool_call = {
        "id": "call_3",
        "type": "function",
        "function": {
            "name": "create_github_comment",
            "arguments": '{"repo": "oatrice/Akasa", "issue_number": 10, "body": "Good job"}'
        }
    }
    
    mock_llm.get_llm_reply = AsyncMock(side_effect=[
        {"role": "assistant", "content": None, "tool_calls": [tool_call]},
        "คอมเมนต์ให้แล้วค่ะ"
    ])

    mock_github.create_comment = MagicMock(return_value="https://github.com/oatrice/Akasa/issues/10#issuecomment-123")
    mock_telegram.send_message = AsyncMock()

    await handle_chat_message(mock_update)

    mock_github.create_comment.assert_called_once_with(
        repo="oatrice/Akasa", issue_number=10, body="Good job"
    )
    assert "คอมเมนต์ให้แล้วค่ะ" in mock_telegram.send_message.call_args[0][1]


@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
@patch("app.services.chat_service.llm_service")
@patch("app.services.chat_service.github_service")
async def test_handle_chat_message_with_close_issue_tool_call(mock_github, mock_llm, mock_telegram, mock_redis, mock_update_base):
    """Test closing a GitHub issue via tool call."""
    mock_update = mock_update_base
    mock_update.message.text = "ปิด issue #10 ใน oatrice/Akasa"

    mock_redis.get_current_project = AsyncMock(return_value="oatrice/Akasa")
    mock_redis.get_user_model_preference = AsyncMock(return_value=None)
    mock_redis.get_chat_history = AsyncMock(return_value=[])
    mock_redis.add_message_to_history = AsyncMock()
    mock_redis.set_user_chat_id_mapping = AsyncMock()
    
    tool_call = {
        "id": "call_4",
        "type": "function",
        "function": {
            "name": "close_github_issue",
            "arguments": '{"repo": "oatrice/Akasa", "issue_number": 10}'
        }
    }
    
    mock_llm.get_llm_reply = AsyncMock(side_effect=[
        {"role": "assistant", "content": None, "tool_calls": [tool_call]},
        "ปิด Issue ให้แล้วค่ะ"
    ])

    mock_github.close_issue = MagicMock(return_value="Successfully closed issue #10")
    mock_telegram.send_message = AsyncMock()

    await handle_chat_message(mock_update)

    mock_github.close_issue.assert_called_once_with(repo="oatrice/Akasa", issue_number=10)


@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
@patch("app.services.chat_service.llm_service")
@patch("app.services.chat_service.github_service")
async def test_handle_chat_message_with_delete_issue_tool_call(mock_github, mock_llm, mock_telegram, mock_redis, mock_update_base):
    """Test deleting a GitHub issue via tool call."""
    mock_update = mock_update_base
    mock_update.message.text = "ลบ issue #10 ใน oatrice/Akasa ทิ้งเลย"

    mock_redis.get_current_project = AsyncMock(return_value="oatrice/Akasa")
    mock_redis.get_user_model_preference = AsyncMock(return_value=None)
    mock_redis.get_chat_history = AsyncMock(return_value=[])
    mock_redis.add_message_to_history = AsyncMock()
    mock_redis.set_user_chat_id_mapping = AsyncMock()
    
    tool_call = {
        "id": "call_5",
        "type": "function",
        "function": {
            "name": "delete_github_issue",
            "arguments": '{"repo": "oatrice/Akasa", "issue_number": 10}'
        }
    }
    
    mock_llm.get_llm_reply = AsyncMock(side_effect=[
        {"role": "assistant", "content": None, "tool_calls": [tool_call]},
        "ลบ Issue ให้ถาวรแล้วค่ะ"
    ])

    mock_github.delete_issue = MagicMock(return_value="Successfully deleted issue #10")
    mock_telegram.send_message = AsyncMock()

    await handle_chat_message(mock_update)

    mock_github.delete_issue.assert_called_once_with(repo="oatrice/Akasa", issue_number=10)


@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
@patch("app.services.chat_service.llm_service")
@patch("app.services.chat_service.github_service")
async def test_handle_chat_message_saves_full_tool_context_to_history(mock_github, mock_llm, mock_telegram, mock_redis, mock_update_base):
    """
    Verify that the full conversational turn (user prompt, tool call, tool result, and final reply)
    is saved to Redis history.
    """
    mock_update = mock_update_base
    mock_update.message.text = "สร้าง issue ใน Akasa"

    mock_redis.get_current_project = AsyncMock(return_value="default")
    mock_redis.get_user_model_preference = AsyncMock(return_value=None)
    mock_redis.get_chat_history = AsyncMock(return_value=[])
    mock_redis.add_message_to_history = AsyncMock()
    mock_redis.set_user_chat_id_mapping = AsyncMock()
    
    tool_call = {
        "id": "call_999",
        "type": "function",
        "function": {
            "name": "create_github_issue",
            "arguments": '{"repo": "oatrice/Akasa", "title": "Context Test", "body": "Testing history"}'
        }
    }
    
    mock_llm.get_llm_reply = AsyncMock(side_effect=[
        {"role": "assistant", "content": None, "tool_calls": [tool_call]},
        "สร้าง Issue ให้เรียบร้อยแล้วค่ะ (พร้อมจำบริบท)"
    ])

    mock_github.create_issue = MagicMock(return_value="https://github.com/oatrice/Akasa/issues/999")
    mock_telegram.send_message = AsyncMock()

    await handle_chat_message(mock_update)

    # ตรวจสอบว่ามีการบันทึกประวัติครบ 4 ขั้นตอน (ปัจจุบันจะมีแค่ 2 คือ user กับ assistant ตัวสุดท้าย)
    # 1. User Prompt
    # 2. Assistant Tool Call
    # 3. Tool Result
    # 4. Assistant Final Reply
    
    calls = mock_redis.add_message_to_history.call_args_list
    roles_saved = [call[0][1] for call in calls]
    
    assert "user" in roles_saved
    assert "assistant" in roles_saved
    assert "tool" in roles_saved
    assert roles_saved.count("assistant") >= 2 # หนึ่งในนั้นต้องมี tool_calls
