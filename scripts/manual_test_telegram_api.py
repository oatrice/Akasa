import asyncio
import os
import sys
from pathlib import Path

import httpx

# Allow running from repo root: `python3 scripts/...py`
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from app.config import settings
from app.services.telegram_service import TelegramService


async def main():
    tg = TelegramService(settings.TELEGRAM_BOT_TOKEN)
    chat_id = os.getenv("AKASA_CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID") or "6346467495"
    length = int(os.getenv("AKASA_TEST_MESSAGE_LEN", "4000"))
    text = "A" * length
    try:
        await tg.send_message(chat_id=chat_id, text=text, parse_mode=None)
        print(f"Sent {length} chars to chat_id={chat_id}")
    except httpx.HTTPStatusError as e:
        desc = ""
        try:
            desc = e.response.text
        except Exception:
            pass
        print(f"Telegram send failed (status={getattr(e.response, 'status_code', None)}): {desc or str(e)}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    asyncio.run(main())

