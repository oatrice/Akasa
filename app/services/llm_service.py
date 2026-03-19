"""
LLM Service — ส่ง messages ไปยัง OpenRouter API และรับคำตอบกลับมา

รองรับการส่ง conversation history เป็น list ของ message dictionaries
"""

import httpx
import logging
import asyncio
import google.generativeai as genai
from typing import Optional, Any
from app.config import settings
from app.exceptions import LLMTimeoutError, LLMUpstreamError, LLMMalformedResponseError

logger = logging.getLogger(__name__)


class OpenRouterInsufficientCreditsError(Exception):
    """Exception raised when OpenRouter reports insufficient credits."""
    pass


async def get_llm_reply(messages: list[dict], model: Optional[str] = None, tools: Optional[list] = None) -> Any:
    """
    Sends a list of messages to the LLM (OpenRouter or Google SDK) and returns the generated reply.

    Args:
        messages: list ของ message dicts รูปแบบ [{"role": "user/assistant/system", "content": "..."}]
        model: ชื่อ identifier ของโมเดลที่ต้องการใช้ (ถ้าเป็น None จะใช้ค่าจาก settings)
        tools: รายการเครื่องมือ (tools) ที่ต้องการส่งให้ LLM
    """
    selected_model = model or settings.LLM_MODEL
    
    # 1. ถ้าเป็นโมเดลตระกูล gemini และมีการตั้งค่า GEMINI_API_KEY ไว้ ให้ใช้ Google SDK โดยตรง
    # หมายเหตุ: ปัจจุบัน Google SDK ใน wrapper นี้ยังไม่รองรับ tools ดังนั้นถ้ามี tools ให้ใช้ OpenRouter แทน
    if "gemini" in selected_model.lower() and settings.GEMINI_API_KEY and not tools:
        return await _get_google_gemini_reply(messages, selected_model)
    
    # 2. กรณีอื่นๆ ใช้ OpenRouter
    return await _get_openrouter_reply(messages, selected_model, tools)


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


async def _get_openrouter_reply(messages: list[dict], model: str, tools: Optional[list] = None) -> Any:
    """เรียกใช้ OpenRouter API พร้อม Retry เมื่อเจอ Server Error"""
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": messages
    }
    if tools:
        payload["tools"] = tools

    print(f"--- [DEBUG] Sending payload to OpenRouter: {payload} ---")

    max_retries = 3
    retry_delay = 1.0 # วินาที

    async with httpx.AsyncClient() as client:
        for attempt in range(max_retries):
            try:
                response = await client.post(
                    f"{settings.LLM_BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                
                # ถ้าเจอ 5xx (Server Error) ให้ลองใหม่
                if response.status_code >= 500 and attempt < max_retries - 1:
                    logger.warning(f"OpenRouter returned {response.status_code} (attempt {attempt+1}). Retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2 # Exponential backoff
                    continue
                
                # ตรวจสอบกรณี 402 Payment Required (OpenRouter ใช้สำหรับเงินไม่พอ)
                if response.status_code == 402:
                    raise OpenRouterInsufficientCreditsError("OpenRouter: Insufficient credits.")
                    
                data = {}
                try:
                    data = response.json()
                except Exception:
                    pass

                # ตรวจสอบข้อความ error message ใน JSON (บางครั้งอาจมาในรูป 400 Bad Request แต่เนื้อหาคือเงินไม่พอ)
                if isinstance(data, dict) and "error" in data:
                    error_msg = data["error"].get("message", "")
                    if "credits" in error_msg.lower() or "balance" in error_msg.lower():
                        raise OpenRouterInsufficientCreditsError(f"OpenRouter: {error_msg}")
                    
                    # ถ้าเป็น 500 ในรูปแบบ JSON error ให้ลองใหม่ได้
                    if response.status_code == 500 and attempt < max_retries - 1:
                         logger.warning(f"OpenRouter API returned 500 (attempt {attempt+1}). Retrying...")
                         await asyncio.sleep(retry_delay)
                         retry_delay *= 2
                         continue
                
                # ถ้าไม่ใช่ error เรื่องเงิน ให้ raise ตามปกติ
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    raise LLMUpstreamError(
                        f"OpenRouter API returned status {response.status_code}."
                    ) from exc
                
                try:
                    message = data["choices"][0]["message"]
                    # ถ้ามี tool_calls ให้ส่งคืนทั้ง message dict เพื่อให้ ChatService นำไปใช้ต่อ
                    if "tool_calls" in message and message["tool_calls"]:
                        return message
                    return message.get("content", "")
                except (KeyError, IndexError) as e:
                    # ถ้า API ตอบกลับมาผิดฟอร์มแต่ไม่ได้ติด error credits
                    if isinstance(data, dict) and "error" in data:
                        error_msg = data["error"].get("message", "Unknown OpenRouter error")
                        raise LLMUpstreamError(f"OpenRouter API Error: {error_msg}") from e
                    
                    print(f"--- [DEBUG] Malformed OpenRouter response: {data} ---")
                    raise LLMMalformedResponseError("Malformed OpenRouter response.") from e
                    
            except httpx.TimeoutException as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Network error (attempt {attempt+1}): {e}. Retrying...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                raise LLMTimeoutError("The LLM request timed out.") from e
            except httpx.ConnectError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Network error (attempt {attempt+1}): {e}. Retrying...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                raise LLMUpstreamError("Unable to reach the LLM provider.") from e
    
    raise LLMUpstreamError("Max retries exceeded for OpenRouter API")
