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

app.include_router(health.router)
