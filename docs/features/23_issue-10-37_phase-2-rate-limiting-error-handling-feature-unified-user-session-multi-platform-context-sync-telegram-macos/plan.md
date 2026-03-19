# Implementation Plan: Incremental Active Project Context Sync + Telegram Reliability

> Refers to: [spec.md](./spec.md)
> Status: Draft

## 1. Architecture and Design

### Component View

- **New context router:** add `GET/PUT /api/v1/context/project` for local tools.
- **Existing auth reuse:** use the existing `verify_api_key` dependency based on `X-Akasa-API-Key`; do not introduce bearer auth or login challenges in this phase.
- **Existing Redis project storage reuse:** keep Telegram and local tools on the same `user_current_project:{chat_id}` storage pattern.
- **New Telegram rate limiter:** add a focused inbound Telegram message rate limiter before command handling or LLM work.
- **LLM failure normalization:** make timeout, upstream failure, malformed response, and insufficient-credit outcomes explicit in the bot flow.

### Data Model Changes

**New request/response models**

```python
class ProjectContextResponse(BaseModel):
    active_project: str


class ProjectContextUpdateRequest(BaseModel):
    active_project: str
```

**New settings**

```python
TELEGRAM_MESSAGE_RATE_LIMIT: int = 5
TELEGRAM_MESSAGE_RATE_WINDOW_SECONDS: int = 60
```

**Redis behavior**

- Keep using `user_current_project:{chat_id}` as the v1 source of truth.
- The context sync API resolves the owner chat from `AKASA_CHAT_ID` and reads/writes that same key.
- No Redis migration is required in this phase.

## 2. Step-by-Step Implementation

### Step 1: Add the Context Sync API

- **Code:** add `app/routers/context.py`.
- **Behavior:** expose:
  - `GET /api/v1/context/project`
  - `PUT /api/v1/context/project`
- **Auth:** import and reuse the existing `verify_api_key` dependency; do not refactor auth in this phase.
- **Models:** add a small context request/response model file, such as `app/models/context.py`.
- **Redis integration:** add thin owner-context helpers around the existing project storage so the router reads and writes the configured owner chat's project.
- **Validation:** trim whitespace, reject empty values, and store normalized lowercase project names.
- **App wiring:** register the new router in `app/main.py`.
- **Tests:** add `tests/routers/test_context.py` for success, invalid API key, invalid payload, and misconfigured owner context.

### Step 2: Keep Telegram and Local Sync on the Same State

- **Code:** keep Telegram `/project` handling in `app/services/chat_service.py` as the Telegram-side write path.
- **Code:** keep project storage in `app/services/redis_service.py` as the shared v1 backing store.
- **Behavior:** ensure Telegram `/project` changes are visible to the sync API and sync API updates are visible to subsequent Telegram interactions.
- **Tests:** add Redis or service-level coverage proving:
  - Telegram-side writes are readable by the context API helpers.
  - Context API writes are visible through the existing Telegram project lookup path.

### Step 3: Add Telegram Inbound Message Rate Limiting

- **Code:** add `app/services/rate_limiter.py` with a simple Redis-backed fixed-window limiter using `INCR` plus `EXPIRE`.
- **Keying rule:** rate limit by Telegram `user_id` when available; fall back to `chat_id` if needed.
- **Chat integration:** call the limiter at the top of `handle_chat_message` before command dispatch and before normal LLM handling.
- **Blocked outcome:** send a short slow-down warning and return immediately without calling the LLM.
- **Scope:** do not change existing command-queue rate limiting in this phase.
- **Tests:** add:
  - `tests/services/test_rate_limiter.py`
  - targeted chat-service tests ensuring a blocked message never reaches LLM execution

### Step 4: Normalize LLM Error Handling

- **Code:** extend `app/exceptions.py` with explicit bot-facing error categories:
  - `LLMTimeoutError`
  - `LLMUpstreamError`
  - `LLMMalformedResponseError`
- **Code:** update `app/services/llm_service.py` to translate raw timeout, upstream, and malformed-response cases into those exceptions.
- **Credits case:** keep `OpenRouterInsufficientCreditsError` as a distinct user-facing path.
- **Chat integration:** update `app/services/chat_service.py` to map each failure category to a clear Telegram fallback message.
- **Tests:** add service-level tests covering timeout, upstream HTTP failure, malformed response, and insufficient credits.

### Step 5: Verification and Regression Coverage

- **Automated tests:**
  - context router success and failure paths,
  - shared project-state behavior between Telegram and the new sync API,
  - Telegram rate-limit enforcement before LLM execution,
  - LLM failure mapping to friendly Telegram outcomes.
- **Manual verification:**
  1. Set project from Telegram and verify `GET /api/v1/context/project`.
  2. Set project from `PUT /api/v1/context/project` and verify Telegram `/project`.
  3. Exceed the Telegram message limit and verify the blocked message does not call the LLM.
  4. Simulate an LLM timeout or upstream error and verify a friendly fallback response.

## 3. Verification Plan

### Automated Tests

- [ ] `tests/routers/test_context.py`
- [ ] `tests/services/test_rate_limiter.py`
- [ ] chat-service tests for rate-limit short-circuit behavior
- [ ] llm-service and chat-service tests for timeout, upstream failure, malformed response, and insufficient-credit handling

### Manual Verification

- [ ] `GET /api/v1/context/project` returns `default` before any explicit change.
- [ ] `PUT /api/v1/context/project` with a valid API key updates the owner chat's shared project.
- [ ] Telegram `/project select akasa` is visible to the local sync API.
- [ ] Telegram spam beyond the configured limit returns a slow-down warning.
- [ ] LLM failure paths return friendly user-facing fallbacks instead of raw errors.

## 4. Explicit Non-Goals for This Plan

- No login challenge implementation.
- No bearer-token auth.
- No multi-user routing.
- No persistent `Unified User ID` storage model.
- No synchronization of model preference, history, or agent state in this phase.
