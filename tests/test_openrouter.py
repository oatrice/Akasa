import os
import pytest
import responses
from unittest.mock import patch
import sys

# Add the project root to sys.path so we can import from scripts
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# We will import the function to test from scripts.test_openrouter
# For TDD, this import will initially fail until we create the file
from scripts.test_openrouter import call_openrouter_api

@responses.activate
def test_call_openrouter_api_success():
    # 1. Setup mock response
    api_key = "test_valid_key"
    os.environ["OPENROUTER_API_KEY"] = api_key
    
    expected_response = {
        "id": "gen-12345",
        "model": "mistralai/mistral-7b-instruct:free",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "2"
                }
            }
        ]
    }
    
    responses.add(
        responses.POST,
        "https://openrouter.ai/api/v1/chat/completions",
        json=expected_response,
        status=200
    )
    
    # 2. Execute
    # We will test a function call_openrouter_api(prompt, model)
    result = call_openrouter_api(prompt="What is 1+1?", model="mistralai/mistral-7b-instruct:free")
    
    # 3. Assert
    assert result is not None
    assert result["choices"][0]["message"]["content"] == "2"
    
    # Verify request headers
    assert len(responses.calls) == 1
    request = responses.calls[0].request
    assert request.headers["Authorization"] == f"Bearer {api_key}"
    assert request.headers["Content-Type"] == "application/json"

@responses.activate
def test_call_openrouter_api_unauthorized():
    # 1. Setup mock response for invalid key
    os.environ["OPENROUTER_API_KEY"] = "invalid_key"
    
    error_response = {
        "error": {
            "message": "Incorrect API key provided...",
            "type": "invalid_request_error",
            "code": "invalid_api_key"
        }
    }
    
    responses.add(
        responses.POST,
        "https://openrouter.ai/api/v1/chat/completions",
        json=error_response,
        status=401
    )
    
    # 2. Execute & Assert
    with pytest.raises(Exception) as exc_info:
        call_openrouter_api(prompt="Test prompt", model="mistralai/mistral-7b-instruct:free")
        
    assert "401" in str(exc_info.value)
