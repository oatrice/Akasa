"""
Health Check Router

Router สำหรับ endpoint ดูสถานะระบบ
"""

from fastapi import APIRouter

router = APIRouter(tags=["Monitoring"])


@router.get("/health")
def health_check() -> dict:
    """
    Endpoint สำหรับตรวจสอบสถานะของระบบ (Health Check)
    """
    return {"status": "ok"}
