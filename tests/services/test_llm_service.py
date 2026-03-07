import pytest
import httpx
from app.services.llm_service import get_llm_reply
from app.config import settings

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
    settings.OPENROUTER_API_KEY = "test_api_key"
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
    settings.OPENROUTER_API_KEY = "test_api_key"
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
