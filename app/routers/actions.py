from fastapi import APIRouter, Header, HTTPException, Depends
from app.models.notification import (
    NotificationPayload, 
    ActionRequestResponse, 
    ActionRequestState
)
from app.services.telegram_service import tg_service
from app.services.redis_service import (
    set_action_request, 
    get_action_request, 
    has_session_permission
)
from app.config import settings
import logging
import asyncio

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/actions", tags=["actions"])

async def verify_api_key(x_akasa_api_key: str = Header(None)):
    """ตรวจสอบ API Key จาก Settings"""
    if not x_akasa_api_key or x_akasa_api_key != settings.AKASA_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return True

def validate_chat_id(chat_id: str):
    """ตรวจสอบว่า Chat ID ได้รับอนุญาตหรือไม่"""
    if not settings.ALLOWED_TELEGRAM_CHAT_IDS:
        # ถ้าไม่ได้ตั้งค่าไว้ ให้ผ่านได้ (เพื่อความยืดหยุ่นใน dev)
        return
    
    allowed_ids = [s.strip() for s in settings.ALLOWED_TELEGRAM_CHAT_IDS.split(",")]
    if chat_id not in allowed_ids:
        logger.warning(f"Unauthorized chat_id attempt: {chat_id}")
        raise HTTPException(status_code=403, detail=f"Chat ID {chat_id} is not allowed to receive notifications")

@router.post("/request", response_model=ActionRequestResponse)
async def create_action_request(
    payload: NotificationPayload,
    authenticated: bool = Depends(verify_api_key)
):
    """รับคำขอ Action Confirmation จาก CLI"""
    chat_id = payload.chat_id if hasattr(payload, "chat_id") else payload.user_id
    validate_chat_id(chat_id)
    
    metadata = payload.metadata
    if not metadata:
        raise HTTPException(status_code=400, detail="Metadata is required for action requests")
    
    request_id = metadata.get("request_id")
    command = metadata.get("command")
    cwd = metadata.get("cwd")
    session_id = metadata.get("session_id")
    
    # 1. เช็ค Session Permission ก่อน
    if session_id and await has_session_permission(session_id):
        logger.info(f"Action automatically allowed due to active session: {session_id}")
        # แจ้งเตือนผู้ใช้เสมอ (Log via Telegram)
        try:
            log_message = f"🛡️ *Auto-allowed (Session)*\n\n{payload.message}"
            await tg_service.send_message(chat_id=int(chat_id), text=log_message)
        except Exception as e:
            logger.error(f"Failed to send auto-allow notification: {e}")
            
        return ActionRequestResponse(
            request_id=request_id,
            status="allowed",
            session_permission=True
        )

    # 2. บันทึกสถานะ pending ลง Redis
    state = ActionRequestState(
        command=command,
        cwd=cwd,
        session_id=session_id,
        status="pending"
    )
    await set_action_request(request_id, state)
    
    # 3. ส่งข้อความเข้า Telegram พร้อมปุ่ม
    try:
        await tg_service.send_confirmation_message(
            chat_id=int(chat_id),
            text=payload.message,
            request_id=request_id
        )
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        raise HTTPException(status_code=500, detail="Failed to send notification to Telegram")
    
    return ActionRequestResponse(
        request_id=request_id,
        status="pending"
    )

@router.get("/requests/{request_id}", response_model=ActionRequestResponse)
async def get_request_status(
    request_id: str,
    authenticated: bool = Depends(verify_api_key)
):
    """เช็คสถานะของ Request (รองรับ Long-polling)"""
    max_wait = 30  # วินาที
    wait_interval = 1.5
    elapsed = 0
    
    while elapsed < max_wait:
        state = await get_action_request(request_id)
        if not state:
            raise HTTPException(status_code=404, detail="Request not found")
        
        if state.status != "pending":
            return ActionRequestResponse(
                request_id=request_id,
                status=state.status,
                session_permission=await has_session_permission(state.session_id) if state.session_id else False
            )
        
        await asyncio.sleep(wait_interval)
        elapsed += wait_interval
    
    # Timeout - คืนค่าสถานะปัจจุบัน (ซึ่งน่าจะเป็น pending)
    state = await get_action_request(request_id)
    return ActionRequestResponse(
        request_id=request_id,
        status=state.status if state else "pending"
    )
