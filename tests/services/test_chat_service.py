import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.services.chat_service import handle_chat_message
from app.models.telegram import Update, Message, Chat
from app.config import settings
from app.exceptions import LLMTimeoutError, LLMUpstreamError, LLMMalformedResponseError
import httpx

@pytest.fixture(autouse=True)
def set_production_env():
    """บังคับให้ทุก test รันใน environment = production ยกเว้น test ที่ระบุเป็นอย่างอื่นชัดเจน"""
    original_env = getattr(settings, "ENVIRONMENT", "production")
    settings.ENVIRONMENT = "production"
    yield
    settings.ENVIRONMENT = original_env


@pytest.fixture(autouse=True)
def allow_telegram_rate_limit():
    with patch(
        "app.services.chat_service.rate_limiter.check_telegram_message_rate_limit",
        new_callable=AsyncMock,
        return_value=(True, 0),
    ) as mock_rate_limit:
        yield mock_rate_limit

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
    mock_redis.get_project_path = AsyncMock(return_value=None)
    mock_redis.get_project_repo = AsyncMock(return_value=None)
    mock_redis.set_current_project = AsyncMock()
    return mock_redis


# === Slash Command Aliases ===

@pytest.mark.asyncio
@patch("app.services.chat_service._handle_project_command", new_callable=AsyncMock)
async def test_project_alias_dispatches_to_project_handler(mock_handle_project):
    update = Update(
        update_id=101,
        message=Message(
            message_id=101,
            date=1612345678,
            chat=Chat(id=12345, type="private"),
            text="/pj status",
        ),
    )

    await handle_chat_message(update)

    mock_handle_project.assert_awaited_once_with(12345, ["status"])


@pytest.mark.asyncio
@patch("app.services.chat_service._handle_github_command", new_callable=AsyncMock)
async def test_github_alias_dispatches_to_github_handler(mock_handle_github):
    update = Update(
        update_id=102,
        message=Message(
            message_id=102,
            date=1612345678,
            chat=Chat(id=12345, type="private"),
            text="/gh issues oatrice/Akasa",
        ),
    )

    await handle_chat_message(update)

    mock_handle_github.assert_awaited_once_with(12345, ["issues", "oatrice/Akasa"])


@pytest.mark.asyncio
@patch("app.services.chat_service._handle_queue_command", new_callable=AsyncMock)
async def test_queue_alias_dispatches_to_queue_handler(mock_handle_queue):
    update = Update(
        update_id=103,
        message=Message(
            message_id=103,
            date=1612345678,
            chat=Chat(id=12345, type="private"),
            text='/q gemini check_status {}',
        ),
    )

    await handle_chat_message(update)

    assert mock_handle_queue.await_count == 1
    call_args = mock_handle_queue.await_args.args
    assert call_args[0] == update.message
    assert call_args[1] == ["gemini", "check_status", "{}"]


@pytest.mark.asyncio
@patch("app.services.chat_service.command_queue_service")
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
async def test_queue_gemini_command_uses_bound_project_path_as_cwd(
    mock_telegram,
    mock_redis,
    mock_command_queue,
):
    from app.models.command import CommandQueueResponse

    project_path = "/Users/oatrice/Software-projects/Akasa"
    mock_redis.set_user_chat_id_mapping = AsyncMock()
    mock_redis.get_current_project = AsyncMock(return_value="akasa")
    mock_redis.get_project_path = AsyncMock(return_value=project_path)
    mock_command_queue.check_rate_limit = AsyncMock(return_value=(True, 0))
    mock_command_queue.enqueue_command = AsyncMock(
        return_value=CommandQueueResponse(
            command_id="cmd_cwd",
            status="queued",
            tool="gemini",
            command="check_status",
            cwd=project_path,
            queued_at="2026-03-21T00:00:00Z",
            expires_at="2026-03-21T00:05:00Z",
        )
    )
    mock_telegram.send_message = AsyncMock()

    update = Update(
        update_id=104,
        message=Message(
            message_id=104,
            date=1612345678,
            chat=Chat(id=12345, type="private"),
            text="/queue gemini check_status {}",
        ),
    )

    await handle_chat_message(update)

    request = mock_command_queue.enqueue_command.await_args.args[0]
    assert request.cwd == project_path
    sent_message = mock_telegram.send_message.call_args[0][1]
    assert "cmd_cwd" in sent_message
    # Path is MarkdownV2-escaped (hyphens become \-), check non-hyphen segment instead
    assert "Akasa" in sent_message
    assert "akasa" in sent_message


@pytest.mark.asyncio
@patch("app.services.chat_service.command_queue_service")
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
async def test_gemini_command_enqueues_run_task_for_current_project(
    mock_telegram,
    mock_redis,
    mock_command_queue,
):
    from app.models.command import CommandQueueResponse

    project_path = "/Users/oatrice/Software-projects/Akasa"
    mock_redis.set_user_chat_id_mapping = AsyncMock()
    mock_redis.get_current_project = AsyncMock(return_value="akasa")
    mock_redis.get_project_path = AsyncMock(return_value=project_path)
    mock_command_queue.check_rate_limit = AsyncMock(return_value=(True, 0))
    mock_command_queue.enqueue_command = AsyncMock(
        return_value=CommandQueueResponse(
            command_id="cmd_gemini",
            status="queued",
            tool="gemini",
            command="run_task",
            cwd=project_path,
            queued_at="2026-03-21T00:00:00Z",
            expires_at="2026-03-21T00:05:00Z",
        )
    )
    mock_telegram.send_message = AsyncMock()

    update = Update(
        update_id=105,
        message=Message(
            message_id=105,
            date=1612345678,
            chat=Chat(id=12345, type="private"),
            text="/gemini inspect the current local repo",
        ),
    )

    await handle_chat_message(update)

    request = mock_command_queue.enqueue_command.await_args.args[0]
    assert request.command == "run_task"
    assert request.args == {"task": "inspect the current local repo"}
    assert request.cwd == project_path
    sent_message = mock_telegram.send_message.call_args[0][1]
    assert "cmd_gemini" in sent_message


@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
async def test_github_help_prefers_gh_commands(mock_telegram, mock_redis):
    mock_redis.set_user_chat_id_mapping = AsyncMock()
    mock_telegram.send_message = AsyncMock()

    update = Update(
        update_id=104,
        message=Message(
            message_id=104,
            date=1612345678,
            chat=Chat(id=12345, type="private"),
            text="/gh",
        ),
    )

    await handle_chat_message(update)

    sent_message = mock_telegram.send_message.call_args[0][1]
    assert "/gh kanban" in sent_message
    assert "/gh roadmap" in sent_message
    assert "/github repo" not in sent_message


@pytest.mark.asyncio
@patch("app.services.chat_service.github_service")
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
async def test_github_kanban_command_uses_current_project_context(
    mock_telegram,
    mock_redis,
    mock_github,
):
    mock_redis.get_current_project = AsyncMock(return_value="oatrice/Akasa")
    mock_redis.get_project_path = AsyncMock(return_value=None)
    mock_redis.get_project_repo = AsyncMock(return_value=None)
    mock_redis.set_user_chat_id_mapping = AsyncMock()
    mock_github.get_repo_kanban_summary = MagicMock(
        return_value={
            "repo": "oatrice/Akasa",
            "source": "open_issues",
            "issues": [
                {"number": 82, "title": "Add kanban command", "url": "https://github.com/oatrice/Akasa/issues/82"}
            ],
        }
    )
    mock_telegram.send_message = AsyncMock()

    update = Update(
        update_id=105,
        message=Message(
            message_id=105,
            date=1612345678,
            chat=Chat(id=12345, type="private"),
            text="/gh kanban",
        ),
    )

    await handle_chat_message(update)

    mock_github.get_repo_kanban_summary.assert_called_once_with("oatrice/Akasa")
    sent_message = mock_telegram.send_message.call_args[0][1]
    assert "Kanban for oatrice/Akasa" in sent_message
    assert "open issues fallback" in sent_message


@pytest.mark.asyncio
@patch("app.services.chat_service.github_service")
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
async def test_current_work_shortcut(
    mock_telegram,
    mock_redis,
    mock_github,
):
    mock_redis.get_current_project = AsyncMock(return_value="oatrice/Akasa")
    mock_redis.get_project_path = AsyncMock(return_value="/mock/path/Akasa")
    mock_redis.get_project_repo = AsyncMock(return_value="oatrice/Akasa")
    mock_redis.set_user_chat_id_mapping = AsyncMock()

    mock_github.get_local_luma_state = MagicMock(return_value={
        "phase": "Execution",
        "active_branch": "feature/shortcut",
        "active_issues": [{"number": 82, "title": "Add kanban"}]
    })
    mock_github.get_local_git_history = MagicMock(return_value="abcdef1 Commit")
    mock_github.get_repo_kanban_summary = MagicMock(
        return_value={
            "repo": "oatrice/Akasa",
            "columns": [{"name": "In Progress", "count": 1, "items": [{"number": 82, "title": "Add kanban"}]}]
        }
    )
    mock_redis.get_user_model_preference = AsyncMock(return_value=None)
    mock_redis.get_chat_history = AsyncMock(return_value=[])
    mock_redis.add_message_to_history = AsyncMock()
    mock_redis.redis_pool = AsyncMock()
    mock_redis.redis_pool.set = AsyncMock()
    mock_telegram.send_message = AsyncMock()

    update = Update(
        update_id=106,
        message=Message(
            message_id=106,
            date=1612345678,
            chat=Chat(id=12345, type="private"),
            text="ตอนนี้โปรเจ็คทำอะไรอยู่",
        ),
    )

    await handle_chat_message(update)

    sent_message = (
        mock_telegram.send_message.call_args.kwargs.get("text")
        or mock_telegram.send_message.call_args.args[1]
        if mock_telegram.send_message.call_args.args else None
    )
    if not sent_message:
        sent_message = mock_telegram.send_message.call_args.args[1]
    assert "Current Work Status" in sent_message
    assert "Luma State" in sent_message
    assert "Execution" in sent_message
    assert "abcdef1 Commit" in sent_message
    assert "In Progress" in sent_message
    # Should also send with inline keyboard containing summary button
    call_kwargs = mock_telegram.send_message.call_args.kwargs
    assert "reply_markup" in call_kwargs
    assert call_kwargs["reply_markup"]["inline_keyboard"][0][0]["text"] == "\U0001f916 \u0e2a\u0e23\u0e38\u0e1b\u0e43\u0e2b\u0e49\u0e1f\u0e31\u0e07\u0e2b\u0e19\u0e48\u0e2d\u0e22"


@pytest.mark.asyncio
@patch("app.services.chat_service.llm_service")
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
async def test_current_work_summary_callback(
    mock_telegram,
    mock_redis,
    mock_llm,
):
    """When user taps the \U0001f916 summary button, bot fetches cached data and asks LLM to summarize."""
    from app.services.chat_service import _handle_current_work_summary_callback
    from app.models.telegram import CallbackQuery, TelegramUser, Chat, Message

    # --- RED: define expected behaviour ---
    # Setup mocks
    mock_redis.redis_pool = AsyncMock()
    mock_redis.redis_pool.get = AsyncMock(return_value="Luma State\nPhase: coding\nGit: abc1234")
    mock_redis.get_user_model_preference = AsyncMock(return_value=None)
    mock_telegram.edit_message_text = AsyncMock()
    mock_telegram.send_message = AsyncMock()
    mock_llm.get_llm_reply = AsyncMock(return_value="ตอนนี้โปรเจ็คกำลัง coding อยู่ครับ")

    callback = CallbackQuery.model_validate({
        "id": "cb1",
        "data": "current_work_summary:12345:myproject",
        "from": {"id": 9, "first_name": "Test"},
        "message": {
            "message_id": 200,
            "date": 1612345678,
            "chat": {"id": 12345, "type": "private"},
            "text": "\U0001f4ca Current Work Status",
        },
    })

    # --- GREEN: call the handler and verify ---
    await _handle_current_work_summary_callback(callback)

    # LLM should have been called with the raw cached data in the user message
    assert mock_llm.get_llm_reply.called
    call_args = mock_llm.get_llm_reply.call_args
    messages = call_args[0][0]
    user_msg = next(m for m in messages if m["role"] == "user")
    assert "Luma State" in user_msg["content"]
    # A final reply should have been sent to the chat
    assert mock_telegram.send_message.called



@pytest.mark.asyncio
@patch("app.services.chat_service.github_service")
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
async def test_github_roadmap_command_uses_bound_path_and_derived_repo(
    mock_telegram,
    mock_redis,
    mock_github,
):
    roadmap_content = "# Roadmap\n\n## Phase 1\n| # | Issue | Status |\n|---|---|---|\n| 1 | Bot | ✅ Complete |\n"

    mock_redis.get_current_project = AsyncMock(return_value="akasa")
    mock_redis.get_project_path = AsyncMock(return_value="/Users/oatrice/Software-projects/Akasa")
    mock_redis.get_project_repo = AsyncMock(return_value=None)
    mock_redis.set_user_chat_id_mapping = AsyncMock()
    mock_github.get_repo_from_local_path = MagicMock(return_value="oatrice/Akasa")
    mock_github.get_local_roadmap_content = MagicMock(
        return_value=("/Users/oatrice/Software-projects/Akasa/docs/ROADMAP.md", roadmap_content)
    )
    mock_telegram.send_message = AsyncMock()

    update = Update(
        update_id=106,
        message=Message(
            message_id=106,
            date=1612345678,
            chat=Chat(id=12345, type="private"),
            text="/gh roadmap",
        ),
    )

    await handle_chat_message(update)

    mock_github.get_repo_from_local_path.assert_called_once_with(
        "/Users/oatrice/Software-projects/Akasa"
    )
    mock_github.get_local_roadmap_content.assert_called_once_with(
        "/Users/oatrice/Software-projects/Akasa"
    )
    sent_message = mock_telegram.send_message.call_args[0][1]
    assert "Roadmap for oatrice/Akasa" in sent_message
    assert "Source: local" in sent_message


@pytest.mark.asyncio
@patch("app.services.chat_service.github_service")
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
async def test_github_roadmap_command_prefers_bound_repo_when_path_points_elsewhere(
    mock_telegram,
    mock_redis,
    mock_github,
):
    remote_roadmap_content = "# Roadmap\n\n## Metadata\n- Keep schema aligned\n"

    mock_redis.get_current_project = AsyncMock(return_value="the-middle-way")
    mock_redis.get_project_path = AsyncMock(return_value="/Users/oatrice/Software-projects/TheMiddleWay")
    mock_redis.get_project_repo = AsyncMock(return_value="oatrice/TheMiddleWay-Metadata")
    mock_redis.set_user_chat_id_mapping = AsyncMock()
    mock_github.get_repo_from_local_path = MagicMock(
        return_value="mdwmediaworld072/TheMiddleWay"
    )
    mock_github.get_local_roadmap_content = MagicMock()
    mock_github.get_remote_roadmap_content = MagicMock(
        return_value=(
            "https://github.com/oatrice/TheMiddleWay-Metadata/blob/main/docs/ROADMAP.md",
            remote_roadmap_content,
        )
    )
    mock_telegram.send_message = AsyncMock()

    update = Update(
        update_id=109,
        message=Message(
            message_id=109,
            date=1612345678,
            chat=Chat(id=12345, type="private"),
            text="/gh roadmap",
        ),
    )

    await handle_chat_message(update)

    mock_github.get_local_roadmap_content.assert_not_called()
    mock_github.get_remote_roadmap_content.assert_called_once_with(
        "oatrice/TheMiddleWay-Metadata"
    )
    sent_message = mock_telegram.send_message.call_args[0][1]
    # Response is MarkdownV2-escaped, so hyphens in repo name become \-
    assert "Roadmap for oatrice" in sent_message
    assert "TheMiddleWay" in sent_message
    assert "Metadata" in sent_message
    assert "Source: repository" in sent_message


@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
async def test_project_list_command_lists_projects_with_bound_repo(mock_telegram, mock_redis):
    mock_redis.get_current_project = AsyncMock(return_value="akasa")
    mock_redis.get_project_list = AsyncMock(return_value=["akasa", "luma"])
    mock_redis.get_project_repo = AsyncMock(
        side_effect=lambda _chat_id, project_name: "oatrice/Akasa" if project_name == "akasa" else None
    )
    mock_telegram.send_message = AsyncMock()

    update = Update(
        update_id=107,
        message=Message(
            message_id=107,
            date=1612345678,
            chat=Chat(id=12345, type="private"),
            text="/project list",
        ),
    )

    await handle_chat_message(update)

    sent_message = mock_telegram.send_message.call_args[0][1]
    assert "Available Projects" in sent_message
    assert "`akasa`" in sent_message
    assert "`oatrice/Akasa`" in sent_message


@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
async def test_project_repo_command_binds_current_project_repo(mock_telegram, mock_redis):
    mock_redis.get_current_project = AsyncMock(return_value="akasa")
    mock_redis.set_project_repo = AsyncMock(return_value="oatrice/Akasa")
    mock_telegram.send_message = AsyncMock()

    update = Update(
        update_id=108,
        message=Message(
            message_id=108,
            date=1612345678,
            chat=Chat(id=12345, type="private"),
            text="/project repo oatrice/Akasa",
        ),
    )

    await handle_chat_message(update)

    mock_redis.set_project_repo.assert_awaited_once_with(12345, "akasa", "oatrice/Akasa")
    sent_message = mock_telegram.send_message.call_args[0][1]
    assert "Bound GitHub repo" in sent_message
    assert "`oatrice/Akasa`" in sent_message


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
    """ถ้า Telegram error (non-400) → ไม่ crash, log error แทน"""
    mock_redis.get_current_project = AsyncMock(return_value="default")
    mock_redis.get_user_model_preference = AsyncMock(return_value=None)
    mock_redis.get_chat_history = AsyncMock(return_value=[])
    mock_redis.add_message_to_history = AsyncMock()
    mock_llm.get_llm_reply = AsyncMock(return_value="Reply from AI")
    # Generic HTTP error with response=None (edge case from mock)
    mock_telegram.send_message = AsyncMock(side_effect=httpx.HTTPStatusError("500 Error", request=None, response=None))

    await handle_chat_message(mock_update)
    mock_llm.get_llm_reply.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
@patch("app.services.chat_service.llm_service")
async def test_send_response_fallback_to_plain_text_on_400(mock_llm, mock_telegram, mock_redis, mock_update):
    """🟥 RED → 🟢 GREEN: เมื่อ MarkdownV2 ส่ง 400 → ต้อง fallback ส่ง plain text แทน"""
    from unittest.mock import MagicMock
    
    mock_redis.get_current_project = AsyncMock(return_value="default")
    mock_redis.get_user_model_preference = AsyncMock(return_value=None)
    mock_redis.get_chat_history = AsyncMock(return_value=[])
    mock_redis.add_message_to_history = AsyncMock()
    mock_llm.get_llm_reply = AsyncMock(return_value="Reply with special chars: (1+2) = 3.")
    
    # สร้าง mock response ที่มี status_code = 400 จริงๆ
    mock_response = MagicMock()
    mock_response.status_code = 400
    
    call_count = 0
    async def side_effect_fn(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # ครั้งแรก (MarkdownV2) → fail
            raise httpx.HTTPStatusError("400 Bad Request", request=MagicMock(), response=mock_response)
        # ครั้งที่สอง (plain text) → success
        return None
    
    mock_telegram.send_message = AsyncMock(side_effect=side_effect_fn)

    await handle_chat_message(mock_update)
    
    # send_message ต้องถูกเรียก 2 ครั้ง (MarkdownV2 fail → plain text success)
    assert mock_telegram.send_message.call_count == 2
    # ครั้งที่สอง ต้องส่งด้วย parse_mode=None (plain text)
    second_call = mock_telegram.send_message.call_args_list[1]
    assert second_call.kwargs.get("parse_mode") is None or (len(second_call.args) >= 3 and second_call.args[2] is None)


@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
@patch("app.services.chat_service.llm_service")
async def test_handle_chat_message_timeout(mock_llm, mock_telegram, mock_redis, mock_update):
    """ถ้า LLM timeout → จะส่งข้อความ timeout-friendly กลับไป"""
    mock_redis.get_current_project = AsyncMock(return_value="default")
    mock_redis.get_user_model_preference = AsyncMock(return_value=None)
    mock_redis.get_chat_history = AsyncMock(return_value=[])
    mock_redis.add_message_to_history = AsyncMock()
    mock_llm.get_llm_reply = AsyncMock(side_effect=LLMTimeoutError("Timeout"))
    mock_telegram.send_message = AsyncMock()

    await handle_chat_message(mock_update)
    mock_telegram.send_message.assert_called_once_with(
        12345,
        "ขออภัย คำขอใช้เวลานานเกินไป โปรดลองใหม่อีกครั้งในอีกสักครู่ 🙇‍♂️",
    )
    mock_redis.add_message_to_history.assert_not_called()


@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
@patch("app.services.chat_service.llm_service")
async def test_handle_chat_message_upstream_error(mock_llm, mock_telegram, mock_redis, mock_update):
    mock_redis.get_current_project = AsyncMock(return_value="default")
    mock_redis.get_user_model_preference = AsyncMock(return_value=None)
    mock_redis.get_chat_history = AsyncMock(return_value=[])
    mock_redis.add_message_to_history = AsyncMock()
    mock_llm.get_llm_reply = AsyncMock(side_effect=LLMUpstreamError("Upstream"))
    mock_telegram.send_message = AsyncMock()

    await handle_chat_message(mock_update)
    mock_telegram.send_message.assert_called_once_with(
        12345,
        "ขออภัย ระบบ AI ภายนอกขัดข้องชั่วคราว โปรดลองใหม่อีกครั้งในภายหลัง 🙇‍♂️",
    )
    mock_redis.add_message_to_history.assert_not_called()


@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
@patch("app.services.chat_service.llm_service")
async def test_handle_chat_message_malformed_response_error(mock_llm, mock_telegram, mock_redis, mock_update):
    mock_redis.get_current_project = AsyncMock(return_value="default")
    mock_redis.get_user_model_preference = AsyncMock(return_value=None)
    mock_redis.get_chat_history = AsyncMock(return_value=[])
    mock_redis.add_message_to_history = AsyncMock()
    mock_llm.get_llm_reply = AsyncMock(side_effect=LLMMalformedResponseError("Bad payload"))
    mock_telegram.send_message = AsyncMock()

    await handle_chat_message(mock_update)
    mock_telegram.send_message.assert_called_once_with(
        12345,
        "ขออภัย ระบบไม่สามารถประมวลผลคำตอบจาก AI ได้ 🙇‍♂️",
    )
    mock_redis.add_message_to_history.assert_not_called()


@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
@patch("app.services.chat_service.llm_service")
async def test_handle_chat_message_rate_limited(mock_llm, mock_telegram, mock_redis, mock_update, allow_telegram_rate_limit):
    mock_redis.set_user_chat_id_mapping = AsyncMock()
    mock_telegram.send_message = AsyncMock()
    allow_telegram_rate_limit.return_value = (False, 42)

    await handle_chat_message(mock_update)

    mock_llm.get_llm_reply.assert_not_called()
    mock_telegram.send_message.assert_called_once()
    sent_message = mock_telegram.send_message.call_args[0][1]
    assert "ถี่เกินไป" in sent_message
    assert "42" in sent_message

@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
@patch("app.services.chat_service.llm_service")
async def test_send_response_chunks_long_messages(mock_llm, mock_telegram, mock_redis, mock_update):
    """🟥 RED → 🟢 GREEN: ข้อความที่ยาวเกิน 4000 ตัวอักษร ต้องถูกแบ่งออกเป็นหลายๆ ข้อความ"""
    mock_redis.get_current_project = AsyncMock(return_value="default")
    mock_redis.get_user_model_preference = AsyncMock(return_value=None)
    mock_redis.get_chat_history = AsyncMock(return_value=[])
    mock_redis.add_message_to_history = AsyncMock()
    
    # สร้างข้อความยาว 9000 ตัวอักษร
    long_reply = "A" * 9000
    mock_llm.get_llm_reply = AsyncMock(return_value=long_reply)
    mock_telegram.send_message = AsyncMock(return_value=None)

    await handle_chat_message(mock_update)
    
    # ความยาว 9000 ตัวอักษร ถูกแบ่งเป็น 4000, 4000, 1000 -> ส่ง 3 ครั้ง (ไม่รวม Local Dev Info)
    # แต่เนื่องจากอาจมี Local Dev Info ต่อท้าย ทำให้ความยาวเพิ่มขึ้น เราจึง assert ว่าส่งมากกว่า 1 ครั้งก็พอ
    assert mock_telegram.send_message.call_count >= 3
    # ตรวจสอบว่าไม่ควรมีข้อความไหนที่ความยาวเกิน 4096 (Telegram Limit)
    for call in mock_telegram.send_message.call_args_list:
        text_sent = call.args[1] if len(call.args) > 1 else call.kwargs.get("text", "")
        assert len(text_sent) <= 4096
    mock_redis.add_message_to_history = AsyncMock()
    mock_llm.get_llm_reply = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
    mock_telegram.send_message = AsyncMock()

    await handle_chat_message(mock_update)
    mock_telegram.send_message.assert_called_once_with(12345, "ขออภัย ระบบขัดข้องชั่วคราวในการตอบสนอง 🙇‍♂️")
    mock_redis.add_message_to_history.assert_not_called()

@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
async def test_testsource_command_sends_task_notification(mock_telegram, mock_redis):
    """พิมพ์ /testsource <source> ใน Telegram → ต้องส่ง task notification ทันที"""
    mock_redis.get_current_project = AsyncMock(return_value="akasa")
    mock_telegram.send_task_notification = AsyncMock(return_value=None)

    update = Update(
        update_id=999,
        message=Message(
            message_id=999,
            date=1612345678,
            chat=Chat(id=777, type="private"),
            text="/testsource Cursor",
        ),
    )

    await handle_chat_message(update)

    mock_telegram.send_task_notification.assert_called_once()
    call_kwargs = mock_telegram.send_task_notification.call_args.kwargs
    assert call_kwargs["chat_id"] == 777
    req = call_kwargs["request"]
    assert req.project == "akasa"
    assert req.status == "success"
    assert req.source == "Cursor"
    assert req.chat_id == "777"


@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
async def test_testsource_command_usage_when_missing_arg(mock_telegram, mock_redis):
    """/testsource ไม่มี arg → ส่ง usage กลับไป"""
    mock_telegram.send_message = AsyncMock(return_value=None)

    update = Update(
        update_id=1000,
        message=Message(
            message_id=1000,
            date=1612345678,
            chat=Chat(id=777, type="private"),
            text="/testsource",
        ),
    )

    await handle_chat_message(update)

    mock_telegram.send_message.assert_called_once()
    sent = mock_telegram.send_message.call_args[0][1]
    assert "Usage" in sent or "usage" in sent

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

        # send_message ถูกเรียก 1 ครั้ง และข้อความที่ส่งต้องผ่าน escape_markdown_v2 แล้ว
        mock_telegram.send_message.assert_called_once()
        sent_text = mock_telegram.send_message.call_args[0][1]
        # ข้อความที่ส่งต้องมี Build Info ต่อท้าย (escaped)
        assert "Reply from AI" in sent_text
        assert "Local Dev Info" in sent_text
        assert "Version" in sent_text
        assert "Commit" in sent_text
        
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
    # ต้องแจ้งยืนยัน (ข้อความถูก escape_markdown_v2 แล้ว แต่ยังคงเช็คเนื้อหาได้)
    args = mock_telegram.send_message.call_args[0]
    assert "updated" in args[1].lower()
    # เช็คว่ามีชื่อโมเดล (อาจมี escape char เช่น \. แต่ text ยังมีคำหลักอยู่)
    assert "Gemini" in args[1]
    assert "Flash" in args[1]


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
async def test_project_path_command_shows_bound_path(mock_telegram, mock_redis):
    import datetime

    chat_id = 2003
    now = datetime.datetime.now(datetime.timezone.utc)

    mock_redis.get_current_project = AsyncMock(return_value="akasa")
    mock_redis.get_project_path = AsyncMock(
        return_value="/Users/oatrice/Software-projects/Akasa"
    )
    mock_telegram.send_message = AsyncMock()

    update = Update(
        update_id=26,
        message=Message(
            message_id=26,
            date=int(now.timestamp()),
            chat=Chat(id=chat_id, type="private"),
            text="/project path",
        ),
    )

    await handle_chat_message(update)

    mock_redis.get_project_path.assert_awaited_once_with(chat_id, "akasa")
    sent_message = mock_telegram.send_message.call_args[0][1]
    assert "Project path" in sent_message
    assert "/Users/oatrice/Software-projects/Akasa" in sent_message


@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
async def test_project_bind_command_binds_named_project_path(mock_telegram, mock_redis):
    import datetime

    chat_id = 2004
    now = datetime.datetime.now(datetime.timezone.utc)

    mock_redis.get_current_project = AsyncMock(return_value="default")
    mock_redis.set_project_path = AsyncMock(
        return_value="/Users/oatrice/Software-projects/Akasa"
    )
    mock_telegram.send_message = AsyncMock()

    update = Update(
        update_id=27,
        message=Message(
            message_id=27,
            date=int(now.timestamp()),
            chat=Chat(id=chat_id, type="private"),
            text="/project bind akasa /Users/oatrice/Software-projects/Akasa",
        ),
    )

    await handle_chat_message(update)

    mock_redis.set_project_path.assert_awaited_once_with(
        chat_id,
        "akasa",
        "/Users/oatrice/Software-projects/Akasa",
    )
    sent_message = mock_telegram.send_message.call_args[0][1]
    assert "Bound project" in sent_message
    assert "`akasa`" in sent_message


@pytest.mark.asyncio
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
async def test_project_bind_command_defaults_to_current_project_for_path_only(
    mock_telegram,
    mock_redis,
):
    import datetime

    chat_id = 2005
    now = datetime.datetime.now(datetime.timezone.utc)

    mock_redis.get_current_project = AsyncMock(return_value="akasa")
    mock_redis.set_project_path = AsyncMock(
        return_value="/Users/oatrice/Software-projects/My App"
    )
    mock_telegram.send_message = AsyncMock()

    update = Update(
        update_id=28,
        message=Message(
            message_id=28,
            date=int(now.timestamp()),
            chat=Chat(id=chat_id, type="private"),
            text="/project bind /Users/oatrice/Software-projects/My App",
        ),
    )

    await handle_chat_message(update)

    mock_redis.set_project_path.assert_awaited_once_with(
        chat_id,
        "akasa",
        "/Users/oatrice/Software-projects/My App",
    )


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


@pytest.mark.asyncio
@patch("app.services.chat_service.agent_task_service")
@patch("app.services.chat_service.deploy_service")
@patch("app.services.chat_service.command_queue_service")
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
async def test_project_status_command_shows_recent_activity(
    mock_telegram,
    mock_redis,
    mock_command_queue,
    mock_deploy_service,
    mock_agent_task_service,
):
    from app.models.agent_state import AgentState
    from app.models.agent_task import AgentTaskLog
    from app.models.command import CommandStatusResponse
    from app.models.deployment import DeploymentRecord
    import datetime

    chat_id = 2002
    now = datetime.datetime.now(datetime.timezone.utc)

    mock_redis.get_current_project = AsyncMock(return_value="akasa")
    mock_redis.get_project_path = AsyncMock(
        return_value="/Users/oatrice/Software-projects/Akasa"
    )
    mock_redis.get_project_repo = AsyncMock(return_value="oatrice/Akasa")
    mock_redis.get_agent_state = AsyncMock(
        return_value=AgentState(
            current_task="Implement /project status",
            focus_file="app/services/chat_service.py",
            last_activity_timestamp=now,
        )
    )
    mock_redis.get_recent_command_ids = AsyncMock(return_value=["cmd_123"])
    mock_redis.get_recent_deployment_ids = AsyncMock(return_value=["dep_456"])
    mock_redis.get_chat_history = AsyncMock(
        return_value=[{"role": "assistant", "content": "Status summary ready"}]
    )
    mock_telegram.send_message = AsyncMock()

    mock_command_queue.get_command_status = AsyncMock(
        return_value=CommandStatusResponse(
            command_id="cmd_123",
            status="running",
            tool="gemini",
            command="run_task",
            cwd="/Users/oatrice/Software-projects/Akasa",
            queued_at="2026-03-19T10:00:00Z",
        )
    )
    mock_deploy_service.get_deployment = AsyncMock(
        return_value=DeploymentRecord(
            deployment_id="dep_456",
            status="success",
            command="vercel deploy",
            cwd="/tmp/akasa",
            project="akasa",
        )
    )
    mock_agent_task_service.get_tasks_by_project = AsyncMock(
        return_value=[
            AgentTaskLog(
                task_id="task_1",
                project="akasa",
                task="Review ready summary",
                status="starting",
                source="Antigravity",
                chat_id=str(chat_id),
            )
        ]
    )

    update = Update(
        update_id=22,
        message=Message(
            message_id=22,
            date=int(now.timestamp()),
            chat=Chat(id=chat_id, type="private"),
            text="/project status",
        ),
    )

    await handle_chat_message(update)

    mock_telegram.send_message.assert_called_once()
    sent_message = mock_telegram.send_message.call_args[0][1]
    assert "Project Status" in sent_message
    assert "Implement /project status" in sent_message
    assert "cmd_123" in sent_message
    assert "running" in sent_message
    assert "/Users/oatrice/Software-projects/Akasa" in sent_message
    assert "dep_456" in sent_message
    assert "vercel deploy" in sent_message
    assert "Review ready summary" in sent_message
    assert "Last updated" in sent_message
    assert "Bound path" in sent_message
    assert "oatrice/Akasa" in sent_message


@pytest.mark.asyncio
@patch("app.services.chat_service.agent_task_service")
@patch("app.services.chat_service.deploy_service")
@patch("app.services.chat_service.command_queue_service")
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
async def test_projects_overview_command_summarizes_multiple_projects(
    mock_telegram,
    mock_redis,
    mock_command_queue,
    mock_deploy_service,
    mock_agent_task_service,
):
    from app.models.agent_state import AgentState
    from app.models.agent_task import AgentTaskLog
    from app.models.command import CommandStatusResponse
    from app.models.deployment import DeploymentRecord
    import datetime

    now = datetime.datetime.now(datetime.timezone.utc)
    chat_id = 3001

    mock_redis.get_current_project = AsyncMock(return_value="akasa")
    mock_redis.get_project_list = AsyncMock(return_value=["akasa", "luma"])
    async def get_project_repo_side_effect(_chat_id, project_name):
        if project_name == "akasa":
            return "oatrice/Akasa"
        return "oatrice/Luma"

    mock_redis.get_project_repo = AsyncMock(side_effect=get_project_repo_side_effect)
    mock_telegram.send_message = AsyncMock()

    async def get_chat_history_side_effect(_chat_id, project_name="default"):
        if project_name == "akasa":
            return [
                {"role": "user", "content": "Investigate queue behavior"},
                {"role": "assistant", "content": "Queue looks healthy"},
            ]
        return [{"role": "user", "content": "Deploy started"}]

    async def get_agent_state_side_effect(_chat_id, project_name):
        if project_name == "akasa":
            return AgentState(
                current_task="Finish overview command",
                last_activity_timestamp=now,
            )
        return None

    async def get_recent_command_ids_side_effect(_chat_id, project_name, limit=3):
        return ["cmd_akasa"] if project_name == "akasa" else []

    async def get_recent_deployment_ids_side_effect(_chat_id, project_name, limit=3):
        return ["dep_luma"] if project_name == "luma" else []

    async def get_tasks_side_effect(project_name):
        if project_name == "luma":
            return [
                AgentTaskLog(
                    task_id="task_luma",
                    project="luma",
                    task="Review docs",
                    status="partial",
                    source="Luma",
                    chat_id=str(chat_id),
                )
            ]
        return []

    mock_redis.get_agent_state = AsyncMock(side_effect=get_agent_state_side_effect)
    async def get_project_path_side_effect(_chat_id, project_name):
        if project_name == "akasa":
            return "/Users/oatrice/Software-projects/Akasa"
        return "/Users/oatrice/Software-projects/Luma"

    mock_redis.get_project_path = AsyncMock(side_effect=get_project_path_side_effect)
    mock_redis.get_recent_command_ids = AsyncMock(
        side_effect=get_recent_command_ids_side_effect
    )
    mock_redis.get_recent_deployment_ids = AsyncMock(
        side_effect=get_recent_deployment_ids_side_effect
    )
    mock_redis.get_chat_history = AsyncMock(side_effect=get_chat_history_side_effect)
    mock_command_queue.get_command_status = AsyncMock(
        return_value=CommandStatusResponse(
            command_id="cmd_akasa",
            status="queued",
            tool="gemini",
            command="check_status",
            queued_at="2026-03-19T10:00:00Z",
        )
    )
    mock_deploy_service.get_deployment = AsyncMock(
        return_value=DeploymentRecord(
            deployment_id="dep_luma",
            status="running",
            command="render deploy",
            cwd="/tmp/luma",
            project="luma",
        )
    )
    mock_agent_task_service.get_tasks_by_project = AsyncMock(
        side_effect=get_tasks_side_effect
    )

    update = Update(
        update_id=23,
        message=Message(
            message_id=23,
            date=int(now.timestamp()),
            chat=Chat(id=chat_id, type="private"),
            text="/projects overview",
        ),
    )

    await handle_chat_message(update)

    mock_telegram.send_message.assert_called_once()
    sent_message = mock_telegram.send_message.call_args[0][1]
    assert "Projects Overview" in sent_message
    assert "`akasa`" in sent_message
    assert "Finish overview command" in sent_message
    assert "check_status" in sent_message
    assert "`luma`" in sent_message
    assert "render deploy" in sent_message
    assert "Review docs" in sent_message
    assert "Last updated" in sent_message
    assert "History count" in sent_message
    assert "Path:" in sent_message
    assert "GitHub:" in sent_message


@pytest.mark.asyncio
@patch("app.services.chat_service.agent_task_service")
@patch("app.services.chat_service.deploy_service")
@patch("app.services.chat_service.command_queue_service")
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
async def test_projects_overview_verbose_includes_history_snippet(
    mock_telegram,
    mock_redis,
    mock_command_queue,
    mock_deploy_service,
    mock_agent_task_service,
):
    import datetime

    now = datetime.datetime.now(datetime.timezone.utc)
    chat_id = 3002

    mock_redis.get_current_project = AsyncMock(return_value="akasa")
    mock_redis.get_project_list = AsyncMock(return_value=["akasa"])
    mock_redis.get_agent_state = AsyncMock(return_value=None)
    mock_redis.get_project_path = AsyncMock(
        return_value="/Users/oatrice/Software-projects/Akasa"
    )
    mock_redis.get_project_repo = AsyncMock(return_value="oatrice/Akasa")
    mock_redis.get_recent_command_ids = AsyncMock(return_value=[])
    mock_redis.get_recent_deployment_ids = AsyncMock(return_value=[])
    mock_redis.get_chat_history = AsyncMock(
        return_value=[
            {"role": "user", "content": "Can you summarize the deploy status for staging?"}
        ]
    )
    mock_telegram.send_message = AsyncMock()
    mock_command_queue.get_command_status = AsyncMock(return_value=None)
    mock_deploy_service.get_deployment = AsyncMock(return_value=None)
    mock_agent_task_service.get_tasks_by_project = AsyncMock(return_value=[])

    update = Update(
        update_id=24,
        message=Message(
            message_id=24,
            date=int(now.timestamp()),
            chat=Chat(id=chat_id, type="private"),
            text="/projects overview verbose",
        ),
    )

    await handle_chat_message(update)

    mock_telegram.send_message.assert_called_once()
    sent_message = mock_telegram.send_message.call_args[0][1]
    assert "Projects Overview" in sent_message
    assert "Verbose" in sent_message
    assert "History count" in sent_message
    assert "History:" in sent_message
    assert "summarize the deploy status" in sent_message
    assert "Path:" in sent_message
    assert "GitHub:" in sent_message


@pytest.mark.asyncio
@patch("app.services.chat_service.agent_task_service")
@patch("app.services.chat_service.deploy_service")
@patch("app.services.chat_service.command_queue_service")
@patch("app.services.chat_service.redis_service")
@patch("app.services.chat_service.tg_service")
async def test_projects_overview_json_returns_machine_readable_payload(
    mock_telegram,
    mock_redis,
    mock_command_queue,
    mock_deploy_service,
    mock_agent_task_service,
):
    import datetime

    now = datetime.datetime.now(datetime.timezone.utc)
    chat_id = 3003

    mock_redis.get_current_project = AsyncMock(return_value="akasa")
    mock_redis.get_project_list = AsyncMock(return_value=["akasa"])
    mock_redis.get_agent_state = AsyncMock(return_value=None)
    mock_redis.get_project_path = AsyncMock(
        return_value="/Users/oatrice/Software-projects/Akasa"
    )
    mock_redis.get_project_repo = AsyncMock(return_value="oatrice/Akasa")
    mock_redis.get_recent_command_ids = AsyncMock(return_value=[])
    mock_redis.get_recent_deployment_ids = AsyncMock(return_value=[])
    mock_redis.get_chat_history = AsyncMock(
        return_value=[{"role": "assistant", "content": "Latest status snapshot"}]
    )
    mock_telegram.send_message = AsyncMock()
    mock_command_queue.get_command_status = AsyncMock(return_value=None)
    mock_deploy_service.get_deployment = AsyncMock(return_value=None)
    mock_agent_task_service.get_tasks_by_project = AsyncMock(return_value=[])

    update = Update(
        update_id=25,
        message=Message(
            message_id=25,
            date=int(now.timestamp()),
            chat=Chat(id=chat_id, type="private"),
            text="/projects overview json",
        ),
    )

    await handle_chat_message(update)

    mock_telegram.send_message.assert_called_once()
    sent_message = mock_telegram.send_message.call_args[0][1]
    assert "```json" in sent_message
    assert '"current_project": "akasa"' in sent_message
    assert '"history_count": 1' in sent_message
    assert '"history_snippet": null' in sent_message
    assert '"project_path": "/Users/oatrice/Software-projects/Akasa"' in sent_message


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

    # 2. Create a valid Update object, ensuring the 'from' alias is handled
    user_id = 98765
    chat_id = 12345
    update_data = {
        "update_id": 1,
        "message": {
            "message_id": 1,
            "date": 1612345678,
            "chat": {"id": chat_id, "type": "private"},
            "text": "Hello Bot",
            "from": {"id": user_id, "is_bot": False, "first_name": "Test User"}
        }
    }
    update_with_user = Update.parse_obj(update_data)

    # 3. Call the function under test
    await handle_chat_message(update_with_user)

    # 4. Assert that the target mock was called correctly
    mock_set_mapping.assert_called_once_with(
        user_id=user_id,
        chat_id=chat_id
    )
    mock_send_message.assert_called_once()
