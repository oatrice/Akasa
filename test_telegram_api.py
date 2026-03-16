import asyncio
import httpx
from app.services.telegram_service import TelegramService

async def main():
    tg = TelegramService()
    try:
        # A very long text?
        text = "A" * 5000
        await tg.send_message(chat_id="6346467495", text=text, parse_mode=None)
    except Exception as e:
        print(f"Error: {e}")
        if hasattr(e, 'response'):
            print(f"Response: {e.response.text}")

asyncio.run(main())
