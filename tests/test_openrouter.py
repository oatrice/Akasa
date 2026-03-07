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

def test_call_openrouter_api_missing_key():
    """Test that ValueError is raised when API key is not set."""
    # Remove the key from environment
    os.environ.pop("OPENROUTER_API_KEY", None)
    
    # Patch load_dotenv to prevent loading real .env file
    with patch("scripts.test_openrouter.load_dotenv"):
        with pytest.raises(ValueError) as exc_info:
            call_openrouter_api(prompt="Test prompt")
    
    assert "OPENROUTER_API_KEY" in str(exc_info.value)

@responses.activate
def test_call_openrouter_api_server_error():
    """Test that server errors (500/503) are handled correctly."""
    os.environ["OPENROUTER_API_KEY"] = "test_key"
    
    responses.add(
        responses.POST,
        "https://openrouter.ai/api/v1/chat/completions",
        json={"error": {"message": "Internal Server Error"}},
        status=500
    )
    
    with pytest.raises(Exception) as exc_info:
        call_openrouter_api(prompt="Test prompt")
    
    assert "500" in str(exc_info.value)

@responses.activate
def test_call_openrouter_api_malformed_response():
    """Test that malformed JSON (empty choices) raises ValueError, not IndexError."""
    os.environ["OPENROUTER_API_KEY"] = "test_key"
    
    # Response 200 OK but with empty choices list
    responses.add(
        responses.POST,
        "https://openrouter.ai/api/v1/chat/completions",
        json={"id": "gen-123", "choices": []},
        status=200
    )
    
    with pytest.raises(ValueError) as exc_info:
        call_openrouter_api(prompt="Test prompt")
    
    assert "choices" in str(exc_info.value).lower() or "response" in str(exc_info.value).lower()
