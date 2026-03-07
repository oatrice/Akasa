"""
LLM Service — ส่ง messages ไปยัง OpenRouter API และรับคำตอบกลับมา

รองรับการส่ง conversation history เป็น list ของ message dictionaries
"""

import httpx
import logging
from app.config import settings

logger = logging.getLogger(__name__)


async def get_llm_reply(messages: list[dict]) -> str:
    """
    Sends a list of messages to the OpenRouter API and returns the generated reply.

    Args:
        messages: list ของ message dicts รูปแบบ [{"role": "user/assistant", "content": "..."}]
    """
    headers = {
        "Authorization": f"Bearer {settings.LLM_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": settings.LLM_MODEL,
        "messages": messages
    }

    logger.warning(f"Sending payload to OpenRouter: {payload}")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.LLM_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30.0
        )
        response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"]
