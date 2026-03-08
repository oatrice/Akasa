import pytest
import httpx
from app.services.llm_service import get_llm_reply
from app.config import settings

@pytest.mark.asyncio
async def test_get_llm_reply_success(respx_mock):
    # Mock settings
    settings.LLM_API_KEY = "test_api_key"
    messages = [
        {"role": "user", "content": "Tell me about Python."},
        {"role": "assistant", "content": "Python is a programming language."},
        {"role": "user", "content": "What is it used for?"},
    ]
    expected_reply = "Python is used for web development, data science, and more."

    # Intercept OpenRouter API call
    route = respx_mock.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": expected_reply
                        }
                    }
                ]
            }
        )
    )

    # Call the service with messages list
    reply = await get_llm_reply(messages)

    # Assertions
    assert reply == expected_reply
    assert route.called
    assert route.calls[0].request.headers["Authorization"] == "Bearer test_api_key"
    import json
    sent_payload = json.loads(route.calls[0].request.content)
    # ต้องส่ง messages list ทั้งหมดไปให้ LLM (ไม่ใช่แค่ prompt เดียว)
    assert sent_payload["messages"] == messages

@pytest.mark.asyncio
async def test_get_llm_reply_api_error(respx_mock):
    # Mock settings
    settings.LLM_API_KEY = "test_api_key"
    messages = [{"role": "user", "content": "Hello AI"}]

    # Intercept OpenRouter API call and simulate a 500 error
    respx_mock.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )

    # Calling the service should raise an exception (like HTTPStatusError)
    with pytest.raises(httpx.HTTPStatusError):
        await get_llm_reply(messages)

@pytest.mark.asyncio
async def test_get_llm_reply_single_message(respx_mock):
    """ทดสอบกรณีส่ง message เดียว (ไม่มี history)"""
    settings.LLM_API_KEY = "test_api_key"
    messages = [{"role": "user", "content": "Hello"}]
    expected_reply = "Hi!"

    route = respx_mock.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {"content": expected_reply}}]}
        )
    )

    reply = await get_llm_reply(messages)

    assert reply == expected_reply
    import json
    sent_payload = json.loads(route.calls[0].request.content)
    assert len(sent_payload["messages"]) == 1
    assert sent_payload["messages"][0]["content"] == "Hello"


@pytest.mark.asyncio
async def test_get_llm_reply_with_custom_model(respx_mock):
    """ทดสอบการส่ง model parameter ไปยัง OpenRouter"""
    settings.LLM_API_KEY = "test_api_key"
    messages = [{"role": "user", "content": "Hello"}]
    custom_model = "anthropic/claude-3.5-sonnet"

    route = respx_mock.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {"content": "Claude reply"}}]}
        )
    )

    await get_llm_reply(messages, model=custom_model)

    import json
    sent_payload = json.loads(route.calls[0].request.content)
    assert sent_payload["model"] == custom_model


@pytest.mark.asyncio
async def test_get_llm_reply_uses_google_sdk_when_gemini_and_key_provided(monkeypatch):
    """ทดสอบว่าถ้าเป็นโมเดล gemini และมี GEMINI_API_KEY ให้ใช้ Google SDK โดยตรง"""
    from unittest.mock import AsyncMock, MagicMock
    import google.generativeai as genai

    # Mock settings
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "google_test_key")
    
    # Mock genai
    mock_chat = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Google AI reply"
    # send_message_async เป็น coroutine
    mock_chat.send_message_async = AsyncMock(return_value=mock_response)
    
    mock_model = MagicMock()
    mock_model.start_chat = MagicMock(return_value=mock_chat)
    
    monkeypatch.setattr(genai, "GenerativeModel", MagicMock(return_value=mock_model))
    monkeypatch.setattr(genai, "configure", MagicMock())

    messages = [{"role": "user", "content": "Hello Google"}]
    # ชื่อโมเดลที่มีคำว่า 'gemini'
    model = "google/gemini-pro-1.5"

    reply = await get_llm_reply(messages, model=model)

    assert reply == "Google AI reply"
    # ตรวจสอบว่าเรียก genai.configure ด้วย key ที่ถูกต้อง
    genai.configure.assert_called_with(api_key="google_test_key")
    # ตรวจสอบว่ามีการเรียก start_chat และ send_message_async
    mock_model.start_chat.assert_called_once()
    mock_chat.send_message_async.assert_called_once_with("Hello Google")
