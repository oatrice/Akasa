from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, Any
from datetime import datetime

class NotificationPayload(BaseModel):
    user_id: Optional[str] = None
    chat_id: Optional[str] = None
    message: str
    priority: str = "medium"
    metadata: Optional[Dict[str, Any]] = None

    def get_formatted_message(self) -> str:
        prefix = ""
        if self.priority.lower() == "high":
            prefix = "🚨 "
        elif self.priority.lower() == "low":
            prefix = "ℹ️ "
        return f"{prefix}{self.message}"

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
    requested_at: datetime = Field(default_factory=datetime.utcnow)
    decided_by: Optional[str] = None
    decided_at: Optional[datetime] = None

class ActionRequestResponse(BaseModel):
    request_id: str
    status: str
    session_permission: bool = False
