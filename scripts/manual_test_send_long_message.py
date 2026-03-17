import asyncio
import logging
import os
import sys
from pathlib import Path

# Allow running from repo root: `python3 scripts/...py`
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from app.services.telegram_service import tg_service


logging.basicConfig(level=logging.ERROR)


async def main():
    # Telegram message hard limit is 4096 characters.
    # Use <= 4000 by default so the manual script succeeds.
    chat_id = os.getenv("AKASA_CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID") or "6346467495"
    length = int(os.getenv("AKASA_TEST_MESSAGE_LEN", "4000"))
    text = "A" * length
    try:
        await tg_service.send_message(chat_id, text, parse_mode=None)
    except Exception as e:
        print(f"Exception: {e}")


if __name__ == "__main__":
    asyncio.run(main())

