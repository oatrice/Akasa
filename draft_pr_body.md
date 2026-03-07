## 🎯 [Phase 1] สร้าง Telegram Bot + webhook

Closes https://github.com/oatrice/Akasa/issues/3

### 📝 Summary

This PR integrates the Akasa backend with the **Telegram Bot API** by implementing a secure webhook endpoint. The system can now receive real-time messages from Telegram users, which is the foundation for building the AI Coding Assistant chatbot.

All work was developed following a strict **TDD (Test-Driven Development)** cycle.

### ✨ Changes Implemented

1.  **Configuration Management (`app/config.py`):**
    *   Created a centralized `Settings` class using `pydantic-settings` to securely load environment variables (`TELEGRAM_BOT_TOKEN`, `WEBHOOK_SECRET_TOKEN`) from the `.env` file.

2.  **Telegram Pydantic Models (`app/models/telegram.py`):**
    *   Defined `Update`, `Message`, `Chat`, and `TelegramUser` models to deserialize incoming Telegram payloads with type safety.
    *   Supports both `message` and `edited_message` update types.

3.  **Webhook Endpoint (`app/routers/telegram.py`):**
    *   New endpoint: `POST /api/v1/telegram/webhook`.
    *   **Security:** Validates `X-Telegram-Bot-Api-Secret-Token` header via FastAPI dependency injection. Rejects requests with invalid, missing, or empty tokens (403 Forbidden).
    *   Prevents authentication bypass when `WEBHOOK_SECRET_TOKEN` is an empty string.
    *   Logs received updates for debugging (processing logic deferred to Phase 2).

4.  **Comprehensive Test Suite (`tests/routers/test_telegram.py`):**
    *   7 test cases covering:
        *   ✅ Valid token → 200 OK
        *   ❌ Invalid token → 403
        *   ❌ Missing token → 403
        *   ❌ Unsupported HTTP method → 405
        *   ❌ Malformed payload → 422
        *   ❌ Empty token bypass prevention → 403
        *   ✅ Alternative update types (edited_message) → 200

5.  **Project Configuration:**
    *   Updated `.env.example` with `TELEGRAM_BOT_TOKEN` and `WEBHOOK_SECRET_TOKEN`.
    *   Added `pydantic-settings` to `requirements.txt`.
    *   Updated `app/main.py` to include the Telegram router.

### 🧪 How to Manually Verify

1.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Set up environment:**
    *   Copy `.env.example` to `.env` and add your Telegram Bot Token (from BotFather) and a strong random secret.

3.  **Run automated tests:**
    ```bash
    pytest -v
    ```
    *   All 18 tests should pass.

4.  **Test with real Telegram webhook:**
    ```bash
    ngrok http 8000
    curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=<NGROK_URL>/api/v1/telegram/webhook&secret_token=<SECRET>"
    ```
    *   Send a message to your bot in Telegram — observe `200 OK` in the server logs.