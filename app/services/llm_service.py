"""
LLM Service — ส่ง messages ไปยัง OpenRouter API และรับคำตอบกลับมา

รองรับการส่ง conversation history เป็น list ของ message dictionaries
"""

import httpx
import logging
import google.generativeai as genai
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)


async def get_llm_reply(messages: list[dict], model: Optional[str] = None) -> str:
    """
    Sends a list of messages to the LLM (OpenRouter or Google SDK) and returns the generated reply.

    Args:
        messages: list ของ message dicts รูปแบบ [{"role": "user/assistant/system", "content": "..."}]
        model: ชื่อ identifier ของโมเดลที่ต้องการใช้ (ถ้าเป็น None จะใช้ค่าจาก settings)
    """
    selected_model = model or settings.LLM_MODEL
    
    # 1. ถ้าเป็นโมเดลตระกูล gemini และมีการตั้งค่า GEMINI_API_KEY ไว้ ให้ใช้ Google SDK โดยตรง
    if "gemini" in selected_model.lower() and settings.GEMINI_API_KEY:
        return await _get_google_gemini_reply(messages, selected_model)
    
    # 2. กรณีอื่นๆ ใช้ OpenRouter
    return await _get_openrouter_reply(messages, selected_model)


async def _get_google_gemini_reply(messages: list[dict], model: str) -> str:
    """เรียกใช้ Google Generative AI SDK โดยตรง"""
    logger.info(f"Using Google SDK for model: {model}")
    genai.configure(api_key=settings.GEMINI_API_KEY)
    
    # แปลงรูปแบบ messages ให้เข้ากับ Gemini SDK (user/model)
    gemini_history = []
    # Gemini แยก System Prompt ออกมาตอนสร้าง model
    system_instruction = None
    
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        
        if role == "system":
            system_instruction = content
        elif role == "user":
            gemini_history.append({"role": "user", "parts": [content]})
        elif role == "assistant":
            gemini_history.append({"role": "model", "parts": [content]})
            
    # ดึงข้อความล่าสุดออกมาเป็น prompt
    if not gemini_history:
        return "No user message found."
        
    last_msg = gemini_history.pop()
    prompt = last_msg["parts"][0]
    
    # สร้าง model พร้อม system instruction (ถ้ามี)
    # ตัด 'google/' ออกจากชื่อโมเดลถ้ามี เพราะ SDK ใช้แค่ชื่อรุ่น (เช่น gemini-1.5-pro)
    sdk_model_name = model.replace("google/", "")
    generative_model = genai.GenerativeModel(
        model_name=sdk_model_name,
        system_instruction=system_instruction
    )
    
    # เริ่มแชทด้วยประวัติที่เหลือ
    chat = generative_model.start_chat(history=gemini_history)
    response = await chat.send_message_async(prompt)
    
    return response.text


async def _get_openrouter_reply(messages: list[dict], model: str) -> str:
    """เรียกใช้ OpenRouter API ตามปกติ"""
    headers = {
        "Authorization": f"Bearer {settings.LLM_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": messages
    }

    logger.debug(f"Sending payload to OpenRouter: {payload}")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.LLM_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30.0
        )
        response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"]
