# SBE: Incremental Active Project Context Sync + Telegram Reliability

> Created: 2026-03-19
> Issues: [#10](https://github.com/oatrice/Akasa/issues/10), [#37](https://github.com/oatrice/Akasa/issues/37)

## Feature

This feature synchronizes the owner's `active_project` between Telegram and authenticated local tools while also protecting Telegram interactions with inbound message rate limiting and friendly LLM failure handling.

### Scenario: Telegram updates the project and local tools read the same value

**Given** the owner chat configured by `AKASA_CHAT_ID` currently has `active_project` set to `<before_project>`

**When** the Telegram user sends `<telegram_command>`

**Then** the shared project state is updated to `<after_project>`

**And** `GET /api/v1/context/project` with a valid `X-Akasa-API-Key` returns `{"active_project": "<after_project>"}`.

#### Examples

| before_project | telegram_command | after_project |
|----------------|------------------|---------------|
| default | `/project select akasa` | akasa |
| akasa | `/project select release-notes` | release-notes |
| default | `/project new docs-bot` | docs-bot |

### Scenario: Local tools update the project and Telegram uses the same value

**Given** the local tool is authenticated with a valid `X-Akasa-API-Key`

**And** the owner chat currently has `active_project` set to `<before_project>`

**When** the local tool calls `PUT /api/v1/context/project` with `{"active_project": "<requested_project>"}`

**Then** the API responds with `{"active_project": "<stored_project>"}`

**And** the next Telegram interaction resolves `<stored_project>` as the current project.

#### Examples

| before_project | requested_project | stored_project |
|----------------|-------------------|----------------|
| default | Akasa | akasa |
| akasa | release-notes | release-notes |
| docs-bot |  Docs-Bot  | docs-bot |

### Scenario: Invalid API key is rejected by the context sync API

**Given** the context sync API requires `X-Akasa-API-Key`

**When** a client requests `<method> /api/v1/context/project` with header `<header_value>`

**Then** the API returns status `<status>`

**And** the shared `active_project` remains unchanged.

#### Examples

| method | header_value | status |
|--------|--------------|--------|
| GET | missing | 401 |
| GET | `wrong-key` | 401 |
| PUT | missing | 401 |
| PUT | `expired-or-unknown-key` | 401 |

### Scenario: Telegram inbound rate limit blocks excess messages

**Given** the Telegram inbound rate limit is `<limit>` messages per `<window_seconds>` seconds

**And** the same Telegram user has already sent `<already_sent>` messages inside the current window

**When** the user sends one more message

**Then** the system responds with `<result>`

**And** the blocked message does not call the LLM when the limit is exceeded.

#### Examples

| limit | window_seconds | already_sent | result |
|-------|----------------|--------------|--------|
| 5 | 60 | 4 | message is processed normally |
| 5 | 60 | 5 | user receives a slow-down warning |
| 10 | 60 | 10 | user receives a slow-down warning |

### Scenario: LLM failures return friendly fallback outcomes

**Given** the current `active_project` is `akasa`

**When** the user sends a valid Telegram message that requires LLM processing and the provider failure is `<failure_type>`

**Then** the bot returns `<user_visible_outcome>`

**And** the conversation does not fail silently.

#### Examples

| failure_type | user_visible_outcome |
|--------------|----------------------|
| request timeout | friendly timeout message with retry guidance |
| upstream 502 or 503 | friendly temporary-failure message |
| malformed provider response | friendly processing-error message |
| insufficient OpenRouter credits | friendly configuration or credits guidance |
