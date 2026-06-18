import pytest
import httpx
from app.services.llm_service import get_llm_reply
from app.config import settings
from app.exceptions import LLMTimeoutError, LLMUpstreamError, LLMMalformedResponseError


@pytest.mark.asyncio
async def test_get_llm_reply_success(respx_mock):
    # Mock settings
    settings.OPENROUTER_API_KEY = "test_api_key"
    messages = [
        {"role": "user", "content": "Tell me about Python."},
        {"role": "assistant", "content": "Python is a programming language."},
        {"role": "user", "content": "What is it used for?"},
    ]
    expected_reply = "Python is used for web development, data science, and more."

    # Intercept OpenRouter API call
    route = respx_mock.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(
            200, json={"choices": [{"message": {"content": expected_reply}}]}
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
    settings.OPENROUTER_API_KEY = "test_api_key"
    messages = [{"role": "user", "content": "Hello AI"}]

    # Intercept OpenRouter API call and simulate a 500 error
    respx_mock.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )

    # Calling the service should raise a normalized upstream error
    with pytest.raises(LLMUpstreamError):
        await get_llm_reply(messages)


@pytest.mark.asyncio
async def test_get_llm_reply_timeout_error(respx_mock):
    settings.OPENROUTER_API_KEY = "test_api_key"
    messages = [{"role": "user", "content": "Hello AI"}]

    respx_mock.post("https://openrouter.ai/api/v1/chat/completions").mock(
        side_effect=httpx.TimeoutException("Timeout")
    )

    with pytest.raises(LLMTimeoutError):
        await get_llm_reply(messages)


@pytest.mark.asyncio
async def test_get_llm_reply_malformed_response(respx_mock):
    settings.OPENROUTER_API_KEY = "test_api_key"
    messages = [{"role": "user", "content": "Hello AI"}]

    respx_mock.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={"choices": []})
    )

    with pytest.raises(LLMMalformedResponseError):
        await get_llm_reply(messages)


@pytest.mark.asyncio
async def test_get_llm_reply_single_message(respx_mock):
    """ทดสอบกรณีส่ง message เดียว (ไม่มี history)"""
    settings.OPENROUTER_API_KEY = "test_api_key"
    messages = [{"role": "user", "content": "Hello"}]
    expected_reply = "Hi!"

    route = respx_mock.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(
            200, json={"choices": [{"message": {"content": expected_reply}}]}
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
    settings.OPENROUTER_API_KEY = "test_api_key"
    messages = [{"role": "user", "content": "Hello"}]
    custom_model = "anthropic/claude-3.5-sonnet"

    route = respx_mock.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(
            200, json={"choices": [{"message": {"content": "Claude reply"}}]}
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
    from google import genai

    # Mock settings
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "google_test_key")

    mock_response = MagicMock()
    mock_response.text = "Google AI reply"

    mock_aio_models = MagicMock()
    mock_aio_models.generate_content = AsyncMock(return_value=mock_response)

    mock_aio = MagicMock()
    mock_aio.models = mock_aio_models

    mock_client_instance = MagicMock()
    mock_client_instance.aio = mock_aio

    mock_client_class = MagicMock(return_value=mock_client_instance)
    monkeypatch.setattr(genai, "Client", mock_client_class)

    messages = [{"role": "user", "content": "Hello Google"}]
    # ชื่อโมเดลที่มีคำว่า 'gemini'
    model = "google/gemini-pro-1.5"

    reply = await get_llm_reply(messages, model=model)

    assert reply == "Google AI reply"
    # ตรวจสอบว่าเรียก Client ด้วย key ที่ถูกต้อง
    mock_client_class.assert_called_with(api_key="google_test_key")
    # ตรวจสอบว่ามีการเรียก generate_content
    mock_aio_models.generate_content.assert_called_once()


@pytest.mark.asyncio
async def test_get_llm_reply_insufficient_credits(respx_mock):
    """ทดสอบกรณี OpenRouter แจ้งเตือนเงินไม่พอ (Insufficient credits)"""
    from app.services.llm_service import OpenRouterInsufficientCreditsError

    settings.OPENROUTER_API_KEY = "test_api_key"
    messages = [{"role": "user", "content": "Hello"}]

    # 1. จำลองกรณี 402 Payment Required
    respx_mock.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(
            402, json={"error": {"message": "Insufficient credits", "code": 402}}
        )
    )

    with pytest.raises(OpenRouterInsufficientCreditsError):
        await get_llm_reply(messages)

    # 2. จำลองกรณี 400 Bad Request แต่ใน JSON บอกว่า Insufficient credits
    respx_mock.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(
            400, json={"error": {"message": "Credit balance too low", "code": 400}}
        )
    )

    with pytest.raises(OpenRouterInsufficientCreditsError):
        await get_llm_reply(messages)
