"""
Akasa API — FastAPI Backend Entry Point

จุดเริ่มต้นของแอปพลิเคชัน Backend สำหรับโปรเจกต์ Akasa
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.models.notification import TaskNotificationResponse
from app.routers import (
    actions,
    commands,
    context,
    deployments,
    health,
    notifications,
    telegram,
)
from app.routers.notifications import task_complete_notification

# ตั้งค่า Logging เบื้องต้น
logging.basicConfig(
    level=logging.INFO, format="%(levelname)s:     %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan: startup and graceful shutdown."""
    # Startup: Start the timeout watcher background task
    from app.services.timeout_watcher_service import timeout_watcher

    await timeout_watcher.start()
    logger.info("Timeout watcher started.")

    yield

    # Shutdown: Stop the timeout watcher
    await timeout_watcher.stop()
    logger.info("Timeout watcher stopped.")

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
app.include_router(deployments.router, prefix="/api/v1")
app.include_router(commands.router, prefix="/api/v1")
app.include_router(context.router, prefix="/api/v1")

# Backward-compatible webhook aliases (Issue #98). External agent/IDE systems
# call POST /notify_task_complete (and /api/notify_task_complete); both reuse the
# versioned handler and its X-Akasa-API-Key authentication.
app.add_api_route(
    "/notify_task_complete",
    task_complete_notification,
    methods=["POST"],
    response_model=TaskNotificationResponse,
    tags=["notifications"],
)
app.add_api_route(
    "/api/notify_task_complete",
    task_complete_notification,
    methods=["POST"],
    response_model=TaskNotificationResponse,
    tags=["notifications"],
    include_in_schema=False,
)
