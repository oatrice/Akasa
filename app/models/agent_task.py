"""
Agent Task Log Model — AI Agent Timeout Observer Feature

Pydantic model สำหรับเก็บสถานะการทำงานของ AI Agent ใน Redis
เพื่อตรวจจับ timeout เมื่อ agent หยุดทำงานโดยไม่ได้ส่ง notification กลับ
"""

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field


AgentTaskStatus = Literal[
    "starting",  # Agent เริ่มทำงาน
    "success",  # Agent ทำงานเสร็จสำเร็จ
    "failure",  # Agent ทำงานพัง
    "partial",  # Agent ทำงานเสร็จแต่มี warning
    "timeout",  # Agent หายไปนานเกิน threshold
]


class AgentTaskLog(BaseModel):
    """
    บันทึกสถานะการทำงานของ AI Agent

    เก็บใน Redis key: akasa:agent_task:{task_id}
    """

    task_id: str = Field(..., description="Unique task identifier")
    project: str = Field(default="General", description="Project name")
    task: str = Field(..., description="Task description")
    status: AgentTaskStatus = Field(default="starting", description="Current task status")
    source: Optional[str] = Field(default=None, description="Source agent (e.g., 'Antigravity IDE')")
    chat_id: Optional[str] = Field(default=None, description="Telegram chat ID for notifications")

    # Timestamps (ISO 8601)
    started_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        description="When the task started",
    )
    completed_at: Optional[str] = Field(default=None, description="When the task completed/failed/timed out")

    # Optional fields from notify_task_complete
    duration: Optional[str] = Field(default=None, description="Task duration (e.g., '5m 20s')")
    message: Optional[str] = Field(default=None, description="Additional details")
    link: Optional[str] = Field(default=None, description="Related link (PR, file, etc.)")

    def is_timed_out(self, threshold_minutes: int) -> bool:
        """
        Check if this task has exceeded the timeout threshold.

        Args:
            threshold_minutes: Maximum allowed duration in minutes

        Returns:
            True if the task has been running longer than threshold
        """
        if self.status != "starting":
            return False

        try:
            started = datetime.fromisoformat(self.started_at.replace("Z", "+00:00"))
            elapsed = (datetime.now(timezone.utc) - started).total_seconds() / 60
            return elapsed > threshold_minutes
        except Exception:
            return False

    def mark_timeout(self) -> "AgentTaskLog":
        """
        Mark this task as timed out.

        Returns:
            Updated AgentTaskLog with timeout status
        """
        self.status = "timeout"
        self.completed_at = (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
        return self

    def mark_completed(self, status: AgentTaskStatus) -> "AgentTaskLog":
        """
        Mark this task as completed with the given status.

        Args:
            status: Final status (success, failure, partial)

        Returns:
            Updated AgentTaskLog
        """
        self.status = status
        self.completed_at = (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
        return self
