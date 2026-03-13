"""
Akasa API — FastAPI Backend Entry Point

จุดเริ่มต้นของแอปพลิเคชัน Backend สำหรับโปรเจกต์ Akasa
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routers import actions, health, notifications, telegram

# ตั้งค่า Logging เบื้องต้น
logging.basicConfig(
    level=logging.INFO, format="%(levelname)s:     %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan: startup and graceful shutdown."""
    yield
    # Gracefully close the shared httpx.AsyncClient used by TelegramService
    from app.services.telegram_service import tg_service

    await tg_service.client.aclose()
    logger.info("TelegramService httpx client closed.")


app = FastAPI(
    title="Akasa API",
    version="0.1.0",
    lifespan=lifespan,
)

# บังคับ Strict Routing: /health จะไม่สนใจ /health/ และคืนค่า 404 แทนที่จะเป็น 307 Redirect
app.router.redirect_slashes = False

app.include_router(health.router)
app.include_router(telegram.router)
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(actions.router, prefix="/api/v1")
