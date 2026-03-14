import logging
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException

from app.config import settings
from app.exceptions import BotBlockedException, UserChatIdNotFoundException
from app.models.notification import (
    NotificationPayload,
    NotificationResponse,
    ReviewReadyRequest,
    ReviewReadyResponse,
    TaskNotificationRequest,
    TaskNotificationResponse,
)
from app.services.redis_service import redis_pool
from app.services.telegram_service import tg_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notifications", tags=["notifications"])


async def verify_api_key(x_akasa_api_key: str = Header(None)):
    """ตรวจสอบ API Key จากทั้ง Environment (Settings) และ Redis"""
    if not x_akasa_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    # 1. เช็คจาก Environment (Settings)
    if x_akasa_api_key == settings.AKASA_API_KEY:
        return True

    # 2. เช็คจาก Redis (กรณีต้องการรองรับหลาย Key หรือ Key ที่เปลี่ยนพลวัต)
    try:
        # สมมติว่าเก็บ API Key อื่นๆ ไว้ใน SET ชื่อ 'akasa_api_keys' หรือเช็คโดยตรง
        is_valid_in_redis = await redis_pool.sismember(
            "akasa_api_keys", x_akasa_api_key
        )
        if is_valid_in_redis:
            return True
    except Exception as e:
        logger.error(f"Error checking API key in Redis: {e}")

    raise HTTPException(status_code=401, detail="Invalid or missing API key")


@router.post("/send", response_model=NotificationResponse)
async def send_notification(
    payload: NotificationPayload, authenticated: bool = Depends(verify_api_key)
):
    """รับการแจ้งเตือนจากภายนอกและส่งหา User"""
    logger.info(
        f"Incoming notification for user_id: {payload.user_id}, priority: {payload.priority}"
    )
    if payload.metadata:
        logger.info(f"Notification metadata: {payload.metadata}")

    # จัดการ Priority (B) ผ่านโมเดล
    message_text = payload.get_formatted_message()

    try:
        # ตรวจสอบการแปลง user_id เป็น int (เพื่อความชัวร์ว่าไม่ตายตรงนี้)
        u_id = int(payload.user_id)

        await tg_service.send_proactive_message(user_id=u_id, text=message_text)
        return NotificationResponse(
            status="success", message="Notification queued for delivery."
        )
    except UserChatIdNotFoundException as e:
        logger.warning(f"Notification error: {e}")
        raise HTTPException(status_code=400, detail="User not found for notification")
    except BotBlockedException as e:
        logger.warning(f"Notification error: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to send notification: Bot blocked by user."
        )
    except ValueError:
        logger.error(f"Invalid user_id format: {payload.user_id}")
        raise HTTPException(
            status_code=400, detail="Invalid user_id format. Must be numeric."
        )
    except Exception as e:
        logger.error(f"Error in send_notification: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred during notification dispatch.",
        )


@router.post("/task-complete", response_model=TaskNotificationResponse)
async def task_complete_notification(
    payload: TaskNotificationRequest,
    authenticated: bool = Depends(verify_api_key),
):
    """
    รับการแจ้งเตือน Task Completion จาก AI Assistants (MCP Tool หรือ CLI)
    และส่งข้อความสรุปงานไปยัง Telegram

    Chat ID routing:
      1. ใช้ chat_id จาก payload ถ้ามี (caller-specified)
      2. Fallback ไปใช้ AKASA_CHAT_ID จาก server config
    """
    # Resolve chat_id: caller-provided takes precedence over server default
    chat_id_str = payload.chat_id or settings.AKASA_CHAT_ID
    if not chat_id_str:
        raise HTTPException(
            status_code=400,
            detail="No chat_id provided and AKASA_CHAT_ID is not configured on the server.",
        )

    try:
        chat_id = int(chat_id_str)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid chat_id format. Must be numeric.",
        )

    logger.info(
        f"Task notification received — project: {payload.project!r}, "
        f"task: {payload.task!r}, status: {payload.status}, source: {payload.source!r}"
    )

    try:
        await tg_service.send_task_notification(chat_id=chat_id, request=payload)
        return TaskNotificationResponse(
            delivered=True,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            logger.warning(
                f"Telegram rate limit hit while sending task notification to chat_id {chat_id}: {e}"
            )
            raise HTTPException(
                status_code=429,
                detail="Telegram rate limit exceeded. Please retry after a moment.",
            )
        logger.error(
            f"Telegram API error in task_complete_notification (chat_id={chat_id}): {e}",
            exc_info=True,
        )
        return TaskNotificationResponse(
            delivered=False,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        logger.error(
            f"Unexpected error in task_complete_notification: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred during task notification dispatch.",
        )


@router.post("/review-ready", response_model=ReviewReadyResponse)
async def review_ready_notification(
    payload: ReviewReadyRequest,
    authenticated: bool = Depends(verify_api_key),
):
    """
    รับการแจ้งเตือน "Changes Ready for Review" จาก Zed AI (ผ่าน MCP tool notify_pending_review)
    และส่งข้อความ "✏️ Changes Ready for Review" ไปยัง Telegram

    เรียกใช้เมื่อ AI ใน Zed Agent mode ทำการ generate/แก้ไขโค้ดเสร็จแล้ว
    และกำลังรอให้ผู้ใช้กด Accept / Reject ใน IDE

    Chat ID routing:
      1. ใช้ chat_id จาก payload ถ้ามี
      2. Fallback ไปใช้ AKASA_CHAT_ID จาก server config
    """
    chat_id_str = payload.chat_id or settings.AKASA_CHAT_ID
    if not chat_id_str:
        raise HTTPException(
            status_code=400,
            detail="No chat_id provided and AKASA_CHAT_ID is not configured on the server.",
        )

    try:
        chat_id = int(chat_id_str)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid chat_id format. Must be numeric.",
        )

    logger.info(
        f"Review-ready notification received — project: {payload.project!r}, "
        f"task: {payload.task!r}, files: {len(payload.files_changed or [])} file(s)"
    )

    try:
        await tg_service.send_review_notification(chat_id=chat_id, request=payload)
        return ReviewReadyResponse(
            delivered=True,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            logger.warning(
                f"Telegram rate limit hit while sending review-ready notification to chat_id {chat_id}: {e}"
            )
            raise HTTPException(
                status_code=429,
                detail="Telegram rate limit exceeded. Please retry after a moment.",
            )
        logger.error(
            f"Telegram API error in review_ready_notification (chat_id={chat_id}): {e}",
            exc_info=True,
        )
        return ReviewReadyResponse(
            delivered=False,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        logger.error(
            f"Unexpected error in review_ready_notification: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred during review-ready notification dispatch.",
        )
