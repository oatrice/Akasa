"""
Akasa Configuration — จัดการค่า settings จาก environment variables

ใช้ pydantic-settings เพื่อโหลดค่าจากไฟล์ .env อัตโนมัติ
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    TELEGRAM_BOT_TOKEN: str = ""
    WEBHOOK_SECRET_TOKEN: str = ""
    OPENROUTER_API_KEY: str = ""
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_HISTORY_LIMIT: int = 10
    REDIS_TTL_SECONDS: int = 86400  # 24 hours

    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://openrouter.ai/api/v1"
    LLM_MODEL: str = "google/gemini-2.5-flash"
    
    SYSTEM_PROMPT: str = (
        "You are Akasa, an expert AI assistant specializing in software development. "
        "Provide clear, concise, and technically accurate answers. "
        "Always use Markdown for code snippets with the correct language identifier."
    )

settings = Settings()
