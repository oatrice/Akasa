"""
Akasa API — FastAPI Backend Entry Point

จุดเริ่มต้นของแอปพลิเคชัน Backend สำหรับโปรเจกต์ Akasa
"""

import logging
from fastapi import FastAPI
from app.routers import health, telegram, notifications, actions

# ตั้งค่า Logging เบื้องต้น
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:     %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Akasa API",
    version="0.1.0",
)

# บังคับ Strict Routing: /health จะไม่สนใจ /health/ และคืนค่า 404 แทนที่จะเป็น 307 Redirect
app.router.redirect_slashes = False

app.include_router(health.router)
app.include_router(telegram.router)
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(actions.router, prefix="/api/v1")
