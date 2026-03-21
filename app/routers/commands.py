"""
Commands Router — Feature #66
Telegram → Local Tools Command Queue (Bidirectional Control)

Endpoints:
  POST /api/v1/commands              — Enqueue a new command
  GET  /api/v1/commands/{command_id} — Get command status
  POST /api/v1/commands/{command_id}/result — Daemon reports result
"""

import logging
import re
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException

from app.config import settings
from app.models.command import (
    CommandQueueRequest,
    CommandQueueResponse,
    CommandResultRequest,
    CommandResultResponse,
    CommandStatusResponse,
)
from app.routers.notifications import verify_api_key
from app.services import command_queue_service
from app.services.telegram_service import tg_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/commands", tags=["commands"])

_QUOTA_RESET_RE = re.compile(r"quota will reset after ([^\n.]+)", re.IGNORECASE)
_DURATION_FRAGMENT_RE = re.compile(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", re.IGNORECASE)
_FALLBACK_MODEL_RE = re.compile(r"Retried with fallback model:\s*([^\n]+)", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Daemon secret validation
# ---------------------------------------------------------------------------


def _verify_daemon_secret(x_daemon_secret: Optional[str] = Header(None)) -> None:
    """Validate the X-Daemon-Secret header for daemon-only endpoints."""
    if not x_daemon_secret or x_daemon_secret != settings.AKASA_DAEMON_SECRET:
        raise HTTPException(status_code=401, detail="Invalid or missing daemon secret")


def _format_wait_fragment(fragment: str) -> str:
    cleaned = fragment.strip()
    match = _DURATION_FRAGMENT_RE.fullmatch(cleaned)
    if not match:
        return cleaned

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)

    parts: list[str] = []
    if hours:
        parts.append(f"{hours} ชั่วโมง")
    if minutes:
        parts.append(f"{minutes} นาที")
    if seconds:
        parts.append(f"{seconds} วินาที")

    return " ".join(parts) if parts else cleaned


def _summarize_command_output(
    tool: str,
    status: str,
    output: Optional[str],
) -> Optional[str]:
    if not output:
        return None

    if tool.lower() != "gemini":
        return None

    fallback_match = _FALLBACK_MODEL_RE.search(output)
    if fallback_match:
        fallback_model = fallback_match.group(1).strip()
        if status == "success":
            return (
                f"Gemini quota บนโมเดลหลัก จึงสลับไปใช้ {fallback_model} "
                "และรันต่อสำเร็จ"
            )
        return (
            f"Gemini quota บนโมเดลหลัก จึงลองสลับไปใช้ {fallback_model} "
            "แล้ว แต่คำสั่งยังไม่สำเร็จ"
        )

    normalized = output.lower()
    if (
        "terminalquotaerror" not in normalized
        and "exhausted your capacity on this model" not in normalized
        and "quota will reset after" not in normalized
    ):
        return None

    reset_match = _QUOTA_RESET_RE.search(output)
    if reset_match:
        wait_text = _format_wait_fragment(reset_match.group(1))
        return f"Gemini quota หมดชั่วคราว รีเซ็ตอีกประมาณ {wait_text}"

    return "Gemini quota หมดชั่วคราว ลองใหม่อีกครั้งภายหลัง"


# ---------------------------------------------------------------------------
# POST /api/v1/commands — Enqueue
# ---------------------------------------------------------------------------


@router.post("", response_model=CommandQueueResponse)
async def enqueue_command(
    request: CommandQueueRequest,
    user_id: Optional[int] = None,
    chat_id: Optional[int] = None,
    _auth: None = Depends(verify_api_key),
):
    """
    Enqueue a command for a local tool daemon to execute.

    - Validates the command against the whitelist.
    - Checks per-user rate limits.
    - Pushes the command to the Redis queue.
    """
    # Resolve defaults for user_id and chat_id
    resolved_user_id = user_id or _get_default_user_id()
    resolved_chat_id = chat_id or _get_default_chat_id()

    # Rate limit check
    allowed, retry_after = await command_queue_service.check_rate_limit(resolved_user_id)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Retry after {retry_after} seconds.",
        )

    try:
        result = await command_queue_service.enqueue_command(
            request, user_id=resolved_user_id, chat_id=resolved_chat_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ConnectionError:
        raise HTTPException(
            status_code=503, detail="Queue service unavailable. Please try again later."
        )

    return result


# ---------------------------------------------------------------------------
# GET /api/v1/commands/{command_id} — Status
# ---------------------------------------------------------------------------


@router.get("/{command_id}", response_model=CommandStatusResponse)
async def get_command_status(
    command_id: str,
    _auth: None = Depends(verify_api_key),
):
    """Retrieve the current status of a queued command."""
    status = await command_queue_service.get_command_status(command_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"Command '{command_id}' not found")
    return status


# ---------------------------------------------------------------------------
# POST /api/v1/commands/{command_id}/result — Daemon Reports Result
# ---------------------------------------------------------------------------


@router.post("/{command_id}/result", response_model=CommandResultResponse)
async def report_command_result(
    command_id: str,
    result: CommandResultRequest,
    x_daemon_secret: Optional[str] = Header(None),
):
    """
    Receive a result from the local tool daemon.

    - Validates daemon secret.
    - Updates command status in Redis.
    - Sends Telegram notification with the result.
    """
    # Validate daemon secret
    _verify_daemon_secret(x_daemon_secret)

    # Check command exists
    status = await command_queue_service.get_command_status(command_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"Command '{command_id}' not found")

    # Update status
    await command_queue_service.update_command_status(
        command_id,
        status=result.status,
        result=result.output,
        error=result.output if result.status == "failed" else None,
        cwd=result.cwd,
    )

    # Send Telegram notification
    notification_sent = False
    try:
        from app.utils.markdown_utils import escape_markdown_v2, escape_markdown_v2_content
        emoji = "✅" if result.status == "success" else "❌"
        
        safe_tool = escape_markdown_v2_content(status.tool)
        safe_command = escape_markdown_v2_content(status.command)
        safe_status = escape_markdown_v2_content(result.status)
        
        msg = (
            f"{emoji} *Command Result*\n\n"
            f"*Command ID:* `{command_id}`\n"
            f"*Tool:* {safe_tool}\n"
            f"*Command:* {safe_command}\n"
            f"*Status:* {safe_status}\n"
        )
        if result.exit_code is not None:
            safe_exit = escape_markdown_v2_content(str(result.exit_code))
            msg += f"*Exit Code:* {safe_exit}\n"
        if result.duration_seconds is not None:
            safe_duration = escape_markdown_v2_content(f"{result.duration_seconds:.1f}s")
            msg += f"*Duration:* {safe_duration}\n"
        effective_cwd = result.cwd or status.cwd
        if effective_cwd:
            safe_cwd = escape_markdown_v2_content(effective_cwd)
            msg += f"*CWD:* `{safe_cwd}`\n"
        summary = _summarize_command_output(
            status.tool,
            result.status,
            result.output,
        )
        if summary:
            safe_summary = escape_markdown_v2_content(summary)
            msg += f"*Summary:* {safe_summary}\n"
        if result.output:
            # We don't escape output with _content because it goes in a code block
            # where escape_markdown_v2 will preserve it, though if it contains ``` 
            # we should replace it to avoid breaking the block.
            output_preview = result.output[:500].replace("```", "'''")
            msg += f"\n*Output:*\n```\n{output_preview}\n```"

        escaped_msg = escape_markdown_v2(msg)

        # Use the chat_id from the original command payload for notification
        # Fallback to AKASA_CHAT_ID if original chat_id is somehow missing
        if status.chat_id:
            target_chat_id = status.chat_id
        elif settings.AKASA_CHAT_ID:
            target_chat_id = int(settings.AKASA_CHAT_ID)
        else:
            raise ValueError("No chat_id available for notification (both status.chat_id and AKASA_CHAT_ID are empty)")

        await tg_service.send_message(
            chat_id=target_chat_id,
            text=escaped_msg,
        )
        notification_sent = True
    except Exception as exc:
        logger.error(f"Failed to send result notification: {exc}")

    return CommandResultResponse(
        command_id=command_id,
        status=result.status,
        notification_sent=notification_sent,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_default_user_id() -> int:
    """Resolve default user_id from settings."""
    allowed = settings.ALLOWED_TELEGRAM_USER_IDS
    if allowed:
        first_id = allowed.split(",")[0].strip()
        if first_id.isdigit():
            return int(first_id)
    return 0


def _get_default_chat_id() -> int:
    """Resolve default chat_id from settings."""
    chat_id = settings.AKASA_CHAT_ID
    if chat_id and chat_id.strip().isdigit():
        return int(chat_id.strip())
    return 0
