# Implementation Plan: Proactive Messaging in TelegramService

> **Refers to**: [Spec Link](./spec.md)
> **Status**: Draft

## 1. Architecture & Design
*High-level technical approach.*

The implementation will introduce a new public method, `send_proactive_message`, to the existing `TelegramService`. This method will orchestrate the process of retrieving a user's `chat_id` from Redis via the `RedisService` and then using the existing `httpx`-based functionality within `TelegramService` to send the message.

Error handling will be managed within `send_proactive_message` to gracefully handle cases like a missing user in Redis or a blocked bot reported by the Telegram API. The function will return a boolean to indicate success or failure.

### Component View
- **Modified Components**:
    - `app/services/telegram_service.py`: To add the new `send_proactive_message` method and its core logic.
    - `app/services/redis_service.py`: To add a new method for retrieving a `chat_id` based on a `user_id`.
- **New Components**: None.
- **Dependencies**: No new external libraries are required. The implementation will use the existing `redis` and `httpx` libraries.

### Data Model Changes
No changes to the database schema or Pydantic models are required. However, this implementation relies on a specific key-value structure in Redis, which needs to be handled consistently.

**Redis Key-Value Assumption:**
- A mechanism (outside the scope of this task) is responsible for storing a mapping from a user's Telegram ID to their chat ID.
- This plan will implement the retrieval part, assuming the following structure:
  - **Key**: `user_chat_id:{user_id}`
  - **Value**: `{chat_id}`

---

## 2. Step-by-Step Implementation

### Step 1: Add `chat_id` Lookup Logic to RedisService
- **Description**: Create a dedicated function in `RedisService` to abstract the logic of finding a `chat_id` for a given `user_id`. This centralizes the key management.
- **Files to Modify**: `app/services/redis_service.py`
- **Code**:
  - Add a new `async` method: `get_chat_id_for_user(user_id: str) -> Optional[str]`.
  - Inside the method, construct the Redis key (e.g., `f"user_chat_id:{user_id}"`).
  - Use `redis_pool.get(key)` to retrieve the `chat_id`.
  - Return the `chat_id` if found, otherwise return `None`.
- **Tests**:
  - **File**: `tests/services/test_redis_service.py`
  - Add a new unit test to verify that `get_chat_id_for_user` correctly returns a stored `chat_id` and returns `None` for a non-existent `user_id`.

### Step 2: Implement `send_proactive_message` in TelegramService
- **Description**: Create the main public method in `TelegramService` that orchestrates the entire process.
- **Files to Modify**: `app/services/telegram_service.py`
- **Code**:
  - Define the new public method: `async def send_proactive_message(self, user_id: str, text: str) -> bool:`.
  - Call `redis_service.get_chat_id_for_user(user_id)` to get the `chat_id`.
  - **User Not Found Handling**: If `chat_id` is `None`, log a warning (`logger.warning(f"Chat ID not found for user_id: {user_id}")`) and `return False`.
  - **Success Path**: If `chat_id` is found, proceed to call the existing `self.send_message(chat_id=chat_id, text=text)` method.

### Step 3: Integrate Robust Error Handling
- **Description**: Wrap the core message-sending logic in a `try...except` block to handle API errors, specifically for cases where the bot is blocked.
- **Files to Modify**: `app/services/telegram_service.py`
- **Code**:
  - Surround the `self.send_message` call with a `try...except httpx.HTTPStatusError as e:`.
  - Inside the `except` block, check if `e.response.status_code == 403`.
  - If it is 403, log a specific warning: `logger.warning(f"Failed to send to user_id {user_id}: Bot was blocked.")`.
  - In all exception cases, `return False`.
  - If the `send_message` call succeeds, `return True`.
- **Tests**:
  - **File**: `tests/services/test_telegram_service.py`
  - Add new unit tests for `send_proactive_message`:
    1.  **Happy Path**: Mock `redis_service` to return a `chat_id` and verify `send_message` is called correctly.
    2.  **User Not Found**: Mock `redis_service` to return `None` and assert the method returns `False` and `send_message` is not called.
    3.  **Bot Blocked**: Mock `redis_service` to return a `chat_id`, but make the `send_message` mock raise an `httpx.HTTPStatusError` with a 403 status. Assert the method returns `False` and logs the correct warning.

---

## 3. Verification Plan
*How will we verify success?*

### Automated Tests
- [ ] **Redis Service**: Add unit tests to `tests/services/test_redis_service.py` for the new `get_chat_id_for_user` function.
- [ ] **Telegram Service**: Add comprehensive unit tests to `tests/services/test_telegram_service.py` covering the success, user-not-found, and bot-blocked scenarios for `send_proactive_message`.

### Manual Verification
To facilitate manual testing, a temporary debug endpoint could be added.

- [ ] **Setup**: Add a temporary route (e.g., `/debug/send/{user_id}`) to the FastAPI app that calls `telegram_service.send_proactive_message`.
- [ ] **Step 1 (Happy Path)**:
    - Send a message to the bot to ensure your `user_id` and `chat_id` are stored in Redis.
    - Call the debug endpoint with your correct `user_id`.
    - **Expected**: You receive the test message in your Telegram client.
- [ ] **Step 2 (User Not Found)**:
    - Call the debug endpoint with a random, non-existent `user_id` (e.g., `"123"`).
    - **Expected**: You receive no message. The application logs show a "Chat ID not found" warning.
- [ ] **Step 3 (Bot Blocked)**:
    - In Telegram, block the bot.
    - Call the debug endpoint again with your correct `user_id`.
    - **Expected**: You receive no message. The application logs show a "Bot was blocked" warning.