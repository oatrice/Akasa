# Implementation Plan: [Phase 1] Telegram Bot Webhook Integration

> **Refers to**: [Spec Link](./spec.md)
> **Status**: Ready for Dev

## 1. Architecture & Design
*High-level technical approach.*

This plan outlines the creation of a secure webhook endpoint to integrate the Akasa backend with the Telegram Bot API. The core of the implementation is a new API router (`/api/v1/telegram`) that listens for `POST` requests from Telegram.

Security is paramount; therefore, a dependency injection pattern will be used to enforce the validation of a secret token (`X-Telegram-Bot-Api-Secret-Token`) on every incoming request. We will also introduce Pydantic models to represent the Telegram `Update` object, ensuring type safety and making the data easy to work with.

### Component View
- **Modified Components**:
    - `.env.example`: Add new environment variables for Telegram.
    - `app/main.py`: Include the new Telegram router.
    - `requirements.txt`: Add `pydantic-settings` for better configuration management.
- **New Components**:
    - `app/config.py`: A centralized module for managing settings and secrets.
    - `app/models/telegram.py`: Pydantic models for deserializing Telegram API objects.
    - `app/routers/telegram.py`: The router handling the webhook logic.
    - `tests/routers/test_telegram.py`: Unit tests for the new webhook endpoint.
- **Dependencies**:
    - `pydantic-settings`: For loading configuration from environment variables cleanly.

### Data Model Changes
```python
# Defined in app/models/telegram.py
# (Simplified for brevity)

from pydantic import BaseModel
from typing import Optional

class User(BaseModel):
    id: int
    first_name: str

class Chat(BaseModel):
    id: int
    type: str

class Message(BaseModel):
    message_id: int
    chat: Chat
    from_user: Optional[User] = None
    text: Optional[str] = None

class Update(BaseModel):
    update_id: int
    message: Optional[Message] = None
```

---

## 2. Step-by-Step Implementation

### Step 1: Configuration and Dependencies

- **Code**:
    1.  **Update `.env.example`**: Add placeholder variables for Telegram secrets.
        ```
        TELEGRAM_BOT_TOKEN="your_bot_token_here"
        WEBHOOK_SECRET_TOKEN="a_strong_random_secret"
        ```
    2.  **Update `requirements.txt`**: Add `pydantic-settings`.
        ```diff
        ...
        httpx
        +pydantic-settings
        ```
    3.  **Create `app/config.py`**: Implement a settings management class.
        ```python
        from pydantic_settings import BaseSettings, SettingsConfigDict

        class Settings(BaseSettings):
            model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
            
            TELEGRAM_BOT_TOKEN: str
            WEBHOOK_SECRET_TOKEN: str

        settings = Settings()
        ```
- **Verification**:
    - Run `pip install -r requirements.txt`.
    - Create a `.env` file with the new variables. Verify that `from app.config import settings` can load them correctly in a Python shell.

### Step 2: Create Pydantic Models for Telegram

- **Code**:
    1.  **Create `app/models/telegram.py`**: Define the necessary models to represent a Telegram `Update` object as shown in the "Data Model Changes" section. This will help validate the structure of incoming data.
- **Verification**:
    - The file `app/models/telegram.py` exists and can be imported without syntax errors.

### Step 3: Implement the Telegram Webhook Router

- **Code**:
    1.  **Create `app/routers/telegram.py`**: Create the new router file.
    2.  **Implement Webhook Logic**: Add the code for the endpoint, including the security dependency.
        ```python
        import logging
        from fastapi import APIRouter, Request, Header, HTTPException, status
        from app.config import settings
        from app.models.telegram import Update

        router = APIRouter(prefix="/api/v1/telegram", tags=["Telegram"])
        logging.basicConfig(level=logging.INFO)

        # Dependency to verify the secret token
        async def verify_secret_token(x_telegram_bot_api_secret_token: str = Header(None)):
            if x_telegram_bot_api_secret_token is None:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Secret token missing")
            if x_telegram_bot_api_secret_token != settings.WEBHOOK_SECRET_TOKEN:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid secret token")

        @router.post("/webhook", dependencies=[Depends(verify_secret_token)])
        async def telegram_webhook(update: Update):
            """
            Receives updates from the Telegram Bot API.
            """
            logging.info(f"Received update: {update.model_dump_json(indent=2)}")
            # In this phase, we just acknowledge receipt.
            # Processing logic will be added in a future task.
            return {"status": "ok"}
        ```
    3.  **Update `app/main.py`**: Include the new router in the main FastAPI app.
        ```diff
        from fastapi import FastAPI
        - from app.routers import health
        + from app.routers import health, telegram
 
        app = FastAPI(...)
 
        app.include_router(health.router)
        + app.include_router(telegram.router)
        ```
- **Verification**: The server should restart. The new endpoint `/api/v1/telegram/webhook` should appear in the auto-generated docs at `http://127.0.0.1:8000/docs`.

### Step 4: Create Unit Tests

- **Code**:
    1.  **Create `tests/routers/test_telegram.py`**: Create the test file.
    2.  **Add Test Cases**: Implement tests for the success and failure scenarios defined in the spec.
        ```python
        from fastapi.testclient import TestClient
        from app.main import app
        from app.config import settings

        client = TestClient(app)
        WEBHOOK_URL = "/api/v1/telegram/webhook"
        VALID_TOKEN = settings.WEBHOOK_SECRET_TOKEN
        
        def test_webhook_success_valid_token():
            response = client.post(
                WEBHOOK_URL,
                headers={"X-Telegram-Bot-Api-Secret-Token": VALID_TOKEN},
                json={"update_id": 1, "message": {"message_id": 1, "chat": {"id": 1, "type": "private"}, "text": "test"}},
            )
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

        def test_webhook_fail_invalid_token():
            response = client.post(
                WEBHOOK_URL,
                headers={"X-Telegram-Bot-Api-Secret-Token": "invalid-token"},
                json={"update_id": 1},
            )
            assert response.status_code == 403
            assert response.json() == {"detail": "Invalid secret token"}

        def test_webhook_fail_missing_token():
            response = client.post(WEBHOOK_URL, json={"update_id": 1})
            assert response.status_code == 403
            assert response.json() == {"detail": "Secret token missing"}
        ```
- **Verification**: Run `pytest`. All tests in `tests/routers/test_telegram.py` must pass.

---

## 3. Verification Plan
*How will we verify success?*

### Automated Tests
- [ ] **Unit Tests**: Run `pytest`. All tests for the Telegram router must pass, covering valid token, invalid token, and missing token scenarios.

### Manual Verification
- [ ] **Prerequisite**: Start a tunneling service like `ngrok` to expose your local server: `ngrok http 8000`.
- [ ] **Set Webhook**: Use the `ngrok` HTTPS URL to set your bot's webhook with Telegram (can be done via a `curl` command or a simple script).
- [ ] **Send Message**: Send a message to your Telegram bot from the Telegram app.
- [ ] **Check Logs**: Observe the running FastAPI application's console logs. You should see the JSON payload of the message you sent, indicating the webhook was received successfully.
- [ ] **Check `ngrok` Inspector**: Use the `ngrok` web interface (usually at `http://127.0.0.1:4040`) to inspect the request and verify that your backend responded with `200 OK`.