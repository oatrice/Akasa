"""
Akasa Configuration — จัดการค่า settings จาก environment variables

ใช้ pydantic-settings เพื่อโหลดค่าจากไฟล์ .env อัตโนมัติ
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

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

    AKASA_API_KEY: str = "default-dev-key"
    AKASA_CHAT_ID: str = ""  # Default Telegram Chat ID for server-side notifications (e.g., task completion alerts)
    GITHUB_TOKEN: str = ""
    ALLOWED_TELEGRAM_CHAT_IDS: str = (
        ""  # Comma-separated list of Chat IDs (e.g., "123,456")
    )

    AVAILABLE_MODELS: dict[str, dict[str, str]] = {
        "gemini": {
            "name": "Google Gemini 2.5 Flash",
            "identifier": "google/gemini-2.5-flash",
        },
        "llama3": {
            "name": "Meta Llama 3.3 70B",
            "identifier": "meta-llama/llama-3.3-70b-instruct",
        },
        "deepseek-r1": {
            "name": "DeepSeek R1 (Reasoning)",
            "identifier": "deepseek/deepseek-r1",
        },
        "deepseek-chat": {
            "name": "DeepSeek Chat",
            "identifier": "deepseek/deepseek-chat",
        },
        "qwen-coder": {
            "name": "Qwen 2.5 Coder 32B",
            "identifier": "qwen/qwen-2.5-coder-32b-instruct",
        },
        "free-router": {
            "name": "OpenRouter Auto (Free)",
            "identifier": "openrouter/auto:free",
        },
        "claude": {
            "name": "Claude 3.5 Sonnet (Paid)",
            "identifier": "anthropic/claude-3.5-sonnet",
        },
        "gpt4o": {"name": "OpenAI GPT-4o (Paid)", "identifier": "openai/gpt-4o"},
        "gemini-pro": {
            "name": "Google Gemini Pro 1.5 (Paid)",
            "identifier": "google/gemini-pro-1.5",
        },
    }

    SYSTEM_PROMPT: str = (
        "You are Akasa, an expert AI assistant specializing in software development. "
        "Provide clear, concise, and technically accurate answers. "
        "Always use Markdown for code snippets with the correct language identifier. "
        "CRITICAL INSTRUCTION: You MUST ONLY answer questions related to programming, software development, IT, and computer science. "
        "If the user asks about ANY other unrelated topics (like travel, food, general advice, etc.), you must politely decline and state that you are a coding assistant."
    )


settings = Settings()
