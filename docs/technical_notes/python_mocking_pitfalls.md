# Python Mocking Pitfalls: Lessons Learned from Issue #30

This document summarizes the key challenges and solutions discovered while debugging a persistent `AssertionError: Expected 'mock' to be called once. Called 0 times.` in a `pytest` environment with `asyncio` and `unittest.mock`.

## Problem 1: Silent `TypeError` from `await` on a Synchronous Mock

### Symptom

A test asserting a mock was called fails with "Called 0 times", but there is no obvious error in the application logic.

### Root Cause

- The application code wraps a service call in a broad `try...except Exception`.
- The test uses `@patch` which, by default, creates a synchronous `MagicMock`.
- When the application code tries to `await` a method on this synchronous mock (e.g., `await redis_service.set_user_chat_id_mapping(...)`), it raises a `TypeError`.
- This `TypeError` is silently caught by the `except` block, preventing the mock from ever being successfully called, but allowing the test to continue to the assertion, which then fails.

### Solution

Always ensure mocks for `async` functions are also `async`. Use `new_callable=AsyncMock` when patching.

**Incorrect:** `@patch("app.services.chat_service.redis_service")`
**Correct:** `@patch("app.services.chat_service.redis_service.some_async_function", new_callable=AsyncMock)`

## Problem 2: Pydantic Model Initialization with Aliases

### Symptom

An `if` condition like `if update.message.from_user:` evaluates to `False` even though the test data seems to provide the `from_user` object.

### Root Cause

- A Pydantic model uses an `alias` for a field (e.g., `from_user: Optional[TelegramUser] = Field(None, alias="from")`).
- The test was creating the model instance directly using keyword arguments (`Message(from_user=...)`) instead of parsing a dictionary.
- Direct initialization does not respect the `alias`. To populate a field with an alias, you must parse a dictionary that uses the aliased key (e.g., `{"from": ...}`).

### Solution

Create test data using a dictionary and parse it with `.parse_obj()` (or `.model_validate()` in Pydantic v2+).

**Incorrect:** `Message(from_user=TelegramUser(...))`
**Correct:** 
```python
data = {"from": {"id": 123, ...}}
message = Message.parse_obj(data)
# Now message.from_user will be correctly populated.
```

## Problem 3: Naming Collision with Singleton Instances (`module` vs. `instance`)

### Symptom

An `AttributeError: <module '...' has no attribute '...'>` occurs when trying to mock a method on a service instance, especially when the module (`.py` file) and the singleton instance variable share the same name.

### Root Cause

- A file like `my_service.py` contains `my_service = MyService()`.
- Another file imports it via `from services import my_service`.
- `unittest.mock.patch` gets confused whether `my_service` refers to the module or the instance within it.

### Solution: Be Specific and Unambiguous

**1. Rename the Singleton (Best for Prevention):**
   - In `my_service.py`, rename the instance to `my_svc = MyService()`. This eliminates the ambiguity entirely.

**2. Patch the Class Method (Most Robust):**
   - Instead of patching the instance, patch the method on the class definition itself. This works for all instances of the class.
   - `from app.services.telegram_service import TelegramService`
   - `@patch.object(TelegramService, "send_message", ...)`

**3. Patch "Where It's Used" (The Golden Rule):**
   - If `chat_service.py` imports and uses `redis_service`, the correct string path for the patch is where the name is looked up: `"app.services.chat_service.redis_service.set_user_chat_id_mapping"`. This ensures you are patching the name in the correct namespace.
