import asyncio
import httpx
from app.config import settings
async def main():
    payload = {"model": "google/gemma-2-9b-it:free", "messages": [{"role": "user", "content": "hi"}]}
    async with httpx.AsyncClient() as client:
        resp = await client.post("https://openrouter.ai/api/v1/chat/completions", headers={"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}"}, json=payload)
        print("gemma-2-9b-it", resp.status_code, resp.text)
    
    payload["model"] = "google/gemma-3-4b-it:free"
    async with httpx.AsyncClient() as client:
        resp = await client.post("https://openrouter.ai/api/v1/chat/completions", headers={"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}"}, json=payload)
        print("gemma-3-4b-it", resp.status_code, resp.text)

asyncio.run(main())
