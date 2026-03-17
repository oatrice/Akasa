import asyncio

from app.config import settings
from app.services.telegram_service import TelegramService


async def main():
    tg = TelegramService(settings.TELEGRAM_BOT_TOKEN)
    text = "A" * 5000
    await tg.send_message(chat_id="6346467495", text=text, parse_mode=None)


if __name__ == "__main__":
    asyncio.run(main())

