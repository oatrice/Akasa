# Implementation Plan: [Phase 4] Multi-Model Selection via Chat Command

> **Refers to**: [Spec Link](./spec.md)
> **Status**: Ready for Dev

## 1. Architecture & Design
*High-level technical approach.*

This feature will be implemented by introducing a command-handling mechanism within the `ChatService`. When an incoming message is detected as a command (i.e., starts with `/`), it will be routed to a dedicated command processor instead of the standard chat flow.

The user's model preference will be persisted as a simple `STRING` in Redis, with the key `user_model_pref:<chat_id>`. For the standard chat flow, the `ChatService` will first query Redis for this preference. If a preference is found, it will be passed to the `LLMService`. If not found, or if Redis is unavailable, the system will gracefully fall back to using the default model specified in the application settings. This ensures both flexibility and resilience.

A model alias map will be defined in `app/config.py` to translate user-friendly names (e.g., `claude`) to the full model identifiers required by the OpenRouter API (e.g., `anthropic/claude-3.5-sonnet`).

### Component View
- **Modified Components**:
    - `app/config.py`: Add a dictionary to map model aliases to full model names.
    - `app/services/llm_service.py`: Parameterize the function to accept a dynamic model name.
    - `app/services/redis_service.py`: Add functions to get/set the user's model preference.
    - `app/services/chat_service.py`: Implement the core command parsing and model selection logic.
- **New Components**:
    - None. The logic will be added to existing services.
- **Dependencies**:
    - No new external dependencies are required.

### Data Model Changes
```python
# No new Pydantic models.
#
# Redis Data Structure:
# Key: "user_model_pref:{chat_id}"
# Type: STRING
# Value: "google/gemini-pro" (The full model identifier)
```

---

## 2. Step-by-Step Implementation

### Step 1: Update Configuration and Redis Service

- **Code**:
    1.  **Modify `app/config.py`**: Define the available models and their aliases.
        ```python
        # In app/config.py
        class Settings(BaseSettings):
            # ...
            AVAILABLE_MODELS: dict[str, dict[str, str]] = {
                "claude": {"name": "Claude 3.5 Sonnet", "identifier": "anthropic/claude-3.5-sonnet"},
                "gemini": {"name": "Google Gemini 2.5 Flash", "identifier": "google/gemini-flash"},
                "gpt4o": {"name": "OpenAI GPT-4o", "identifier": "openai/gpt-4o"},
            }
        ```
    2.  **Modify `app/services/redis_service.py`**: Add functions to manage the model preference.
        ```python
        # In app/services/redis_service.py
        # ...
        async def set_user_model_preference(chat_id: int, model_identifier: str):
            pref_key = f"user_model_pref:{chat_id}"
            await redis_pool.set(pref_key, model_identifier, ex=settings.REDIS_TTL_SECONDS)

        async def get_user_model_preference(chat_id: int) -> str | None:
            pref_key = f"user_model_pref:{chat_id}"
            return await redis_pool.get(pref_key)
        ```
- **Verification**:
    - Add unit tests for `get_user_model_preference` and `set_user_model_preference` in a new file `tests/services/test_redis_service.py` using `fakeredis`.

### Step 2: Parameterize the LLM Service

- **Code**:
    1.  **Modify `app/services/llm_service.py`**: Update `get_llm_reply` to accept an optional `model` argument.
        ```python
        # In app/services/llm_service.py
        # ...
        async def get_llm_reply(messages: list[dict], model: str | None = None) -> str:
            # ...
            payload = {
                "model": model or settings.LLM_MODEL, # Use passed model or fallback to default
                "messages": messages
            }
            # ...
        ```
- **Verification**:
    - Update the unit tests in `tests/services/test_llm_service.py` to check that the correct model is being used when the `model` parameter is provided.

### Step 3: Implement Command and Model Selection Logic in Chat Service

- **Code**:
    1.  **Refactor `app/services/chat_service.py`**: Separate the command handling from the regular message handling.
        ```python
        # In app/services/chat_service.py
        # ...
        async def handle_chat_message(update: Update):
            if not (update.message and update.message.text):
                return
            
            text = update.message.text
            if text.startswith("/"):
                await handle_command(update)
            else:
                await handle_standard_message(update)

        async def handle_command(update: Update):
            # ... (Implementation for /model command)
            # This is where you parse the command, validate, save to Redis, and reply.

        async def handle_standard_message(update: Update):
            # ... (Existing logic)
            # Modify this to get the user's preferred model from Redis.
            # If not found, use the default.
            # Pass the selected model to the llm_service call.
        ```
    2.  **Implement the full logic** for `handle_command` and `handle_standard_message` according to the specification.
- **Verification**:
    - Create extensive unit tests in `tests/services/test_chat_service.py` to cover all scenarios:
        - Setting a valid model.
        - Setting an invalid model.
        - Checking the current model.
        - Sending a regular message with a model preference set.
        - Sending a regular message with no preference set (should use default).
        - Sending a regular message when Redis is down (should use default).

---

## 3. Verification Plan
*How will we verify success?*

### Automated Tests
- [ ] **Unit Tests**: All new and modified tests for `redis_service`, `llm_service`, and `chat_service` must pass, covering all scenarios specified.

### Manual Verification
- [ ] **Setup**: Start the bot locally with Redis and `ngrok`.
- [ ] **1. Set Model**: Send the command `/model claude`.
    - **Expected**: Receive a confirmation message "✅ Model selection updated to: Claude 3.5 Sonnet."
- [ ] **2. Verify Model Usage**: Ask a question, e.g., "What's the latest news on Anthropic?".
    - **Expected**: The answer should be in the style of Claude.
- [ ] **3. Check Status**: Send the command `/model`.
    - **Expected**: Receive a status message: "❇️ Current model: `Claude 3.5 Sonnet`...".
- [ ] **4. Set Invalid Model**: Send `/model foo`.
    - **Expected**: Receive an error message listing the available models.
- [ ] **5. Fallback Check**: Restart the bot, but **do not** start Redis. Send a message.
    - **Expected**: The bot should still reply using the default model defined in the settings, demonstrating graceful degradation.