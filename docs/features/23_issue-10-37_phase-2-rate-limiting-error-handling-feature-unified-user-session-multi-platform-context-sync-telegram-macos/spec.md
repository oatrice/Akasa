# Specification

**Title:** [Phase 2] Rate Limiting & Error Handling + Incremental Active Project Context Sync (Telegram + macOS)

**Version:** 1.1
**Status:** Draft

## 1. Executive Summary

This phase improves Akasa in two practical ways:
1. It makes Telegram interactions more reliable by adding inbound message rate limiting and clearer LLM failure handling.
2. It lets Telegram and local macOS tools share the same `active_project` value so the user can switch context once and continue from either side.

This v1 is intentionally incremental. It reuses the repo's existing `X-Akasa-API-Key` pattern and the current chat-based Redis storage model. Full account linking, bearer-token auth, and multi-user unified identity are explicitly deferred to a later phase.

## 2. V1 Product Contract

### 2.1 Core Behaviors

- Local tools can read the current project via `GET /api/v1/context/project`.
- Local tools can update the current project via `PUT /api/v1/context/project`.
- Both endpoints require `X-Akasa-API-Key`.
- The only synchronized field in v1 is `active_project`.
- Telegram `/project` commands and the local sync API must read and write the same underlying project state.
- Inbound Telegram messages are rate limited before command handling or LLM processing.
- LLM failures must produce user-friendly fallback messages instead of silent failure or raw stack traces.

### 2.2 V1 Assumptions

- V1 is single-user in practice.
- The canonical synced Telegram chat is the owner chat configured by `AKASA_CHAT_ID`.
- The sync API does not accept `chat_id`, `user_id`, or session identifiers in the request body.
- Project names are treated as case-insensitive and are stored in normalized lowercase form to stay aligned with current Telegram `/project` behavior.

### 2.3 Non-Goals

- No login challenge flow.
- No `AuthService` or `session_id` handshake in v1.
- No bearer-token auth.
- No `Unified User ID` persistence model in v1.
- No synchronization of model preference, chat history, agent state, or linked-account metadata.
- No multi-user routing between multiple Telegram accounts and multiple local profiles.

## 3. User Journey

1. The owner uses Akasa in Telegram and currently works in project `default`.
2. From Telegram, the owner sends `/project select akasa`.
3. Akasa updates the current project in Redis.
4. A local tool authenticated with `X-Akasa-API-Key` calls `GET /api/v1/context/project` and receives `{"active_project": "akasa"}`.
5. Later, the local tool calls `PUT /api/v1/context/project` with `{"active_project": "release-notes"}`.
6. The next Telegram interaction resolves the same `active_project` value and behaves as if the user had switched project from Telegram.
7. If the owner sends too many Telegram messages too quickly, Akasa warns the user and skips LLM processing for the blocked message.
8. If the LLM times out or returns an invalid upstream response, Akasa replies with a friendly error message and keeps the conversation usable.

## 4. Functional Requirements

### 4.1 Cross-Platform Active Project Sync

- **R1.1:** The backend must expose `GET /api/v1/context/project` for local tools to read the current `active_project`.
- **R1.2:** The backend must expose `PUT /api/v1/context/project` for local tools to update the current `active_project`.
- **R1.3:** Both endpoints must require `X-Akasa-API-Key`.
- **R1.4:** In v1, the sync API must operate on the owner chat configured by `AKASA_CHAT_ID`.
- **R1.5:** Telegram project changes and local API updates must use the same Redis-backed project state.
- **R1.6:** `active_project` must be normalized to lowercase before storage.

### 4.2 Telegram Context Usage

- **R2.1:** Telegram `/project` commands must keep updating the shared `active_project`.
- **R2.2:** Standard Telegram messages must resolve the current `active_project` before building LLM context.
- **R2.3:** After a local `PUT /api/v1/context/project`, the next Telegram interaction must observe the updated project without additional linking steps.

### 4.3 Telegram Message Rate Limiting

- **R3.1:** The system must enforce a configurable rate limit on inbound Telegram messages.
- **R3.2:** The rate limit check must happen before command handling and before any LLM request.
- **R3.3:** When the limit is exceeded, Akasa must return a user-friendly warning and skip LLM processing for that message.
- **R3.4:** Existing command-queue rate limiting remains separate and is not replaced by this feature.

### 4.4 LLM Error Handling

- **R4.1:** LLM timeout failures must return a user-friendly timeout message.
- **R4.2:** Upstream API failures must return a user-friendly temporary failure message.
- **R4.3:** Malformed or unusable LLM responses must return a user-friendly processing error message.
- **R4.4:** Insufficient-credit failures must return a user-friendly configuration/payment guidance message.
- **R4.5:** The bot must not expose raw exception traces to Telegram users.

## 5. API Contract

### 5.1 GET `/api/v1/context/project`

**Headers**

```http
X-Akasa-API-Key: <server-or-redis-backed-api-key>
```

**Success Response**

```json
{
  "active_project": "akasa"
}
```

**Notes**

- If no project has been set yet, the endpoint returns `default`.
- The endpoint resolves the project for the configured owner chat, not for a caller-supplied user identifier.

**Error Responses**

| Status | Meaning |
|--------|---------|
| 401 | Missing or invalid `X-Akasa-API-Key` |
| 503 | Context sync is not configured correctly on the server (for example, missing canonical owner chat configuration) |

### 5.2 PUT `/api/v1/context/project`

**Headers**

```http
X-Akasa-API-Key: <server-or-redis-backed-api-key>
Content-Type: application/json
```

**Request Body**

```json
{
  "active_project": "release-notes"
}
```

**Success Response**

```json
{
  "active_project": "release-notes"
}
```

**Rules**

- `active_project` must be a non-empty string.
- Leading and trailing whitespace is ignored.
- The stored value is normalized to lowercase.

**Error Responses**

| Status | Meaning |
|--------|---------|
| 401 | Missing or invalid `X-Akasa-API-Key` |
| 422 | Invalid request body, including missing or empty `active_project` |
| 503 | Context sync is not configured correctly on the server |

## 6. Telegram Reliability Contract

### 6.1 Rate Limit Outcome

When the inbound Telegram message limit is exceeded:
- the message is not sent to the LLM,
- the conversation remains intact,
- and the user receives a short warning telling them to slow down and retry later.

### 6.2 LLM Failure Outcome

When LLM processing fails, the user must receive a friendly fallback outcome in one of these categories:
- timeout,
- temporary upstream failure,
- malformed response,
- insufficient credits or invalid provider configuration.

The exact wording may vary, but the message must clearly tell the user what happened and whether retrying later is appropriate.

## 7. Future Evolution

The following items are intentionally deferred and must not be treated as v1 acceptance criteria:

- full `Unified User ID` across Telegram account and local profile,
- login challenge or one-time linking token,
- bearer-token auth for local clients,
- multi-user local-tool routing,
- synchronization of state beyond `active_project`.

These remain valid future directions once the repo moves beyond the current single-owner, API-key-based operating model.
