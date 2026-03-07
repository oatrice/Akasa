import asyncio
from app.config import settings
from app.services.telegram_service import send_message

async def main():
    try:
        # User's chat_id can be seen from previous test: 1111111 was mock, maybe let's getUpdates
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getUpdates")
            data = resp.json()
            print("Updates:", data)
            if data["ok"] and data["result"]:
                chat_id = data["result"][0]["message"]["chat"]["id"]
                print("Found chat_id:", chat_id)
                await send_message(chat_id, "Test from script")
                print("Sent successfully!")
            else:
                print("No updates found or error.")
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(main())
