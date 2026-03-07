import asyncio
from app.services.llm_service import get_llm_reply

async def main():
    try:
        reply = await get_llm_reply("hello testing")
        print("REPLY:", reply)
    except Exception as e:
        print("ERROR:", str(e))
        import traceback
        traceback.print_exc()

asyncio.run(main())
