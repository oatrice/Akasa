import httpx
from app.config import settings

async def send_message(chat_id: int, text: str) -> None:
    """
    Sends a text message to a specific chat using the Telegram Bot API.
    """
    api_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": text
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            api_url,
            json=payload,
            timeout=10.0
        )
        response.raise_for_status()
