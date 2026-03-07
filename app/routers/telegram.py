"""
Telegram Webhook Router — รับ Webhook จาก Telegram Bot API

Endpoint: POST /api/v1/telegram/webhook
- ตรวจสอบ Secret Token จาก Header
- รับ Update object จาก Telegram
- ในเฟสนี้แค่ log ยังไม่ประมวลผล
"""

import logging
from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.config import settings
from app.models.telegram import Update

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/telegram", tags=["Telegram"])


async def verify_secret_token(
    x_telegram_bot_api_secret_token: str = Header(None),
):
    """Dependency สำหรับตรวจสอบ Secret Token ที่ Telegram ส่งมาใน Header"""
    if x_telegram_bot_api_secret_token is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Secret token missing",
        )
    if not settings.WEBHOOK_SECRET_TOKEN or x_telegram_bot_api_secret_token != settings.WEBHOOK_SECRET_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid secret token",
        )


@router.post("/webhook", dependencies=[Depends(verify_secret_token)])
async def telegram_webhook(update: Update):
    """
    รับ updates จาก Telegram Bot API

    ในเฟสนี้แค่ log ข้อมูลที่ได้รับ
    ยังไม่ประมวลผลหรือตอบกลับผู้ใช้
    """
    logger.info("Received Telegram update: %s", update.model_dump_json(indent=2))
    return {"status": "ok"}
