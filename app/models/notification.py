from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class NotificationPayload(BaseModel):
    user_id: Optional[str] = None
    chat_id: Optional[str] = None
    message: str
    priority: str = "medium"
    metadata: Optional[Dict[str, Any]] = None

    def get_formatted_message(self) -> str:
        if self.priority.lower() == "high":
            return f"🚨 *IMPORTANT NOTIFICATION* 🚨\n\n{self.message}"
        elif self.priority.lower() == "low":
            return f"ℹ️ {self.message}"
        return self.message


class NotificationResponse(BaseModel):
    status: str
    message: str


class TaskNotificationRequest(BaseModel):
    project: Optional[str] = "General"
    task: str
    status: Literal["success", "failure", "partial", "retrying", "limit_reached"]
    duration: Optional[str] = None  # e.g., "5m 20s"
    message: Optional[str] = None  # additional details / summary
    link: Optional[str] = None  # PR link, file, etc.
    source: Optional[str] = None  # "Gemini CLI", "Luma CLI", etc.
    chat_id: Optional[str] = None  # if not provided, backend uses AKASA_CHAT_ID
    retry_count: Optional[int] = None  # current attempt number, 1-based (e.g., 2)
    max_retries: Optional[int] = None  # maximum retry attempts allowed (e.g., 3)

    @field_validator("task")
    @classmethod
    def task_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("task must not be empty")
        return v

    @field_validator("status", mode="before")
    @classmethod
    def status_lowercase(cls, v: str) -> str:
        return v.lower() if isinstance(v, str) else v


class TaskNotificationResponse(BaseModel):
    delivered: bool
    timestamp: str  # ISO 8601 format


class ActionRequestMetadata(BaseModel):
    request_id: str
    command: str
    cwd: str
    session_id: Optional[str] = None
    type: str = "shell_command_confirmation"


class ActionRequestState(BaseModel):
    status: Literal["pending", "allowed", "denied"] = "pending"
    command: str
    cwd: str
    session_id: Optional[str] = None
    source: Optional[str] = None  # "antigravity" | "gemini_cli" | None
    description: Optional[str] = None
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    decided_by: Optional[str] = None
    decided_at: Optional[datetime] = None


class ActionRequestResponse(BaseModel):
    request_id: str
    status: str
    session_permission: bool = False
