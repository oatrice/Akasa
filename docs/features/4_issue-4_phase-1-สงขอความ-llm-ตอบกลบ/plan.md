# Implementation Plan: [Phase 1] Core Chat Loop (Message → LLM → Reply)

> **Refers to**: [Spec Link](./spec.md)
> **Status**: Ready for Dev

## 1. Architecture & Design
*High-level technical approach.*

This implementation will complete the core chat loop by orchestrating data flow between the Telegram webhook, the OpenRouter LLM, and the Telegram `sendMessage` API. To ensure the webhook endpoint is highly responsive as required by Telegram, all time-consuming operations (API calls to external services) **must** be executed as background tasks.

We will introduce a **Service Layer** to encapsulate business logic and isolate concerns, making the system more modular and testable:
- `llm_service`: Responsible for all interactions with the OpenRouter API.
- `telegram_service`: Responsible for all interactions with the Telegram Bot API (e.g., sending messages).
- `chat_service`: The orchestrator that contains the core chat logic, using the other two services to process an incoming message and send a reply.

FastAPI's `BackgroundTasks` feature will be used in the webhook router to delegate the orchestration work to the `chat_service`, allowing the endpoint to return an immediate `200 OK` response.

### Component View
- **Modified Components**:
    - `app/routers/telegram.py`: Will be updated to use `BackgroundTasks` and call the new `ChatService`.
    - `requirements.txt`: Add `httpx` for making asynchronous HTTP requests.
- **New Components**:
    - `app/services/`: New directory for the service layer.
    - `app/services/llm_service.py`: New module for OpenRouter communication.
    - `app/services/telegram_service.py`: New module for Telegram API communication.
    - `app/services/chat_service.py`: New module for chat orchestration logic.
    - `tests/services/`: New directory for service layer tests.
- **Dependencies**:
    - `httpx`: An async-capable HTTP client for communicating with external APIs.

### Data Model Changes
```python
# No new data models are required. Existing models in app/models/telegram.py will be used.
```

---

## 2. Step-by-Step Implementation

### Step 1: Create Service Layer Structure and Dependencies

- **Code**:
    1.  **Create Service Directory**: Create a new directory `app/services/`.
    2.  **Create Service Modules**: Create empty files `app/services/__init__.py`, `app/services/llm_service.py`, `app/services/telegram_service.py`, and `app/services/chat_service.py`.
    3.  **Update `requirements.txt`**: Add `httpx`.
        ```diff
        ...
        pydantic-settings
        +httpx
        ```
- **Verification**:
    - Run `pip install -r requirements.txt`. The `httpx` library should be installed.
    - The new directory and files should exist.

### Step 2: Implement LLM and Telegram Services

- **Code**:
    1.  **Implement `llm_service.py`**: Create an `async` function to call the OpenRouter API.
        ```python
        # In app/services/llm_service.py
        import httpx
        from app.config import settings
        
        async def get_llm_reply(prompt: str) -> str:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}"},
                    json={"model": "google/gemma-2-9b-it:free", "messages": [{"role": "user", "content": prompt}]}
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
        ```
    2.  **Implement `telegram_service.py`**: Create an `async` function to send a message via the Telegram API.
        ```python
        # In app/services/telegram_service.py
        import httpx
        from app.config import settings

        async def send_message(chat_id: int, text: str):
            api_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
            async with httpx.AsyncClient() as client:
                response = await client.post(api_url, json={"chat_id": chat_id, "text": text})
                response.raise_for_status()
        ```
- **Verification**: These services will be tested in the next steps.

### Step 3: Implement Chat Orchestration Service

- **Code**: Create the main orchestration logic in `app/services/chat_service.py`.
    ```python
    # In app/services/chat_service.py
    import logging
    from app.models.telegram import Update
    from app.services import llm_service, telegram_service

    logger = logging.getLogger(__name__)

    async def handle_chat_message(update: Update):
        if not (update.message and update.message.text):
            logger.info("Ignoring update without a text message.")
            return

        chat_id = update.message.chat.id
        user_prompt = update.message.text

        try:
            llm_reply = await llm_service.get_llm_reply(prompt=user_prompt)
            await telegram_service.send_message(chat_id=chat_id, text=llm_reply)
        except Exception as e:
            logger.error(f"Error handling chat message for chat_id {chat_id}: {e}")
            # Optionally, send an error message back to the user
            # await telegram_service.send_message(chat_id=chat_id, text="Sorry, an error occurred.")
    ```
- **Verification**: The logic correctly calls the other services.

### Step 4: Integrate into Webhook Router with BackgroundTasks

- **Code**: Modify `app/routers/telegram.py` to use `BackgroundTasks`.
    ```python
    # In app/routers/telegram.py
    # ... (imports)
    from fastapi import BackgroundTasks
    from app.services import chat_service
    
    # ... (router setup)

    @router.post("/webhook", dependencies=[Depends(verify_secret_token)])
    async def telegram_webhook(update: Update, background_tasks: BackgroundTasks):
        """
        Receives updates from Telegram and adds the processing to a background task.
        """
        logger.info("Adding chat handler to background tasks for update_id: %s", update.update_id)
        background_tasks.add_task(chat_service.handle_chat_message, update)
        return {"status": "ok"}
    ```
- **Verification**: The webhook endpoint now accepts `BackgroundTasks` and delegates processing.

### Step 5: Implement Unit Tests for Services

- **Code**: Create test files in a new `tests/services/` directory. Use a mocking library like `respx` to mock `httpx` calls.
    - **`tests/services/test_chat_service.py`**: Mock `llm_service` and `telegram_service` to verify that `handle_chat_message` calls them with the correct arguments.
    - Test the error handling path where `llm_service` raises an exception.
- **Verification**: Run `pytest`. All new service tests must pass.

---

## 3. Verification Plan
*How will we verify success?*

### Automated Tests
- [ ] **Unit Tests**: Run `pytest`. All new tests for the `llm`, `telegram`, and `chat` services must pass, using mocks for external API calls.

### Manual Verification
- [ ] **Prerequisite**: Use `ngrok` to create a public URL for your local server (`ngrok http 8000`).
- [ ] **Set Webhook**: Ensure your Telegram Bot's webhook is set to the `ngrok` URL.
- [ ] **Send Test Message**: Send a message (e.g., "Hello, what is FastAPI?") to your bot in the Telegram app.
- [ ] **Verify Response**: Confirm that you receive a reply from the bot in the chat.
- [ ] **Check Logs**: Inspect the server console logs to see the "Received update" message, followed by logs from the service layer, confirming the background task is working. The initial webhook response should be immediate.