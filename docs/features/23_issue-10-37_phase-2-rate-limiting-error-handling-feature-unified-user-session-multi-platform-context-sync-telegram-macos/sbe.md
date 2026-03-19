# SBE: Unified User Session & Rate Limiting System

> 📅 Created: 2026-03-19
> 🔗 Issue: https://github.com/oatrice/Akasa/issues/10

---

## Feature: Unified User Session & Robust Messaging

This feature implements a unified identity system allowing users to synchronize their "Active Project" context between Telegram and local macOS tools (CLI/IDE). Simultaneously, it introduces rate limiting to prevent abuse and robust error handling for external LLM service failures.

### Scenario: Sync Active Project Across Platforms (Happy Path)

**Given** a unified user account linking Telegram ID `<telegram_id>` and Local API Key `<api_key>`
**And** the current active project is `<initial_project>`
**When** the user sends a command to switch the project to `<new_project>` via `<source_platform>`
**Then** the global session state in Redis is updated to `<new_project>`
**And** querying the active project from `<target_platform>` returns `<new_project>`

#### Examples

| telegram_id | api_key | initial_project | new_project | source_platform | target_platform | expected_state |
|-------------|---------|-----------------|-------------|-----------------|-----------------|----------------|
| 987654321 | ak_dev_01 | Akasa | ProjectOmega | Telegram | CLI/IDE | ProjectOmega |
| 987654321 | ak_dev_01 | ProjectOmega | Phoenix | CLI/IDE | Telegram | Phoenix |
| 112233445 | ak_dev_02 | None | WebsiteV2 | Telegram | CLI/IDE | WebsiteV2 |

### Scenario: API Rate Limiting (Edge Case)

**Given** the global rate limit is set to `<limit>` requests per minute per user
**And** the user has already made `<previous_count>` requests in the last 59 seconds
**When** the user attempts to send `<new_requests>` additional requests
**Then** the system accepts the first `<accepted>` requests
**And** rejects the remaining `<rejected>` requests with a `<status_code>` or warning message

#### Examples

| limit | previous_count | new_requests | accepted | rejected | status_code |
|-------|----------------|--------------|----------|----------|-------------|
| 10 | 0 | 5 | 5 | 0 | 200 OK |
| 10 | 8 | 3 | 2 | 1 | 429 Too Many Requests |
| 5 | 5 | 1 | 0 | 1 | 429 Too Many Requests |
| 20 | 19 | 5 | 1 | 4 | 429 Too Many Requests |

### Scenario: LLM Service Error Handling (Error Handling)

**Given** the external LLM provider is responding with `<upstream_error>`
**When** a user sends a valid prompt requiring LLM generation
**Then** the system attempts to retry `<retry_attempts>` times
**And** finally responds to the user with `<user_message>`

#### Examples

| upstream_error | retry_attempts | user_message |
|----------------|----------------|--------------|
| 503 Service Unavailable | 3 | "LLM service is currently overloaded. Please try again later." |
| 500 Internal Server Error | 3 | "An unexpected error occurred with the AI provider." |
| 429 Too Many Requests (OpenAI) | 3 | "Rate limit exceeded with AI provider. Slowing down..." |
| 401 Unauthorized | 0 | "System configuration error: Invalid LLM credentials." |

### Scenario: Invalid Authentication for Sync API (Error Handling)

**Given** the Sync API requires a valid `X-API-Key` header
**When** a client requests `GET /sync/state` with header `<header_value>`
**Then** the API returns status `<status>` and message `<message>`

#### Examples

| header_value | status | message |
|--------------|--------|---------|
| missing | 401 | "Missing API Key" |
| "Bearer invalid_token" | 401 | "Invalid API Key format" |
| "ak_unknown_key" | 403 | "Access Forbidden: Invalid Key" |
| "ak_dev_01" | 200 | "success" |