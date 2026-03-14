"""
Deployments Router — Async Deployment Service (Issue #33 & #34)

Endpoints:
  POST /api/v1/deployments        — เริ่ม deployment ใหม่ใน background (202 Accepted)
  GET  /api/v1/deployments/{id}   — poll สถานะและผลลัพธ์ของ deployment
"""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException

from app.config import settings
from app.models.deployment import (
    DeploymentRecord,
    DeploymentRequest,
    DeploymentResponse,
    DeploymentStatusResponse,
)
from app.services.deploy_service import (
    create_deployment,
    get_deployment,
    run_deployment,
)
from app.services.telegram_service import tg_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/deployments", tags=["deployments"])


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


async def verify_api_key(x_akasa_api_key: str = Header(None)) -> bool:
    """ตรวจสอบ API Key จาก X-Akasa-API-Key header"""
    if not x_akasa_api_key or x_akasa_api_key != settings.AKASA_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return True


# ---------------------------------------------------------------------------
# Issue #34 — Notification callback
# ---------------------------------------------------------------------------


async def _notify_deployment(record: DeploymentRecord) -> None:
    """
    Callback ที่ถูกเรียกโดย run_deployment() หลังจาก deployment เสร็จสิ้น
    ส่ง Telegram notification พร้อม URL button (Issue #34)
    """
    try:
        chat_id_str = record.chat_id or settings.AKASA_CHAT_ID
        if not chat_id_str:
            logger.warning(
                f"Deployment {record.deployment_id}: no chat_id configured, "
                "skipping Telegram notification"
            )
            return

        await tg_service.send_deployment_notification(
            chat_id=int(chat_id_str),
            record=record,
        )
        logger.info(
            f"Deployment notification sent for {record.deployment_id} → chat_id={chat_id_str}"
        )
    except Exception as e:
        logger.error(
            f"Failed to send deployment notification for {record.deployment_id}: {e}",
            exc_info=True,
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", response_model=DeploymentResponse, status_code=202)
async def start_deployment(
    payload: DeploymentRequest,
    background_tasks: BackgroundTasks,
    authenticated: bool = Depends(verify_api_key),
):
    """
    Issue #33 — เริ่ม deployment ใหม่แบบ async

    รับ command, cwd, และชื่อโปรเจกต์ แล้วรันใน BackgroundTask
    คืนค่า deployment_id เพื่อให้ client poll สถานะได้

    Returns:
        202 Accepted + {"deployment_id": "...", "status": "pending"}
    """
    record = await create_deployment(
        command=payload.command,
        cwd=payload.cwd,
        project=payload.project,
        chat_id=payload.chat_id,
    )

    background_tasks.add_task(run_deployment, record.deployment_id, _notify_deployment)

    logger.info(
        f"Deployment queued: id={record.deployment_id}, "
        f"project={record.project!r}, command={record.command!r}"
    )

    return DeploymentResponse(
        deployment_id=record.deployment_id,
        status=record.status,
    )


@router.get("/{deployment_id}", response_model=DeploymentStatusResponse)
async def get_deployment_status(
    deployment_id: str,
    authenticated: bool = Depends(verify_api_key),
):
    """
    Issue #33 — Poll สถานะของ deployment

    ใช้ polling จาก client เพื่อตรวจสอบว่า deployment เสร็จสิ้นหรือยัง
    เมื่อ status เป็น 'success' หรือ 'failed' จะได้ stdout, stderr, url และ exit_code กลับมาด้วย

    Returns:
        200 OK + DeploymentStatusResponse
        404 Not Found ถ้าไม่มี deployment_id นี้ใน Redis
    """
    record = await get_deployment(deployment_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Deployment '{deployment_id}' not found. It may have expired or never existed.",
        )

    return DeploymentStatusResponse(
        deployment_id=record.deployment_id,
        status=record.status,
        url=record.url,
        stdout=record.stdout,
        stderr=record.stderr,
        exit_code=record.exit_code,
        started_at=record.started_at,
        finished_at=record.finished_at,
    )
