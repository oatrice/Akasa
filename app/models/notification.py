from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, Any
from datetime import datetime, timezone

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
