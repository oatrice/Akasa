"""
Deployment Models — สำหรับ Async Deployment Service (Issue #33 & #34)
"""

from typing import Optional

from pydantic import BaseModel


class DeploymentRequest(BaseModel):
    """Payload สำหรับเริ่ม deployment ใหม่"""

    command: str  # คำสั่งที่ต้องการรัน เช่น "vercel deploy", "render-cli deploy"
    cwd: str  # Working directory ที่จะรันคำสั่ง
    project: str = "General"  # ชื่อโปรเจกต์ (ใช้ใน notification)
    chat_id: Optional[str] = None  # Override AKASA_CHAT_ID สำหรับ notification


class DeploymentResponse(BaseModel):
    """Response หลังจาก POST /deployments (202 Accepted)"""

    deployment_id: str
    status: str  # "pending"


class DeploymentRecord(BaseModel):
    """สถานะของ deployment ที่เก็บใน Redis"""

    deployment_id: str
    status: str  # "pending" | "running" | "success" | "failed"
    command: str
    cwd: str
    project: str = "General"
    chat_id: Optional[str] = None

    # Output จากการรันคำสั่ง
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None

    # URL ที่ extracted จาก stdout/stderr (Issue #34)
    url: Optional[str] = None

    # Timestamps (ISO 8601)
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


class DeploymentStatusResponse(BaseModel):
    """Response สำหรับ GET /deployments/{deployment_id}"""

    deployment_id: str
    status: str  # "pending" | "running" | "success" | "failed"
    url: Optional[str] = None
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
