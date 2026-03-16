import asyncio
from app.services.telegram_service import tg_service
import logging

logging.basicConfig(level=logging.ERROR)

async def main():
    chat_id = "6346467495"
    text = "A" * 5000
    try:
        await tg_service.send_message(chat_id, text, parse_mode=None)
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(main())
