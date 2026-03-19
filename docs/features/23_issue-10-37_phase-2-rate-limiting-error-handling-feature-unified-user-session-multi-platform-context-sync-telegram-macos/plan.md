# Implementation Plan: Unified User Session & Rate Limiting

> **Refers to**: [Spec Link](./spec.md)
> **Status**: Draft

## 1. Architecture & Design

### Component View
-   **Authentication Service (`AuthService`)**: New service responsible for generating login challenges, verifying tokens, and managing the `Unified User` identity linking Telegram `chat_id` with local CLI sessions.
-   **Rate Limiter (`RateLimiterService`)**: New service implementing a Token Bucket or Fixed Window algorithm via Redis to throttle excessive requests.
-   **User State API**: New REST endpoints to allow local clients (CLI) to sync state (e.g., Active Project) with the backend.
-   **Redis Service Enhancements**: Updated to support User ID mapping and store "Unified" state instead of just `chat_id`-based state.
-   **Global Exception Handler**: Centralized error handling logic to catch specific exceptions (LLM timeouts, API errors) and return user-friendly responses.

### Data Model Changes

**Redis Keys:**
-   `auth:challenge:{token}` -> `{"session_id": "...", "created_at": "..."}` (TTL: 5 min)
-   `user:map:telegram:{chat_id}` -> `{unified_user_id}`
-   `user:map:session:{session_id}` -> `{unified_user_id}`
-   `user:state:{unified_user_id}:project` -> `String` (Active Project)

**Pydantic Models (`app/models/auth.py`):**
```python
class LoginChallenge(BaseModel):
    token: str
    expires_in: int
    session_id: str

class UserState(BaseModel):
    unified_user_id: str
    active_project: str
    linked_accounts: dict  # e.g., {"telegram": 12345}
```

---

## 2. Step-by-Step Implementation

### Step 1: Redis Service Refactoring & User Mapping
Refactor `RedisService` to support the concept of a "Unified User". It must transparently handle the lookup from `chat_id` to `unified_user_id` to maintain backward compatibility while enabling the new feature.

-   **Docs**: Update `app/services/redis_service.py` docstrings.
-   **Code**: `app/services/redis_service.py`
    -   Add `get_unified_user_id(identifier: str/int) -> Optional[str]`.
    -   Modify `get_current_project` to first resolve the Unified ID. If found, use `user:state:{uid}:project`; else fallback to legacy `user_current_project:{chat_id}`.
    -   Add `link_user_identities(unified_id: str, telegram_id: int = None, session_id: str = None)`.
-   **Tests**: `tests/services/test_redis_service_unified.py` (New)
    -   Test linking identities.
    -   Test transparent fallback for legacy keys.

### Step 2: Authentication Service & Handshake
Implement the logic to generate a secure token and link the accounts when that token is received via Telegram.

-   **Code**: `app/services/auth_service.py` (New)
    -   `create_login_challenge() -> LoginChallenge`: Generates a random 8-char alphanumeric token and stores it in Redis with a Session ID.
    -   `verify_and_link_telegram(token: str, telegram_chat_id: int) -> bool`: Validates token, creates/retrieves `unified_user_id`, and creates the Redis mapping.
-   **Tests**: `tests/services/test_auth_service.py`
    -   Test token generation and expiration.
    -   Test successful linking flow.

### Step 3: API Endpoints for CLI
Create the HTTP endpoints that the local CLI will use to initiate login and sync state.

-   **Code**: `app/routers/auth.py` (New)
    -   `POST /api/v1/auth/challenge`: Returns a login token for the user to copy.
    -   `GET /api/v1/auth/session`: Checks if the current `session_id` (from header/cookie) is linked to a user.
-   **Code**: `app/routers/users.py` (New)
    -   `GET /api/v1/user/state`: Returns current context (Active Project).
    -   `PUT /api/v1/user/state`: Updates Active Project.
-   **Code**: `app/main.py`
    -   Register new routers.
-   **Tests**: `tests/routers/test_auth_routers.py`

### Step 4: Telegram Integration (Token Handling)
Modify the Chat Service to detect if a user sends a Login Token.

-   **Code**: `app/services/chat_service.py`
    -   In `handle_chat_message`: Check if message text matches the Token pattern (regex `^[A-Z0-9]{8}$`).
    -   If match: Call `AuthService.verify_and_link_telegram`.
    -   If success: Send "✅ Account Linked" message and stop processing (do not send to LLM).
-   **Tests**: `tests/services/test_chat_service_auth.py`
    -   Mock `AuthService` and verify `chat_service` delegates correctly.

### Step 5: Rate Limiting
Implement a Rate Limiter to protect the system.

-   **Code**: `app/services/rate_limiter.py` (New)
    -   `check_rate_limit(key: str, limit: int, window: int) -> bool`: Uses Redis `INCR` + `EXPIRE`.
-   **Code**: `app/services/chat_service.py`
    -   Integrate `check_rate_limit` at the start of `handle_chat_message`.
    -   If limited: Send "Too many messages" reply immediately and return.
-   **Tests**: `tests/services/test_rate_limiter.py`

### Step 6: Unified Error Handling
Ensure the bot fails gracefully with helpful messages.

-   **Code**: `app/exceptions.py`
    -   Define `RateLimitExceeded`, `LLMTimeoutError`, `ExternalAPIError`.
-   **Code**: `app/services/llm_service.py`
    -   Wrap external API calls in `try/except` blocks that translate vendor-specific errors (OpenAI/Anthropic) into internal `app/exceptions`.
-   **Code**: `app/main.py`
    -   Add `exception_handler` for these custom exceptions to return JSON responses (for API) or log errors.
    -   *Note*: For Telegram background tasks, exceptions don't bubble to `main.py` middleware. We must handle them inside `chat_service.py`'s `try/except` block to send a user-friendly Telegram message.
-   **Code**: `app/services/chat_service.py`
    -   Wrap the main processing logic. On `LLMTimeoutError`, send "Request timed out..." message.

---

## 3. Verification Plan

### Automated Tests
- [ ] **Unit Tests**:
    -   `test_redis_service_unified.py`: Verify User ID resolution and fallback.
    -   `test_auth_service.py`: Verify token lifecycle and linking.
    -   `test_rate_limiter.py`: Verify limits are enforced and reset.
- [ ] **Integration Tests**:
    -   `tests/integration/test_auth_flow.py`: Simulate the full flow:
        1. Call API to get Token.
        2. Call `handle_chat_message` with Token.
        3. Verify API `GET /state` returns the same User ID.
        4. Update Project via API, verify `get_current_project(chat_id)` returns new value.

### Manual Verification
- [ ] **Account Linking**: Run `curl` to get a token, send it to the Bot, verify success message.
- [ ] **Context Sync**: Change project via `curl` (simulating CLI), ask Bot "What project am I in?", verify answer.
- [ ] **Rate Limit**: Spam the bot with 10 messages in 5 seconds, verify the "Slow down" warning appears and subsequent messages are ignored.
- [ ] **Error Handling**: Temporarily break the LLM API key (or use a mock that timeouts), verify the Bot sends a "Sorry, something went wrong" message instead of crashing.