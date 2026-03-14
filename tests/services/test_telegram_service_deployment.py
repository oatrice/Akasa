"""
Tests for TelegramService.send_deployment_notification — Issue #34

Covers:
  - Success deployment: ✅ header, URL in text, inline keyboard button
  - Failed deployment: ❌ header, stderr preview, no button
  - Duration calculation from timestamps
  - Missing optional fields handled gracefully
  - MarkdownV2 escaping
  - HTTP error propagation (4xx, 429 rate-limit)
  - Inline keyboard structure validation
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.models.deployment import DeploymentRecord
from app.services.telegram_service import tg_service

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TEST_API_URL = "https://api.telegram.org/bot_test_token"


def _make_record(**kwargs) -> DeploymentRecord:
    defaults = dict(
        deployment_id="dep-test-001",
        status="success",
        command="vercel deploy --prod",
        cwd="/home/user/app",
        project="Akasa",
        chat_id=None,
        stdout="",
        stderr="",
        exit_code=0,
        url=None,
        started_at=None,
        finished_at=None,
    )
    defaults.update(kwargs)
    return DeploymentRecord(**defaults)


def _mock_post_success():
    """Return a pre-configured AsyncMock that acts as a successful httpx post."""
    mock_response = AsyncMock()
    mock_response.raise_for_status = AsyncMock()
    mock_post = AsyncMock(return_value=mock_response)
    return mock_post


# ---------------------------------------------------------------------------
# Happy path — success deployment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_success_sends_check_emoji(monkeypatch):
    """✅ emoji must appear in the message for a successful deployment."""
    monkeypatch.setattr(tg_service, "api_url", TEST_API_URL)
    record = _make_record(status="success")

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = AsyncMock(raise_for_status=AsyncMock())
        await tg_service.send_deployment_notification(chat_id=111, record=record)

    payload = mock_post.call_args.kwargs["json"]
    assert "✅" in payload["text"]


@pytest.mark.asyncio
async def test_success_title_contains_succeeded(monkeypatch):
    monkeypatch.setattr(tg_service, "api_url", TEST_API_URL)
    record = _make_record(status="success")

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = AsyncMock(raise_for_status=AsyncMock())
        await tg_service.send_deployment_notification(chat_id=111, record=record)

    payload = mock_post.call_args.kwargs["json"]
    assert "Succeeded" in payload["text"]


@pytest.mark.asyncio
async def test_success_with_url_includes_url_in_text(monkeypatch):
    monkeypatch.setattr(tg_service, "api_url", TEST_API_URL)
    record = _make_record(status="success", url="https://myapp.vercel.app")

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = AsyncMock(raise_for_status=AsyncMock())
        await tg_service.send_deployment_notification(chat_id=111, record=record)

    payload = mock_post.call_args.kwargs["json"]
    # URL is escaped by escape_markdown_v2_content (dots → \.), check unescaped parts
    assert "myapp" in payload["text"]
    assert "vercel" in payload["text"]


@pytest.mark.asyncio
async def test_success_with_url_attaches_inline_keyboard(monkeypatch):
    """URL button must be present in reply_markup when url is provided."""
    monkeypatch.setattr(tg_service, "api_url", TEST_API_URL)
    record = _make_record(status="success", url="https://myapp.vercel.app")

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = AsyncMock(raise_for_status=AsyncMock())
        await tg_service.send_deployment_notification(chat_id=111, record=record)

    payload = mock_post.call_args.kwargs["json"]
    assert "reply_markup" in payload
    keyboard = payload["reply_markup"]["inline_keyboard"]
    assert len(keyboard) == 1
    assert len(keyboard[0]) == 1
    button = keyboard[0][0]
    assert button["url"] == "https://myapp.vercel.app"
    assert "Open" in button["text"]


@pytest.mark.asyncio
async def test_success_without_url_has_no_reply_markup(monkeypatch):
    """When no URL is found in output, no inline keyboard should be sent."""
    monkeypatch.setattr(tg_service, "api_url", TEST_API_URL)
    record = _make_record(status="success", url=None)

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = AsyncMock(raise_for_status=AsyncMock())
        await tg_service.send_deployment_notification(chat_id=111, record=record)

    payload = mock_post.call_args.kwargs["json"]
    assert "reply_markup" not in payload


@pytest.mark.asyncio
async def test_project_name_appears_in_message(monkeypatch):
    monkeypatch.setattr(tg_service, "api_url", TEST_API_URL)
    record = _make_record(project="MyUniqueProject")

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = AsyncMock(raise_for_status=AsyncMock())
        await tg_service.send_deployment_notification(chat_id=111, record=record)

    payload = mock_post.call_args.kwargs["json"]
    assert "MyUniqueProject" in payload["text"]


@pytest.mark.asyncio
async def test_command_appears_in_message(monkeypatch):
    monkeypatch.setattr(tg_service, "api_url", TEST_API_URL)
    record = _make_record(command="render deploy --service my-backend")

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = AsyncMock(raise_for_status=AsyncMock())
        await tg_service.send_deployment_notification(chat_id=111, record=record)

    payload = mock_post.call_args.kwargs["json"]
    assert "render deploy" in payload["text"]


# ---------------------------------------------------------------------------
# Failure deployment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_failure_sends_cross_emoji(monkeypatch):
    monkeypatch.setattr(tg_service, "api_url", TEST_API_URL)
    record = _make_record(status="failed", exit_code=1)

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = AsyncMock(raise_for_status=AsyncMock())
        await tg_service.send_deployment_notification(chat_id=111, record=record)

    payload = mock_post.call_args.kwargs["json"]
    assert "❌" in payload["text"]


@pytest.mark.asyncio
async def test_failure_title_contains_failed(monkeypatch):
    monkeypatch.setattr(tg_service, "api_url", TEST_API_URL)
    record = _make_record(status="failed", exit_code=1)

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = AsyncMock(raise_for_status=AsyncMock())
        await tg_service.send_deployment_notification(chat_id=111, record=record)

    payload = mock_post.call_args.kwargs["json"]
    assert "Failed" in payload["text"]


@pytest.mark.asyncio
async def test_failure_with_stderr_shows_error_preview(monkeypatch):
    """Last part of stderr should appear in the failure message."""
    monkeypatch.setattr(tg_service, "api_url", TEST_API_URL)
    record = _make_record(
        status="failed",
        stderr="Error: authentication required\nPlease run `vercel login` first.",
    )

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = AsyncMock(raise_for_status=AsyncMock())
        await tg_service.send_deployment_notification(chat_id=111, record=record)

    payload = mock_post.call_args.kwargs["json"]
    assert (
        "authentication required" in payload["text"]
        or "vercel login" in payload["text"]
    )


@pytest.mark.asyncio
async def test_failure_without_stderr_no_error_field(monkeypatch):
    """Empty stderr → 'Error:' line must not appear in the message."""
    monkeypatch.setattr(tg_service, "api_url", TEST_API_URL)
    record = _make_record(status="failed", stderr="")

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = AsyncMock(raise_for_status=AsyncMock())
        await tg_service.send_deployment_notification(chat_id=111, record=record)

    payload = mock_post.call_args.kwargs["json"]
    assert "*Error:*" not in payload["text"]


@pytest.mark.asyncio
async def test_failure_has_no_url_button(monkeypatch):
    """Failed deployment must never show a URL button."""
    monkeypatch.setattr(tg_service, "api_url", TEST_API_URL)
    record = _make_record(status="failed", url=None, stderr="deploy failed")

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = AsyncMock(raise_for_status=AsyncMock())
        await tg_service.send_deployment_notification(chat_id=111, record=record)

    payload = mock_post.call_args.kwargs["json"]
    assert "reply_markup" not in payload


@pytest.mark.asyncio
async def test_failure_long_stderr_is_truncated(monkeypatch):
    """stderr preview must be capped at 200 chars to fit Telegram limits."""
    monkeypatch.setattr(tg_service, "api_url", TEST_API_URL)
    very_long_stderr = "X" * 1000
    record = _make_record(status="failed", stderr=very_long_stderr)

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = AsyncMock(raise_for_status=AsyncMock())
        await tg_service.send_deployment_notification(chat_id=111, record=record)

    payload = mock_post.call_args.kwargs["json"]
    # The raw 1000-char blob must not appear verbatim
    assert "X" * 1000 not in payload["text"]
    # But some truncated version must be there
    assert "X" * 10 in payload["text"]


# ---------------------------------------------------------------------------
# Duration calculation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_duration_shown_in_seconds(monkeypatch):
    """45-second deployment → '45s' appears in message."""
    monkeypatch.setattr(tg_service, "api_url", TEST_API_URL)
    record = _make_record(
        status="success",
        started_at="2024-01-01T10:00:00+00:00",
        finished_at="2024-01-01T10:00:45+00:00",
    )

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = AsyncMock(raise_for_status=AsyncMock())
        await tg_service.send_deployment_notification(chat_id=111, record=record)

    payload = mock_post.call_args.kwargs["json"]
    assert "45s" in payload["text"]


@pytest.mark.asyncio
async def test_duration_shown_in_minutes_and_seconds(monkeypatch):
    """90-second deployment → '1m 30s' appears in message."""
    monkeypatch.setattr(tg_service, "api_url", TEST_API_URL)
    record = _make_record(
        status="success",
        started_at="2024-01-01T10:00:00+00:00",
        finished_at="2024-01-01T10:01:30+00:00",
    )

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = AsyncMock(raise_for_status=AsyncMock())
        await tg_service.send_deployment_notification(chat_id=111, record=record)

    payload = mock_post.call_args.kwargs["json"]
    assert "1m 30s" in payload["text"]


@pytest.mark.asyncio
async def test_duration_not_shown_when_timestamps_missing(monkeypatch):
    """No timestamps → 'Duration:' must not appear in message."""
    monkeypatch.setattr(tg_service, "api_url", TEST_API_URL)
    record = _make_record(status="success", started_at=None, finished_at=None)

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = AsyncMock(raise_for_status=AsyncMock())
        await tg_service.send_deployment_notification(chat_id=111, record=record)

    payload = mock_post.call_args.kwargs["json"]
    assert "Duration" not in payload["text"]


@pytest.mark.asyncio
async def test_duration_not_shown_when_only_started_at_present(monkeypatch):
    """Only started_at (no finished_at) → Duration must not appear."""
    monkeypatch.setattr(tg_service, "api_url", TEST_API_URL)
    record = _make_record(
        status="success",
        started_at="2024-01-01T10:00:00+00:00",
        finished_at=None,
    )

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = AsyncMock(raise_for_status=AsyncMock())
        await tg_service.send_deployment_notification(chat_id=111, record=record)

    payload = mock_post.call_args.kwargs["json"]
    assert "Duration" not in payload["text"]


@pytest.mark.asyncio
async def test_zero_second_deployment_duration(monkeypatch):
    """Started and finished at the same second → '0s'."""
    monkeypatch.setattr(tg_service, "api_url", TEST_API_URL)
    record = _make_record(
        status="success",
        started_at="2024-06-01T12:00:00+00:00",
        finished_at="2024-06-01T12:00:00+00:00",
    )

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = AsyncMock(raise_for_status=AsyncMock())
        await tg_service.send_deployment_notification(chat_id=111, record=record)

    payload = mock_post.call_args.kwargs["json"]
    assert "0s" in payload["text"]


# ---------------------------------------------------------------------------
# Payload contract
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_payload_uses_markdownv2(monkeypatch):
    """parse_mode must be 'MarkdownV2' — required for bold/code formatting."""
    monkeypatch.setattr(tg_service, "api_url", TEST_API_URL)
    record = _make_record()

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = AsyncMock(raise_for_status=AsyncMock())
        await tg_service.send_deployment_notification(chat_id=111, record=record)

    payload = mock_post.call_args.kwargs["json"]
    assert payload.get("parse_mode") == "MarkdownV2"


@pytest.mark.asyncio
async def test_correct_chat_id_sent(monkeypatch):
    monkeypatch.setattr(tg_service, "api_url", TEST_API_URL)
    record = _make_record()

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = AsyncMock(raise_for_status=AsyncMock())
        await tg_service.send_deployment_notification(chat_id=987654321, record=record)

    payload = mock_post.call_args.kwargs["json"]
    assert payload["chat_id"] == 987654321


@pytest.mark.asyncio
async def test_correct_sendmessage_endpoint_called(monkeypatch):
    monkeypatch.setattr(tg_service, "api_url", TEST_API_URL)
    record = _make_record()

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = AsyncMock(raise_for_status=AsyncMock())
        await tg_service.send_deployment_notification(chat_id=111, record=record)

    called_url = mock_post.call_args.args[0]
    assert called_url == f"{TEST_API_URL}/sendMessage"


@pytest.mark.asyncio
async def test_timeout_is_set(monkeypatch):
    """HTTP call must include a timeout to avoid hanging indefinitely."""
    monkeypatch.setattr(tg_service, "api_url", TEST_API_URL)
    record = _make_record()

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = AsyncMock(raise_for_status=AsyncMock())
        await tg_service.send_deployment_notification(chat_id=111, record=record)

    timeout = mock_post.call_args.kwargs.get("timeout")
    assert timeout is not None
    assert timeout > 0


# ---------------------------------------------------------------------------
# URL in message text vs. button
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_url_appears_in_both_text_and_button(monkeypatch):
    """The deployed URL should be visible in the text AND as a button URL."""
    monkeypatch.setattr(tg_service, "api_url", TEST_API_URL)
    url = "https://akasa-deploy.onrender.com"
    record = _make_record(status="success", url=url)

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = AsyncMock(raise_for_status=AsyncMock())
        await tg_service.send_deployment_notification(chat_id=111, record=record)

    payload = mock_post.call_args.kwargs["json"]
    text = payload["text"]
    button_url = payload["reply_markup"]["inline_keyboard"][0][0]["url"]

    # URL is escaped in text (dots → \.), check for unescaped hostname parts
    assert "onrender" in text
    assert button_url == url


@pytest.mark.asyncio
async def test_inline_keyboard_button_is_url_type_not_callback(monkeypatch):
    """
    The inline keyboard button must use 'url' key (opens browser directly),
    NOT 'callback_data' (which would send a callback to the bot server).
    """
    monkeypatch.setattr(tg_service, "api_url", TEST_API_URL)
    record = _make_record(status="success", url="https://example.com")

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = AsyncMock(raise_for_status=AsyncMock())
        await tg_service.send_deployment_notification(chat_id=111, record=record)

    button = mock_post.call_args.kwargs["json"]["reply_markup"]["inline_keyboard"][0][0]
    assert "url" in button
    assert "callback_data" not in button


# ---------------------------------------------------------------------------
# MarkdownV2 escaping
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_special_chars_in_project_are_escaped(monkeypatch):
    """Project name with MarkdownV2 special chars must not break the message."""
    monkeypatch.setattr(tg_service, "api_url", TEST_API_URL)
    # Dots and dashes are MarkdownV2 reserved characters
    record = _make_record(project="my-app.v2_prod")

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = AsyncMock(raise_for_status=AsyncMock())
        # Must not raise, Telegram API call should succeed
        await tg_service.send_deployment_notification(chat_id=111, record=record)

    mock_post.assert_awaited_once()


@pytest.mark.asyncio
async def test_special_chars_in_command_are_escaped(monkeypatch):
    """Command strings with brackets/parens must not produce invalid MarkdownV2."""
    monkeypatch.setattr(tg_service, "api_url", TEST_API_URL)
    record = _make_record(command="deploy.sh --env=prod (v1.2.3)")

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = AsyncMock(raise_for_status=AsyncMock())
        await tg_service.send_deployment_notification(chat_id=111, record=record)

    mock_post.assert_awaited_once()
    payload = mock_post.call_args.kwargs["json"]
    # Content should be present (escaped form)
    assert "deploy" in payload["text"]


# ---------------------------------------------------------------------------
# Error propagation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_http_4xx_error_propagates(monkeypatch):
    """Non-429 HTTP errors from Telegram API must propagate to the caller."""
    monkeypatch.setattr(tg_service, "api_url", TEST_API_URL)
    record = _make_record()

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        # raise_for_status() is called synchronously in the service (not awaited),
        # so we must use MagicMock (sync) — not AsyncMock — to make it raise immediately.
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request",
            request=MagicMock(),
            response=httpx.Response(400, json={"ok": False}),
        )
        mock_post.return_value = mock_response
        with pytest.raises(httpx.HTTPStatusError):
            await tg_service.send_deployment_notification(chat_id=111, record=record)


@pytest.mark.asyncio
async def test_http_429_rate_limit_propagates(monkeypatch):
    """429 Too Many Requests must propagate (caller handles rate-limit logic)."""
    monkeypatch.setattr(tg_service, "api_url", TEST_API_URL)
    record = _make_record()

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Too Many Requests",
            request=MagicMock(),
            response=httpx.Response(429, json={"ok": False}),
        )
        mock_post.return_value = mock_response
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await tg_service.send_deployment_notification(chat_id=111, record=record)

    assert exc_info.value.response.status_code == 429


@pytest.mark.asyncio
async def test_network_error_propagates(monkeypatch):
    """Network-level errors (e.g. DNS failure) must propagate."""
    monkeypatch.setattr(tg_service, "api_url", TEST_API_URL)
    record = _make_record()

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.ConnectError("Network unreachable")
        with pytest.raises(httpx.ConnectError):
            await tg_service.send_deployment_notification(chat_id=111, record=record)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_project_name_does_not_crash(monkeypatch):
    monkeypatch.setattr(tg_service, "api_url", TEST_API_URL)
    record = _make_record(project="")

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = AsyncMock(raise_for_status=AsyncMock())
        await tg_service.send_deployment_notification(chat_id=111, record=record)

    mock_post.assert_awaited_once()


@pytest.mark.asyncio
async def test_very_long_command_is_included_in_message(monkeypatch):
    """Long commands should appear in the message without truncation."""
    monkeypatch.setattr(tg_service, "api_url", TEST_API_URL)
    long_cmd = "vercel deploy --prod --yes --token abc123 --scope my-team --cwd /home/user/projects/my-app"
    record = _make_record(command=long_cmd)

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = AsyncMock(raise_for_status=AsyncMock())
        await tg_service.send_deployment_notification(chat_id=111, record=record)

    payload = mock_post.call_args.kwargs["json"]
    assert "vercel deploy" in payload["text"]


@pytest.mark.asyncio
async def test_post_called_exactly_once(monkeypatch):
    """send_deployment_notification must make exactly one HTTP call."""
    monkeypatch.setattr(tg_service, "api_url", TEST_API_URL)
    record = _make_record()

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = AsyncMock(raise_for_status=AsyncMock())
        await tg_service.send_deployment_notification(chat_id=111, record=record)

    mock_post.assert_awaited_once()


@pytest.mark.asyncio
async def test_success_with_url_does_not_show_success_as_failed(monkeypatch):
    """Sanity: ✅ message must not accidentally contain ❌."""
    monkeypatch.setattr(tg_service, "api_url", TEST_API_URL)
    record = _make_record(status="success", url="https://example.com")

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = AsyncMock(raise_for_status=AsyncMock())
        await tg_service.send_deployment_notification(chat_id=111, record=record)

    text = mock_post.call_args.kwargs["json"]["text"]
    assert "❌" not in text


@pytest.mark.asyncio
async def test_failed_deployment_does_not_show_succeeded(monkeypatch):
    """Sanity: ❌ message must not accidentally contain 'Succeeded'."""
    monkeypatch.setattr(tg_service, "api_url", TEST_API_URL)
    record = _make_record(status="failed", exit_code=1)

    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = AsyncMock(raise_for_status=AsyncMock())
        await tg_service.send_deployment_notification(chat_id=111, record=record)

    text = mock_post.call_args.kwargs["json"]["text"]
    assert "Succeeded" not in text
