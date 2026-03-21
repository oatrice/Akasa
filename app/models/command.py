"""
Command Queue Models — Feature #66

Pydantic models สำหรับ Telegram → Local Tools Command Queue system
"""

import os
from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Request / Response — POST /api/v1/commands (Enqueue)
# ---------------------------------------------------------------------------


class CommandQueueRequest(BaseModel):
    """Request body for enqueueing a new command."""

    tool: str = Field(
        ..., description="Target tool name (e.g., 'gemini', 'luma', 'zed')"
    )
    command: str = Field(..., description="Whitelisted command to execute")
    args: Dict[str, Any] = Field(
        default_factory=dict, description="Structured arguments for the command"
    )
    cwd: Optional[str] = Field(
        default=None,
        description="Optional absolute working directory for command execution",
    )
    ttl_seconds: int = Field(
        default=300, ge=30, le=3600, description="Command TTL in seconds (30–3600)"
    )

    @field_validator("tool")
    @classmethod
    def tool_must_not_be_empty(cls, v: str) -> str:
        v = v.strip().lower()
        if not v:
            raise ValueError("tool must not be empty")
        return v

    @field_validator("command")
    @classmethod
    def command_must_not_be_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("command must not be empty")
        return v

    @field_validator("cwd")
    @classmethod
    def normalize_cwd(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        normalized = value.strip()
        if not normalized:
            raise ValueError("cwd must not be empty")

        expanded = os.path.expanduser(normalized)
        if not os.path.isabs(expanded):
            raise ValueError("cwd must be an absolute path")
        expanded = os.path.abspath(expanded)
        if not os.path.isdir(expanded):
            raise ValueError("cwd must point to an existing directory")
        return expanded


class CommandQueueResponse(BaseModel):
    """Response returned after successfully enqueueing a command."""

    command_id: str
    status: str = "queued"
    tool: str
    command: str
    cwd: Optional[str] = None
    queued_at: str  # ISO 8601
    expires_at: str  # ISO 8601


# ---------------------------------------------------------------------------
# Command Status — GET /api/v1/commands/{command_id}
# ---------------------------------------------------------------------------

CommandStatusLiteral = Literal[
    "queued",
    "picked_up",
    "running",
    "success",
    "failed",
    "expired",
]


class CommandStatusResponse(BaseModel):
    """Current status of a queued command."""

    command_id: str
    status: CommandStatusLiteral
    tool: str
    command: str
    cwd: Optional[str] = None
    queued_at: str  # ISO 8601
    picked_up_at: Optional[str] = None  # ISO 8601
    completed_at: Optional[str] = None  # ISO 8601
    result: Optional[str] = None
    error: Optional[str] = None
    chat_id: Optional[int] = None  # For routing notifications to correct user


# ---------------------------------------------------------------------------
# Internal Redis Payload — stored in the queue list
# ---------------------------------------------------------------------------


class CommandPayload(BaseModel):
    """
    Payload stored as a JSON string in Redis List (akasa:commands:{tool}).
    Created at enqueue time; consumed by the local daemon.
    """

    command_id: str
    tool: str
    command: str
    args: Dict[str, Any] = Field(default_factory=dict)
    cwd: Optional[str] = None
    user_id: int
    chat_id: int
    queued_at: str  # ISO 8601
    ttl_seconds: int = 300

    def is_expired(self) -> bool:
        """Check if this command has exceeded its TTL."""
        try:
            queued = datetime.fromisoformat(self.queued_at)
            age_seconds = (datetime.now(timezone.utc) - queued).total_seconds()
            return age_seconds > self.ttl_seconds
        except Exception:
            return True


# ---------------------------------------------------------------------------
# Command Result — POST /api/v1/commands/{command_id}/result (Daemon → Backend)
# ---------------------------------------------------------------------------


class CommandResultRequest(BaseModel):
    """Payload sent by the daemon when a command finishes."""

    status: Literal["success", "failed"]
    output: Optional[str] = Field(default=None, description="stdout / combined output")
    cwd: Optional[str] = Field(
        default=None,
        description="Working directory actually used during execution",
    )
    exit_code: Optional[int] = None
    duration_seconds: Optional[float] = Field(default=None, ge=0)

    @field_validator("output")
    @classmethod
    def truncate_output(cls, v: Optional[str]) -> Optional[str]:
        """Prevent oversized payloads — cap at 20,000 characters."""
        if v and len(v) > 20000:
            return v[:19997] + "..."
        return v

    @field_validator("cwd")
    @classmethod
    def normalize_result_cwd(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        normalized = value.strip()
        if not normalized:
            raise ValueError("cwd must not be empty")

        expanded = os.path.expanduser(normalized)
        if not os.path.isabs(expanded):
            raise ValueError("cwd must be an absolute path")
        expanded = os.path.abspath(expanded)
        return expanded


class CommandResultResponse(BaseModel):
    """Response returned to the daemon after it reports a result."""

    command_id: str
    status: str
    notification_sent: bool
