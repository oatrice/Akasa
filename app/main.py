"""
Akasa API — FastAPI Backend Entry Point

จุดเริ่มต้นของแอปพลิเคชัน Backend สำหรับโปรเจกต์ Akasa
"""

from fastapi import FastAPI
from app.routers import health

app = FastAPI(
    title="Akasa API",
    version="0.1.0",
)

# บังคับ Strict Routing: /health จะไม่สนใจ /health/ และคืนค่า 404 แทนที่จะเป็น 307 Redirect
app.router.redirect_slashes = False

app.include_router(health.router)
