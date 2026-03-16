# Python Mocking Pitfalls: Lessons Learned

This document summarizes the key challenges and solutions discovered while writing tests for Akasa — covering `asyncio`, `unittest.mock`, `httpx`, and FastAPI lifespan interactions.

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

---

## Problem 4: `raise_for_status()` is Synchronous — `AsyncMock` Silently Does Nothing

*Discovered while writing tests for `TelegramService.send_deployment_notification` (Issue #33/34)*

### Symptom

Tests that are supposed to verify HTTP error propagation (`pytest.raises(httpx.HTTPStatusError)`) fail with `Failed: DID NOT RAISE`. At the same time, happy-path tests emit a `RuntimeWarning: coroutine 'AsyncMockMixin._execute_mock_call' was never awaited`.

### Root Cause

`httpx.Response.raise_for_status()` is a **synchronous** method — it is called without `await` in the service code:

```python
response = await self.client.post(...)
response.raise_for_status()   # ← sync call, no await
```

However, the test mock configured `raise_for_status` as an `AsyncMock`:

```python
mock_response = AsyncMock()
mock_response.raise_for_status = AsyncMock(side_effect=httpx.HTTPStatusError(...))
mock_post.return_value = mock_response
```

When `response.raise_for_status()` is called **without** `await`, calling an `AsyncMock` returns a coroutine object — it does **not** execute the function body or raise the `side_effect`. The coroutine is then immediately garbage-collected, producing the `RuntimeWarning`.

### Solution

Use `MagicMock` (synchronous) for the response object and `raise_for_status`. Reserve `AsyncMock` only for the `post()` call itself, since that is what gets `await`-ed.

**Incorrect (silent failure):**
```python
mock_response = AsyncMock()
mock_response.raise_for_status = AsyncMock(side_effect=httpx.HTTPStatusError(...))
mock_post.return_value = mock_response
```

**Correct:**
```python
mock_response = MagicMock()                          # sync mock for the response object
mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
    "Bad Request",
    request=MagicMock(),
    response=httpx.Response(400, json={"ok": False}),
)
mock_post.return_value = mock_response               # post() is AsyncMock, response is MagicMock
```

**Happy-path mock (no raise needed):**
```python
mock_response = MagicMock()          # raise_for_status() will be a no-op MagicMock by default
mock_post.return_value = mock_response
```

### Rule of Thumb

> Match the mock type to how the code **calls** the method:
> - `await some_method()` → use `AsyncMock`
> - `some_method()` (no await) → use `MagicMock`

httpx's `raise_for_status`, `json()`, `text`, and `.status_code` are all synchronous — always use `MagicMock` for the response object.

---

## Problem 5: Singleton `httpx.AsyncClient` Closed by FastAPI Lifespan

*Discovered when `test_send_confirmation_message_with_keyboard` failed in CI with `RuntimeError: Cannot send a request, as the client has been closed.` but passed locally in isolation*

### Symptom

A test using `respx.mock` (or any test that touches `tg_service` directly) passes when run alone but fails in the full test suite with:

```
RuntimeError: Cannot send a request, as the client has been closed.
```

The error is non-deterministic — it depends on test execution order.

### Root Cause

`TelegramService` holds a single `httpx.AsyncClient` instance as a class attribute (`self.client`), shared across the entire process lifetime.

`app/main.py` defines a FastAPI lifespan that **closes** this client on app shutdown:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await tg_service.client.aclose()   # ← closes the singleton
```

Tests that instantiate `TestClient(app)` trigger the full FastAPI lifespan. When the `with TestClient(app) as c:` block exits, the app shuts down — and `tg_service.client` is closed permanently. Any subsequent test in the same pytest session that uses `tg_service` (even with `respx.mock`) then hits a closed client.

### Solution: `autouse` Fixture in `conftest.py`

Add a session-level autouse fixture that detects a closed client and replaces it with a fresh `httpx.AsyncClient` before each test:

```python
# conftest.py
import httpx
import pytest

@pytest.fixture(autouse=True)
def ensure_tg_client_open():
    """
    Reopen tg_service.client before each test if it was closed by a
    previous test's TestClient lifespan shutdown.
    """
    from app.services.telegram_service import tg_service

    if tg_service.client.is_closed:
        tg_service.client = httpx.AsyncClient()

    yield
```

This makes test order irrelevant — each test always starts with an open client, regardless of what previous tests did.

### Why Not Fix the Lifespan?

The lifespan close is correct behaviour for production: the `AsyncClient` should be gracefully shut down when the app stops. The issue is purely a test isolation concern. The fixture is the least invasive fix.

### General Pattern

Any singleton that holds a closeable resource (database connection pool, HTTP client, Redis connection) and is closed by a lifespan event will have this problem. The standard mitigation is an `autouse` fixture that resets the resource to a usable state before each test.
