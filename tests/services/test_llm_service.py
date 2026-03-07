import pytest
import httpx
from app.services.llm_service import get_llm_reply
from app.config import settings

@pytest.mark.asyncio
async def test_get_llm_reply_success(respx_mock):
    # Mock settings
    settings.OPENROUTER_API_KEY = "test_api_key"
    prompt = "Hello AI"
    expected_reply = "Hi there! I am an AI."

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

    # Call the service
    reply = await get_llm_reply(prompt)

    # Assertions
    assert reply == expected_reply
    assert route.called
    assert route.calls[0].request.headers["Authorization"] == "Bearer test_api_key"
    import json
    assert json.loads(route.calls[0].request.content)["messages"][0]["content"] == prompt

@pytest.mark.asyncio
async def test_get_llm_reply_api_error(respx_mock):
    # Mock settings
    settings.OPENROUTER_API_KEY = "test_api_key"
    prompt = "Hello AI"

    # Intercept OpenRouter API call and simulate a 500 error
    respx_mock.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )

    # Calling the service should raise an exception (like HTTPStatusError)
    with pytest.raises(httpx.HTTPStatusError):
        await get_llm_reply(prompt)
