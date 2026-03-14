import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.config import settings

# Import the instance, not the class or old function
from app.services.telegram_service import tg_service


@pytest.mark.asyncio
async def test_send_message_success(monkeypatch):
    # Use monkeypatch to control the API URL for the test
    test_api_url = "https://api.telegram.org/bot_test_bot_token"
    monkeypatch.setattr(tg_service, "api_url", test_api_url)

    chat_id = 12345
    text = "Hello from AI (v1.0)"

    expected_text = r"Hello from AI \(v1\.0\)"

    # Directly patch the 'post' method on the service's client instance
    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        # Configure the mock to return a successful response
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        # Call the method we are testing
        await tg_service.send_message(chat_id, text)

        # Assert that the 'post' method was called correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args

        # Check the URL it was called with
        assert f"{test_api_url}/sendMessage" in call_args.args

        # Check the JSON payload
        request_data = call_args.kwargs["json"]
        assert request_data["chat_id"] == chat_id
        assert request_data["text"] == expected_text
        assert request_data.get("parse_mode") == "MarkdownV2"


@pytest.mark.asyncio
async def test_send_message_error(monkeypatch):
    # Use monkeypatch to control the API URL for the test
    test_api_url = "https://api.telegram.org/bot_test_bot_token"
    monkeypatch.setattr(tg_service, "api_url", test_api_url)

    chat_id = 12345
    text = "Hello from AI"

    # Directly patch the 'post' method on the service's client instance
    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        # This setup is a bit complex, let's simplify by having the mock itself raise the error
        mock_post.side_effect = httpx.HTTPStatusError(
            "Bad Request",
            request=AsyncMock(),
            response=httpx.Response(
                400, json={"ok": False, "description": "Bad Request: chat not found"}
            ),
        )

        # Calling the service method should now raise the exception
        with pytest.raises(httpx.HTTPStatusError):
            await tg_service.send_message(chat_id, text)

        # Verify the call was made to the correct URL
        mock_post.assert_called_once_with(
            f"{test_api_url}/sendMessage",
            json={
                "chat_id": 12345,
                "text": "Hello from AI",
                "parse_mode": "MarkdownV2",
            },
            timeout=10.0,
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

    with patch.object(
        tg_service, "send_message", new_callable=AsyncMock
    ) as mock_send_message:
        await tg_service.send_proactive_message(user_id, text)

        mock_redis.get_chat_id_for_user.assert_called_once_with(user_id)
        mock_send_message.assert_called_once_with(chat_id=chat_id, text=text)


@pytest.mark.asyncio
@patch("app.services.telegram_service.redis_service")
async def test_send_proactive_message_user_not_found(mock_redis):
    """Should raise UserChatIdNotFoundException if chat_id is not in Redis."""
    from app.exceptions import UserChatIdNotFoundException

    user_id = 999

    mock_redis.get_chat_id_for_user = AsyncMock(return_value=None)

    with patch.object(
        tg_service, "send_message", new_callable=AsyncMock
    ) as mock_send_message:
        with pytest.raises(UserChatIdNotFoundException):
            await tg_service.send_proactive_message(user_id, "This should fail.")

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
    error_response = httpx.Response(
        403, json={"description": "Forbidden: bot was blocked by the user"}
    )
    side_effect = httpx.HTTPStatusError(
        "Forbidden", request=AsyncMock(), response=error_response
    )

    with patch.object(
        tg_service, "send_message", new_callable=AsyncMock, side_effect=side_effect
    ) as mock_send_message:
        with pytest.raises(BotBlockedException):
            await tg_service.send_proactive_message(user_id, "This will also fail.")

        mock_send_message.assert_called_once()


# === Task Completion Notifications (Issue #61) ===


@pytest.mark.asyncio
async def test_send_task_notification_success(monkeypatch):
    """Happy path: success status sends ✅ emoji with all provided fields."""
    from app.models.notification import TaskNotificationRequest

    monkeypatch.setattr(
        tg_service, "api_url", "https://api.telegram.org/bot_test_token"
    )

    request = TaskNotificationRequest(
        project="Akasa",
        task="Refactor Redis Service",
        status="success",
        duration="5m 20s",
        source="Gemini CLI",
    )

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        await tg_service.send_task_notification(chat_id=12345, request=request)

        mock_post.assert_called_once()
        payload = mock_post.call_args.kwargs["json"]

        assert payload["chat_id"] == 12345
        assert payload["parse_mode"] == "MarkdownV2"
        text = payload["text"]
        assert "✅" in text
        assert "Task Completed" in text
        assert "Akasa" in text
        assert "Refactor Redis Service" in text
        assert "5m 20s" in text
        assert "Gemini CLI" in text


@pytest.mark.asyncio
async def test_send_task_notification_failure_status(monkeypatch):
    """Failure status renders ❌ emoji and 'Task Failed' title."""
    from app.models.notification import TaskNotificationRequest

    monkeypatch.setattr(
        tg_service, "api_url", "https://api.telegram.org/bot_test_token"
    )

    request = TaskNotificationRequest(
        project="MyApp",
        task="Deploy to production",
        status="failure",
    )

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        await tg_service.send_task_notification(chat_id=99999, request=request)

        payload = mock_post.call_args.kwargs["json"]
        assert "❌" in payload["text"]
        assert "Task Failed" in payload["text"]


@pytest.mark.asyncio
async def test_send_task_notification_partial_status(monkeypatch):
    """Partial status renders ⚠️ emoji and 'Completed with Warnings' title."""
    from app.models.notification import TaskNotificationRequest

    monkeypatch.setattr(
        tg_service, "api_url", "https://api.telegram.org/bot_test_token"
    )

    request = TaskNotificationRequest(
        project="Akasa",
        task="Run test suite",
        status="partial",
    )

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        await tg_service.send_task_notification(chat_id=12345, request=request)

        payload = mock_post.call_args.kwargs["json"]
        assert "⚠️" in payload["text"]
        assert "Warnings" in payload["text"]


@pytest.mark.asyncio
async def test_send_task_notification_truncates_long_task(monkeypatch):
    """Task description > 500 chars must be truncated with '...' suffix."""
    from app.models.notification import TaskNotificationRequest

    monkeypatch.setattr(
        tg_service, "api_url", "https://api.telegram.org/bot_test_token"
    )

    long_task = "A" * 600
    request = TaskNotificationRequest(
        project="Akasa",
        task=long_task,
        status="success",
    )

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        await tg_service.send_task_notification(chat_id=12345, request=request)

        payload = mock_post.call_args.kwargs["json"]
        text = payload["text"]
        # "..." gets escaped to "\.\.\." in MarkdownV2 — this is correct behavior
        assert "\\.\\.\\." in text
        assert long_task not in text  # full 600-char string must NOT appear


@pytest.mark.asyncio
async def test_send_task_notification_truncates_long_message(monkeypatch):
    """Optional message field > 300 chars must be truncated with '...' suffix."""
    from app.models.notification import TaskNotificationRequest

    monkeypatch.setattr(
        tg_service, "api_url", "https://api.telegram.org/bot_test_token"
    )

    long_message = "B" * 400
    request = TaskNotificationRequest(
        project="Akasa",
        task="Some task",
        status="success",
        message=long_message,
    )

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        await tg_service.send_task_notification(chat_id=12345, request=request)

        payload = mock_post.call_args.kwargs["json"]
        assert long_message not in payload["text"]
        # "..." gets escaped to "\.\.\." in MarkdownV2 — this is correct behavior
        assert "\\.\\.\\." in payload["text"]


@pytest.mark.asyncio
async def test_send_task_notification_escapes_special_chars(monkeypatch):
    """Dynamic content with MarkdownV2 special chars (. _ *) must be escaped."""
    from app.models.notification import TaskNotificationRequest

    monkeypatch.setattr(
        tg_service, "api_url", "https://api.telegram.org/bot_test_token"
    )

    request = TaskNotificationRequest(
        project="My.Project_v2",  # dot and underscore are MarkdownV2 special chars
        task="Fix bug in auth_service (critical!)",
        status="success",
    )

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        await tg_service.send_task_notification(chat_id=12345, request=request)

        payload = mock_post.call_args.kwargs["json"]
        text = payload["text"]
        assert "\\." in text  # dot in project name escaped
        assert "\\_" in text  # underscore in project/task escaped
        assert "\\!" in text  # exclamation mark in task escaped


@pytest.mark.asyncio
async def test_send_task_notification_optional_fields_omitted(monkeypatch):
    """Message with only required fields should not include optional field labels."""
    from app.models.notification import TaskNotificationRequest

    monkeypatch.setattr(
        tg_service, "api_url", "https://api.telegram.org/bot_test_token"
    )

    request = TaskNotificationRequest(
        project="Akasa",
        task="Minimal task",
        status="success",
        # No duration, source, message, link
    )

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        await tg_service.send_task_notification(chat_id=12345, request=request)

        text = mock_post.call_args.kwargs["json"]["text"]
        assert "*Duration:*" not in text
        assert "*Source:*" not in text
        assert "*Details:*" not in text
        assert "*Link:*" not in text


@pytest.mark.asyncio
async def test_send_task_notification_with_link(monkeypatch):
    """Link field appears as *Link:* line when provided."""
    from app.models.notification import TaskNotificationRequest

    monkeypatch.setattr(
        tg_service, "api_url", "https://api.telegram.org/bot_test_token"
    )

    request = TaskNotificationRequest(
        project="Akasa",
        task="Create PR for feature-auth",
        status="success",
        link="https://github.com/oatrice/Akasa/pull/42",
    )

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        await tg_service.send_task_notification(chat_id=12345, request=request)

        text = mock_post.call_args.kwargs["json"]["text"]
        assert "*Link:*" in text
        assert "github" in text


@pytest.mark.asyncio
async def test_send_task_notification_raises_on_telegram_error(monkeypatch):
    """Non-429 HTTPStatusError from Telegram API should propagate to the caller."""
    from app.models.notification import TaskNotificationRequest

    monkeypatch.setattr(
        tg_service, "api_url", "https://api.telegram.org/bot_test_token"
    )

    request = TaskNotificationRequest(
        project="Akasa",
        task="Some task",
        status="success",
    )

    error_response = httpx.Response(
        400, json={"description": "Bad Request: chat not found"}
    )
    side_effect = httpx.HTTPStatusError(
        "Bad Request", request=AsyncMock(), response=error_response
    )

    with patch.object(
        tg_service.client, "post", new_callable=AsyncMock, side_effect=side_effect
    ):
        with pytest.raises(httpx.HTTPStatusError):
            await tg_service.send_task_notification(chat_id=99999, request=request)


@pytest.mark.asyncio
async def test_send_task_notification_retrying_with_counts(monkeypatch):
    """retrying + retry_count/max_retries → 🔄 title แสดง attempt count"""
    from app.models.notification import TaskNotificationRequest

    monkeypatch.setattr(
        tg_service, "api_url", "https://api.telegram.org/bot_test_token"
    )

    request = TaskNotificationRequest(
        project="Akasa",
        task="Deploy to production",
        status="retrying",
        retry_count=2,
        max_retries=3,
        message="Docker daemon not responding",
    )

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        await tg_service.send_task_notification(chat_id=12345, request=request)

        text = mock_post.call_args.kwargs["json"]["text"]
        assert "🔄" in text
        assert "Retrying" in text
        assert "2/3" in text  # retry count in title
        assert "Attempt" in text
        assert "Docker daemon" in text  # message field


@pytest.mark.asyncio
async def test_send_task_notification_retrying_without_counts(monkeypatch):
    """retrying ไม่มี retry_count/max_retries → 🔄 title แบบ generic"""
    from app.models.notification import TaskNotificationRequest

    monkeypatch.setattr(
        tg_service, "api_url", "https://api.telegram.org/bot_test_token"
    )

    request = TaskNotificationRequest(
        project="Akasa",
        task="Run test suite",
        status="retrying",
    )

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        await tg_service.send_task_notification(chat_id=12345, request=request)

        text = mock_post.call_args.kwargs["json"]["text"]
        assert "🔄" in text
        assert "Retrying" in text
        assert "Attempt" not in text  # ไม่มี count → ไม่แสดง


@pytest.mark.asyncio
async def test_send_task_notification_limit_reached_with_max(monkeypatch):
    """limit_reached + max_retries → 🚫 title แสดง N/N"""
    from app.models.notification import TaskNotificationRequest

    monkeypatch.setattr(
        tg_service, "api_url", "https://api.telegram.org/bot_test_token"
    )

    request = TaskNotificationRequest(
        project="Akasa",
        task="Deploy to production",
        status="limit_reached",
        max_retries=3,
        message="Gave up after 3 attempts. Last error: timeout",
    )

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        await tg_service.send_task_notification(chat_id=12345, request=request)

        text = mock_post.call_args.kwargs["json"]["text"]
        assert "🚫" in text
        assert "Retry Limit Reached" in text
        assert "3/3" in text  # max/max format
        assert "Gave up" in text  # message field


@pytest.mark.asyncio
async def test_send_task_notification_limit_reached_without_max(monkeypatch):
    """limit_reached ไม่มี max_retries → 🚫 title แบบ generic"""
    from app.models.notification import TaskNotificationRequest

    monkeypatch.setattr(
        tg_service, "api_url", "https://api.telegram.org/bot_test_token"
    )

    request = TaskNotificationRequest(
        project="Akasa",
        task="Build APK",
        status="limit_reached",
    )

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        await tg_service.send_task_notification(chat_id=12345, request=request)

        text = mock_post.call_args.kwargs["json"]["text"]
        assert "🚫" in text
        assert "Retry Limit Reached" in text
        assert "/" not in text.split("*")[2]  # ไม่มี N/N ใน title


@pytest.mark.asyncio
async def test_send_task_notification_success_after_retries_shows_attempts(monkeypatch):
    """success พร้อม retry_count/max_retries → แสดง *Attempts: 2/3* เพิ่มเติม"""
    from app.models.notification import TaskNotificationRequest

    monkeypatch.setattr(
        tg_service, "api_url", "https://api.telegram.org/bot_test_token"
    )

    request = TaskNotificationRequest(
        project="Akasa",
        task="Deploy to production",
        status="success",
        retry_count=2,
        max_retries=3,
    )

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        await tg_service.send_task_notification(chat_id=12345, request=request)

        text = mock_post.call_args.kwargs["json"]["text"]
        assert "✅" in text
        assert "*Attempts:*" in text  # summary line สำหรับ non-retry statuses
        assert "2/3" in text


@pytest.mark.asyncio
async def test_send_task_notification_raises_on_429(monkeypatch):
    """Telegram 429 Too Many Requests propagates as HTTPStatusError (router handles it)."""
    from app.models.notification import TaskNotificationRequest

    monkeypatch.setattr(
        tg_service, "api_url", "https://api.telegram.org/bot_test_token"
    )

    request = TaskNotificationRequest(
        project="Akasa",
        task="Flood task",
        status="success",
    )

    error_response = httpx.Response(
        429, json={"description": "Too Many Requests: retry after 30"}
    )
    side_effect = httpx.HTTPStatusError(
        "Too Many Requests", request=AsyncMock(), response=error_response
    )

    with patch.object(
        tg_service.client, "post", new_callable=AsyncMock, side_effect=side_effect
    ):
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await tg_service.send_task_notification(chat_id=12345, request=request)

        assert exc_info.value.response.status_code == 429
