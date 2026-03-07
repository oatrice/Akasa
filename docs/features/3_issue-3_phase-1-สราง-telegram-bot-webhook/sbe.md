# SBE: Telegram Webhook Integration

> 📅 Created: 2026-03-07
> 🔗 Issue: [#3](https://github.com/oatrice/Akasa/issues/3)

---

## Feature: Telegram Webhook Receiver

This feature enables the backend to receive real-time updates from the Telegram Bot API via a webhook. It involves creating a secure endpoint that validates incoming requests using a secret token and successfully acknowledges receipt of valid messages from Telegram.

### Scenario: Successful Message Receipt (Happy Path)

**Given** the backend service is running with a configured `WEBHOOK_SECRET_TOKEN`
**When** a `POST` request is sent to `/api/v1/telegram/webhook` with a valid `X-Telegram-Bot-Api-Secret-Token` header
**Then** the service must respond with an `HTTP 200 OK` status and an empty body

#### Examples

| `X-Telegram-Bot-Api-Secret-Token` | `request_body` | `expected_status` |
|---|---|---|
| `a_very_secret_string_123` | `{"update_id": 1, "message": {"text": "hello"}}` | 200 |
| `a_very_secret_string_123` | `{"update_id": 2, "message": {"text": "/start"}}` | 200 |
| `a_very_secret_string_123` | `{"update_id": 3, "edited_message": {"text": "Hi"}}` | 200 |
| `another-valid-token-!@#` | `{"update_id": 4, "message": {"text": "help"}}` | 200 |

### Scenario: Error Handling - Invalid or Missing Secret Token

**Given** the backend service is running
**When** a `POST` request is sent to `/api/v1/telegram/webhook` with an invalid or missing `X-Telegram-Bot-Api-Secret-Token` header
**Then** the service must respond with an `HTTP 403 Forbidden` error to prevent unauthorized access

#### Examples

| `X-Telegram-Bot-Api-Secret-Token` | `expected_status` | `expected_error_detail` |
|---|---|---|
| `this_is_a_wrong_token` | 403 | "Invalid secret token" |
| ` ` (empty string) | 403 | "Invalid secret token" |
| `null` (header is missing) | 403 | "Secret token missing" |
| `a_very_secret_string_1234` (typo) | 403 | "Invalid secret token" |

### Scenario: Edge Case - Unsupported HTTP Method

**Given** the backend service is running and the `/api/v1/telegram/webhook` endpoint exists
**When** a client sends a request to the endpoint using any method other than `POST`
**Then** the service must respond with an `HTTP 405 Method Not Allowed` error

#### Examples

| `request_method` | `endpoint` | `expected_status` | `expected_error_detail` |
|---|---|---|---|
| `GET` | `/api/v1/telegram/webhook` | 405 | "Method Not Allowed" |
| `PUT` | `/api/v1/telegram/webhook` | 405 | "Method Not Allowed" |
| `DELETE`| `/api/v1/telegram/webhook` | 405 | "Method Not Allowed" |
| `PATCH` | `/api/v1/telegram/webhook` | 405 | "Method Not Allowed" |