from fastapi import APIRouter, Header, HTTPException, Depends
from app.models.notification import NotificationPayload, NotificationResponse
from app.services.telegram_service import tg_service
from app.services.redis_service import redis_pool
from app.config import settings
from app.exceptions import UserChatIdNotFoundException, BotBlockedException
import logging

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
        is_valid_in_redis = await redis_pool.sismember("akasa_api_keys", x_akasa_api_key)
        if is_valid_in_redis:
            return True
    except Exception as e:
        logger.error(f"Error checking API key in Redis: {e}")

    raise HTTPException(status_code=401, detail="Invalid or missing API key")

@router.post("/send", response_model=NotificationResponse)
async def send_notification(
    payload: NotificationPayload,
    authenticated: bool = Depends(verify_api_key)
):
    """รับการแจ้งเตือนจากภายนอกและส่งหา User"""
    logger.info(f"Incoming notification for user_id: {payload.user_id}, priority: {payload.priority}")
    if payload.metadata:
        logger.info(f"Notification metadata: {payload.metadata}")
    
    # จัดการ Priority (B) ผ่านโมเดล
    message_text = payload.get_formatted_message()
    
    try:
        # ตรวจสอบการแปลง user_id เป็น int (เพื่อความชัวร์ว่าไม่ตายตรงนี้)
        u_id = int(payload.user_id)
        
        await tg_service.send_proactive_message(
            user_id=u_id, 
            text=message_text
        )
        return NotificationResponse(
            status="success", 
            message="Notification queued for delivery."
        )
    except UserChatIdNotFoundException as e:
        logger.warning(f"Notification error: {e}")
        raise HTTPException(status_code=400, detail="User not found for notification")
    except BotBlockedException as e:
        logger.warning(f"Notification error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send notification: Bot blocked by user.")
    except ValueError:
        logger.error(f"Invalid user_id format: {payload.user_id}")
        raise HTTPException(status_code=400, detail="Invalid user_id format. Must be numeric.")
    except Exception as e:
        logger.error(f"Error in send_notification: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred during notification dispatch.")
