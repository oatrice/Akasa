"""
Akasa Configuration — จัดการค่า settings จาก environment variables

ใช้ pydantic-settings เพื่อโหลดค่าจากไฟล์ .env อัตโนมัติ
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    TELEGRAM_BOT_TOKEN: str = ""
    WEBHOOK_SECRET_TOKEN: str = ""
    ENVIRONMENT: str = "production"
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_HISTORY_LIMIT: int = 10
    REDIS_TTL_SECONDS: int = 86400  # 24 hours

    OPENROUTER_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    LLM_BASE_URL: str = "https://openrouter.ai/api/v1"
    LLM_MODEL: str = "google/gemini-2.5-flash"

    AVAILABLE_MODELS: dict[str, dict[str, str]] = {
        "claude": {"name": "Claude 3.5 Sonnet", "identifier": "anthropic/claude-3.5-sonnet"},
        "gemini": {"name": "Google Gemini 2.5 Flash", "identifier": "google/gemini-2.5-flash"},
        "gpt4o": {"name": "OpenAI GPT-4o", "identifier": "openai/gpt-4o"},
        "gemini-pro": {"name": "Google Gemini Pro 1.5", "identifier": "google/gemini-pro-1.5"},
        "kimi": {"name": "Moonshot Kimi", "identifier": "moonshot/moonshot-v1-8k"},
        "deepseek-coder": {"name": "DeepSeek Coder (Free)", "identifier": "deepseek/deepseek-coder:free"},
        "llama3": {"name": "Meta Llama 3 (Free)", "identifier": "meta-llama/llama-3-8b-instruct:free"},
        "free-router": {"name": "OpenRouter Free Router", "identifier": "openrouter/auto:free"},
    }
    
    SYSTEM_PROMPT: str = (
        "You are Akasa, an expert AI assistant specializing in software development. "
        "Provide clear, concise, and technically accurate answers. "
        "Always use Markdown for code snippets with the correct language identifier. "
        "CRITICAL INSTRUCTION: You MUST ONLY answer questions related to programming, software development, IT, and computer science. "
        "If the user asks about ANY other unrelated topics (like travel, food, general advice, etc.), you must politely decline and state that you are a coding assistant."
    )

settings = Settings()
