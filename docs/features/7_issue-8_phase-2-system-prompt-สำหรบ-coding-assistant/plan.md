# Implementation Plan: [Phase 2] System Prompt for Coding Assistant

> **Refers to**: [Spec Link](./spec.md)
> **Status**: Ready for Dev

## 1. Architecture & Design
*High-level technical approach.*

The implementation will focus on injecting a predefined "System Prompt" at the beginning of every conversation context sent to the Large Language Model (LLM). This prompt acts as a permanent instruction that defines the bot's persona and response style.

The logic will be centralized within the `chat_service.py`. Before calling the `llm_service`, the `handle_chat_message` function will construct the final `messages` payload by prepending the system prompt to the existing conversation history retrieved from Redis and the new user message. This system prompt is ephemeral for each request and will **not** be saved back into the Redis history, preventing context duplication and unnecessary memory usage.

### Component View
- **Modified Components**:
    - `app/config.py`: To store the system prompt text.
    - `app/services/chat_service.py`: To implement the logic of prepending the system prompt.
    - `tests/services/test_chat_service.py`: To update assertions and verify the new behavior.
- **New Components**:
    - None.
- **Dependencies**:
    - No new external dependencies are required.

### Data Model Changes
```python
# No data model changes are required. The change is in the construction of the
# `messages` list sent to the LLM API.
#
# The payload to the LLM will now look like this:
# [
#   {"role": "system", "content": "You are a coding assistant..."},
#   {"role": "user", "content": "Previous user message."},
#   {"role": "assistant", "content": "Previous assistant reply."},
#   {"role": "user", "content": "Current user message."}
# ]
```

---

## 2. Step-by-Step Implementation

### Step 1: Define the System Prompt in Configuration

- **Code**:
    1.  **Modify `app/config.py`**: Add a new setting to hold the system prompt string. This makes it easy to change the bot's persona in one place.
        ```python
        # In app/config.py
        class Settings(BaseSettings):
            # ... existing settings
            REDIS_TTL_SECONDS: int = 3600  # 1 hour
            
            # Add the new system prompt
            SYSTEM_PROMPT: str = (
                "You are Akasa, an expert AI assistant specializing in software development, Python, and FastAPI. "
                "Provide clear, concise, and technically accurate answers. "
                "Always use Markdown for code snippets with the correct language identifier (e.g., ```python)."
            )

        settings = Settings()
        ```
- **Verification**:
    - The application should start without errors.
    - The `settings.SYSTEM_PROMPT` can be imported and accessed from other modules.

### Step 2: Update Chat Service to Prepend System Prompt

- **Code**:
    1.  **Modify `app/services/chat_service.py`**: Update the `handle_chat_message` function to prepend the system prompt before calling the LLM.
        ```python
        # In app/services/chat_service.py
        from app.config import settings # Make sure settings is imported
        ...

        async def handle_chat_message(update: Update):
            ...
            
            # Define the system message
            system_message = {"role": "system", "content": settings.SYSTEM_PROMPT}
            
            try:
                history = await redis_service.get_chat_history(chat_id)
            except ConnectionError as e:
                logger.warning(f"Redis connection failed: {e}. Proceeding without history.")
                history = []
            
            # Construct the full context with the system prompt at the beginning
            messages = [system_message] + history + [{"role": "user", "content": user_prompt}]
            
            try:
                # The llm_service call now receives the full context
                llm_reply = await llm_service.get_llm_reply(messages=messages)
                ...
                # The logic for saving history remains unchanged, as it does not involve the system prompt
                await redis_service.add_message_to_history(chat_id, "user", user_prompt)
                await redis_service.add_message_to_history(chat_id, "assistant", llm_reply)
            ...
        ```
- **Verification**:
    - This logic change will be verified via updated unit tests in the next step.

### Step 3: Update Unit Tests for Chat Service

- **Code**:
    1.  **Modify `tests/services/test_chat_service.py`**: Update the existing tests to assert that the `llm_service.get_llm_reply` mock is called with a `messages` list that starts with the system prompt.
        ```python
        # In tests/services/test_chat_service.py
        ...
        from app.config import settings

        ...
        @patch("app.services.chat_service.llm_service")
        async def test_handle_chat_message_success(mock_llm, mock_telegram, mock_redis, mock_update):
            ...
            # Assertion
            mock_llm.get_llm_reply.assert_called_once()
            call_args = mock_llm.get_llm_reply.call_args[1]
            
            # Check that the first message is the system prompt
            assert call_args['messages'][0]['role'] == 'system'
            assert call_args['messages'][0]['content'] == settings.SYSTEM_PROMPT
            
            # Check that the last message is the user's new prompt
            assert call_args['messages'][-1]['role'] == 'user'
            assert call_args['messages'][-1]['content'] == "Hello Bot"
            ...
        ```
- **Verification**:
    - Run `pytest`. All tests in `tests/services/test_chat_service.py` must pass with the new assertions.

---

## 3. Verification Plan
*How will we verify success?*

### Automated Tests
- [ ] **Unit Tests**: Run `pytest`. The tests for `ChatService` must be updated to verify that the `messages` list passed to the `LLMService` correctly includes the system prompt as the first element.

### Manual Verification
- [ ] **Start the bot locally** with Redis running.
- [ ] **Ask a generic question**: Send a message like "Hello, who are you?". The bot's response should reflect its new persona as "Akasa, an expert AI assistant...".
- [ ] **Ask a technical question**: Send a message like "Write a python function to add two numbers". The response should be concise and include a properly formatted ` ```python` code block.
- [ ] **Check Redis**: Use a Redis client (`redis-cli`) to inspect the `chat_history:{chat_id}` key. Verify that the `system` message is **NOT** present in the stored history.