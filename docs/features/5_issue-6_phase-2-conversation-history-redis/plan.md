# Implementation Plan: [Phase 2] Conversation History with Redis

> **Refers to**: [Spec Link](./spec.md)
> **Status**: Ready for Dev

## 1. Architecture & Design
*High-level technical approach.*

This plan introduces a stateful conversation memory using Redis. The core idea is to store the recent turn-by-turn conversation for each unique `chat_id` in a Redis `LIST`.

- **Data Structure**: Each `chat_id` will have a corresponding key (e.g., `chat_history:12345`). The value will be a Redis `LIST` where each element is a JSON-serialized string representing a message object (`{"role": "user", "content": "..."}` or `{"role": "assistant", "content": "..."}`).
- **Workflow**: Before calling the LLM, the `ChatService` will fetch the recent history from Redis. After receiving a reply, it will append both the user's new message and the AI's reply to the list. The list's size will be capped to a fixed length (e.g., last 10 messages or 5 pairs) using `LTRIM` to manage context window size and memory usage.
- **Fault Tolerance**: The system will be designed to degrade gracefully. If Redis is unavailable, the `ChatService` will catch the connection error and proceed in a stateless mode, ensuring the bot remains operational.

### Component View
- **Modified Components**:
    - `app/config.py`: Add `REDIS_URL`.
    - `app/services/chat_service.py`: Major changes to incorporate history management logic.
    - `app/services/llm_service.py`: Modify function signature to accept a list of messages.
    - `requirements.txt`: Add the `redis` library.
- **New Components**:
    - `app/services/redis_service.py`: A dedicated service to encapsulate all Redis logic (connection, get/add history, trimming).
    - `tests/services/test_redis_service.py`: Unit tests for the new Redis service.
- **Dependencies**:
    - `redis`: The official asynchronous Python client for Redis.

### Data Model Changes
```python
# No changes to Pydantic models. The data structure will be handled in Redis.
# Redis Key: "chat_history:{chat_id}"
# Redis Type: LIST
# Redis Value Example:
# [
#   "{\"role\": \"assistant\", \"content\": \"It's a web framework.\"}",
#   "{\"role\": \"user\", \"content\": \"Tell me about Django.\"}"
# ]
# Note: New messages are pushed to the left (LPUSH).
```

---

## 2. Step-by-Step Implementation

### Step 1: Project Setup for Redis

- **Code**:
    1.  **Update `requirements.txt`**:
        ```diff
        ...
        httpx
        +redis
        ```
    2.  **Update `.env.example`**:
        ```diff
        ...
        WEBHOOK_SECRET_TOKEN="a_strong_random_secret"
        +REDIS_URL="redis://localhost:6379"
        ```
    3.  **Update `app/config.py`**:
        ```diff
        class Settings(BaseSettings):
            ...
            OPENROUTER_API_KEY: str = ""
        +   REDIS_URL: str = "redis://localhost:6379"
        ```
- **Verification**:
    - Run `pip install -r requirements.txt` to install the `redis` package.
    - Start a local Redis instance (e.g., `docker run -d -p 6379:6379 redis`).

### Step 2: Create the Redis Service

- **Code**:
    1.  **Create `app/services/redis_service.py`**: Implement connection handling and history management logic.
        ```python
        # In app/services/redis_service.py
        import redis.asyncio as redis
        import json
        from app.config import settings

        # Use a connection pool
        redis_pool = redis.from_url(settings.REDIS_URL, decode_responses=True)
        HISTORY_LIMIT = 10

        async def get_chat_history(chat_id: int) -> list[dict]:
            history_key = f"chat_history:{chat_id}"
            raw_history = await redis_pool.lrange(history_key, 0, HISTORY_LIMIT - 1)
            # Messages are stored LIFO, so reverse for chronological order
            return [json.loads(msg) for msg in reversed(raw_history)]

        async def add_message_to_history(chat_id: int, role: str, content: str):
            history_key = f"chat_history:{chat_id}"
            message = json.dumps({"role": role, "content": content})
            # Push to the head of the list
            await redis_pool.lpush(history_key, message)
            # Trim the list to keep it at the desired size
            await redis_pool.ltrim(history_key, 0, HISTORY_LIMIT - 1)
        ```
- **Verification**:
    - This service will be tested via unit tests in a later step.

### Step 3: Update LLM and Chat Services

- **Code**:
    1.  **Modify `app/services/llm_service.py`**: Change `get_llm_reply` to accept a list of message dictionaries.
        ```python
        # In app/services/llm_service.py
        ...
        async def get_llm_reply(messages: list[dict]) -> str:
            ...
            payload = {
                "model": "google/gemma-2-9b-it:free",
                "messages": messages  # Use the list directly
            }
            ...
        ```
    2.  **Modify `app/services/chat_service.py`**: Integrate Redis logic.
        ```python
        # In app/services/chat_service.py
        import logging
        from app.services import llm_service, telegram_service, redis_service
        from redis.exceptions import ConnectionError

        ...
        async def handle_chat_message(update: Update):
            ...
            chat_id = update.message.chat.id
            user_prompt = update.message.text
            
            try:
                history = await redis_service.get_chat_history(chat_id)
            except ConnectionError as e:
                logger.warning(f"Redis connection failed: {e}. Proceeding without history.")
                history = []
            
            # Construct the full context
            messages = history + [{"role": "user", "content": user_prompt}]
            
            try:
                llm_reply = await llm_service.get_llm_reply(messages=messages)
                await telegram_service.send_message(chat_id=chat_id, text=llm_reply)
                
                # Save to history only on success
                await redis_service.add_message_to_history(chat_id, "user", user_prompt)
                await redis_service.add_message_to_history(chat_id, "assistant", llm_reply)
                
            except Exception as e:
                logger.error(f"Error in chat loop for chat_id {chat_id}: {e}")
        ```
- **Verification**:
    - The code should be syntactically correct and reflect the new logic.

### Step 4: Implement Unit Tests

- **Code**:
    1.  **Create `tests/services/test_redis_service.py`**: Use a library like `fakeredis.aioredis` to mock Redis calls and test the history logic.
        - Test that `add_message_to_history` correctly adds items and trims the list.
        - Test that `get_chat_history` returns messages in the correct chronological order.
    2.  **Update `tests/services/test_chat_service.py`**:
        - Mock the `redis_service`.
        - Add a test case where `get_chat_history` returns a mock history, and assert that `llm_service.get_llm_reply` is called with the combined context.
        - Add a test case where `redis_service` raises a `ConnectionError`, and assert that the flow completes successfully in stateless mode.
- **Verification**:
    - Run `pytest`. All new and modified tests must pass.

---

## 3. Verification Plan
*How will we verify success?*

### Automated Tests
- [ ] **Unit Tests**: All tests in `tests/services/` must pass, covering the new `redis_service` and the updated `chat_service` logic for both happy path and Redis failure scenarios.

### Manual Verification
- [ ] **Setup**: Run a local Redis instance (`docker run -d -p 6379:6379 redis`).
- [ ] **Test Context**: Send a message to the bot, e.g., "What is FastAPI?". Then, send a follow-up, "What about Flask?". The bot's second reply should be a comparison, demonstrating it understood the context.
- [ ] **Test Isolation**: Use two different Telegram accounts to chat with the bot about different topics. Verify that the contexts are kept separate.
- [ ] **Test Fault Tolerance**: Stop the Redis Docker container. Send a new message to the bot. It should still reply, though it will not have any memory of previous messages.