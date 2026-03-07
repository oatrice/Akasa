# Luma Code Review Report

**Date:** 2026-03-08 05:47:59
**Files Reviewed:** ['app/services/llm_service.py', 'tests/services/test_chat_service.py', 'app/config.py', 'app/services/chat_service.py']

## 📝 Reviewer Feedback

The code is well-tested and includes good features like graceful degradation for Redis failures and detailed build information for local development. However, there are several areas that need improvement for robustness, consistency, and style.

### High Priority Issue

1.  **`app/services/chat_service.py` - Silent Failure on Unexpected Errors**
    *   **Problem:** In `handle_chat_message`, the final `except Exception as e:` block only logs the error and then returns. This means if an unexpected error occurs while getting the LLM reply, the user's message is silently ignored, and they receive no feedback.
    *   **Fix:** The bot should always inform the user about a problem. This block should also call `telegram_service.send_message` with a generic error message, similar to how `HTTPError` or `TimeoutException` are handled.

    ```python
    # In app/services/chat_service.py, inside handle_chat_message()

    # ...
    except Exception as e:
        logger.error(f"Unexpected error getting LLM reply for {chat_id}: {e}")
        # ADD THIS LINE to notify the user
        await telegram_service.send_message(chat_id, "ขออภัย เกิดข้อผิดพลาดที่ไม่คาดคิด โปรดลองอีกครั้งในภายหลัง")
        return
    ```

### Maintainability & Consistency Issues

1.  **`app/services/llm_service.py` - Inconsistent API Key Configuration**
    *   **Problem:** `app/config.py` defines both `LLM_API_KEY` and `OPENROUTER_API_KEY`. However, `llm_service.py` exclusively uses `OPENROUTER_API_KEY`. This is inconsistent and makes the new `LLM_API_KEY` setting useless. The goal of the refactor seems to be to generalize the LLM settings.
    *   **Fix:** The service should use the more generic `settings.LLM_API_KEY`.

    ```python
    # In app/services/llm_service.py, inside get_llm_reply()
    headers = {
        # CHANGE THIS
        "Authorization": f"Bearer {settings.LLM_API_KEY}", 
        "Content-Type": "application/json"
    }
    ```

2.  **`app/services/llm_service.py` - Hardcoded URL**
    *   **Problem:** The OpenRouter API URL is hardcoded. `app/config.py` provides `LLM_BASE_URL` for this purpose.
    *   **Fix:** Construct the full URL from the settings for better maintainability.

    ```python
    # In app/services/llm_service.py, inside get_llm_reply()
    # ...
    async with httpx.AsyncClient() as client:
        response = await client.post(
            # CHANGE THIS
            f"{settings.LLM_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30.0
        )
    ```

### PEP8/Style Issues

1.  **Move Imports to Top of File**
    *   **Problem:** In both `app/services/chat_service.py` and `app/services/llm_service.py`, there are `import` statements located inside functions (e.g., `from app.config import settings`, `import logging`).
    *   **Fix:** According to PEP8, all imports should be at the top of the module, just after the module docstring. Move these imports to the top level of their respective files. This improves readability and avoids re-importing on every function call.

## 🧪 Test Suggestions

### Manual Verification Guide

Here is a step-by-step guide to manually verify that the new System Prompt is working correctly.

**Prerequisites:**
*   You have a local Redis server running (e.g., via Docker).
*   The application dependencies are installed.
*   Your `.env` file is correctly configured with your API keys.

---

**Step 1: Run the Application**

1.  In your terminal, start the Akasa backend server:
    ```bash
    uvicorn app.main:app --reload
    ```
2.  In a separate terminal, use the local setup script to connect your bot to your running server (this requires `ngrok`):
    ```bash
    ./setup_local_bot.sh
    ```

**Step 2: Test the Bot's Persona**

1.  Open your Telegram app and go to the chat with your Akasa bot.
2.  Send the message: `Who are you?`

*   **Expected Result:** The bot should respond by identifying itself as "Akasa, an expert AI assistant specializing in software development...", consistent with the `SYSTEM_PROMPT` defined in `app/config.py`. The tone should be professional and direct.

**Step 3: Test the Coding Assistant Behavior**

1.  In the same Telegram chat, send a technical question that requires a code snippet, for example:
    ```
    Write a python function to add two numbers.
    ```

*   **Expected Result:** The bot should provide a concise answer that includes a correctly formatted Python code block (e.g., inside ```python ... ```), as instructed by the system prompt.

**Step 4: Verify Redis History (Crucial Step)**

1.  Check the terminal where you are running `uvicorn`. The application logs will show the incoming message and the `chat_id`. Note down your `chat_id` (it's a number).
2.  Open a new terminal and connect to your local Redis instance:
    ```bash
    redis-cli
    ```
3.  Inside the Redis CLI, use the `LRANGE` command to view the entire history for your `chat_id`. Replace `<YOUR_CHAT_ID>` with the number from the logs:
    ```
    LRANGE chat_history:<YOUR_CHAT_ID> 0 -1
    ```

*   **Expected Result:** You will see a list of JSON strings. **Crucially, this list must ONLY contain messages with `"role": "user"` and `"role": "assistant"`.** You should **NOT** see any entry with `"role": "system"`. This verifies that the system prompt is not being saved to the conversation history.

