"""
Health Check Router

Router สำหรับ endpoint ดูสถานะระบบ
"""

from fastapi import APIRouter, Depends, HTTPException
import logging

# กำหนด redirect_slashes=False เพื่อ Strict Routing (ใส่ / ตอบกลับ 404 แทน 307)
router = APIRouter(tags=["Monitoring"], redirect_slashes=False)

def check_database() -> bool:
    """Dummy dependency จำลองเช็ค database connection"""
    # ในอนาคตจะเชื่อมต่อกับ DB จริง เช่น yield DB session
    return True

@router.get("/health")
def health_check(db_ok: bool = Depends(check_database)) -> dict:
    """
    Endpoint สำหรับตรวจสอบสถานะของระบบ (Health Check)
    """
    try:
        if db_ok:
            return {"status": "ok"}
    except Exception as e:
        # ถ้าพังให้พ่นหน้า Server Error 503 กลับไป แทนที่จะเป็น Internal Server Error ทั่วไป
        logging.error(f"Health check failed: {str(e)}")
        
    raise HTTPException(status_code=503, detail="Service Unavailable")
