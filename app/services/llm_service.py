import httpx
from app.config import settings

async def get_llm_reply(prompt: str) -> str:
    """
    Sends a prompt to the OpenRouter API and returns the generated reply.
    """
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "google/gemma-3-4b-it:free",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30.0 # Add a timeout for good measure
        )
        response.raise_for_status() # Raise exception for 4xx/5xx errors
        
        data = response.json()
        return data["choices"][0]["message"]["content"]
