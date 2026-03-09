# Specification: Implement Secure Proactive Notification Endpoint

## 1. Overview
This document specifies the requirements for a new secure API endpoint that allows external systems to send proactive notifications to Akasa users via Telegram. The endpoint will validate incoming requests based on an API key and forward the notification message, along with associated metadata and priority, to the `TelegramService` for immediate delivery.

## 2. User Goal
External systems (e.g., Gemini CLI, CI/CD pipelines) need a reliable and secure way to trigger notifications to specific Akasa users through the Telegram messaging platform, enabling timely alerts and updates without direct user initiation.

## 3. User Journey (External System Perspective)
1.  An external system obtains a valid `X-Akasa-API-Key`.
2.  The system prepares a notification payload including `user_id`, `message`, `priority`, and optional `metadata`.
3.  The system sends a `POST` request to the `/api/v1/notifications/send` endpoint, including the API key in the `X-Akasa-API-Key` header and the JSON payload in the request body.
4.  The system receives an HTTP response indicating success or detailing the reason for failure (e.g., authentication error, invalid data).

## 4. Functional Requirements

### FR1: Endpoint Definition
- A new API endpoint `POST /api/v1/notifications/send` will be created.
- This endpoint will be defined in `app/routers/notifications.py`.

### FR2: Request Authentication
- Incoming requests must include an `X-Akasa-API-Key` header.
- The value of this header will be validated against a stored API key. The API key will be retrieved from environment variables or Redis.
- Requests with an invalid, missing, or expired API key must be rejected with an appropriate HTTP status code (e.g., 401 Unauthorized).

### FR3: Request Payload Validation
- The endpoint must accept a JSON payload with the following structure:
    - `user_id` (string, required): The Telegram user identifier to send the notification to.
    - `message` (string, required): The content of the notification message.
    - `priority` (string, optional, enum: "high" | "normal"): Indicates the urgency of the notification. Defaults to "normal" if not provided.
    - `metadata` (object, optional): Additional key-value pairs for context or further processing.
- Requests with missing required fields or incorrect data types must be rejected with an appropriate HTTP status code (e.g., 400 Bad Request).

### FR4: Notification Sending Logic
- Upon successful authentication and payload validation, the endpoint must call the `TelegramService.send_proactive_message` method.
- The `user_id` from the payload will be passed to `send_proactive_message`.
- The `message` from the payload will be passed to `send_proactive_message`.
- The `priority` and `metadata` will be passed to `send_proactive_message` (or used for logging/internal handling if `send_proactive_message` doesn't directly accept them).

### FR5: Response Handling
- **Success**: If the notification is successfully handed off to `TelegramService`, the endpoint should return an HTTP 200 OK response with a confirmation message (e.g., `{"status": "success", "message": "Notification queued for delivery."}`).
- **Authentication Failure**: If the `X-Akasa-API-Key` is invalid, return HTTP 401 Unauthorized.
- **Bad Request**: If the payload is invalid, return HTTP 400 Bad Request with details about the validation error.
- **Internal Errors**: If `TelegramService` raises an exception (e.g., `UserChatIdNotFoundException`, `BotBlockedException`), the endpoint should catch it and return an appropriate HTTP error response (e.g., 400 Bad Request or 500 Internal Server Error, depending on the nature of the error and how it should be surfaced externally).

## 5. Non-Functional Requirements

### NFR1: Security
- The API key validation mechanism must be robust and prevent unauthorized access.
- Sensitive information (API keys) should be stored securely (e.g., in environment variables or encrypted in Redis).

### NFR2: Reliability
- The endpoint should return consistent and informative error messages.
- Logging should be implemented to track incoming requests, authentication results, and errors.

## 6. Specification by Example (SBE)

### Scenario 1: Successful Notification Send

**Given** a valid `X-Akasa-API-Key` is provided in the request header.
**And** the request payload contains valid `user_id`, `message`, `priority`, and `metadata`.
**When** a `POST` request is sent to `/api/v1/notifications/send`.
**Then** the API key is validated successfully.
**And** the payload is parsed and validated.
**And** `TelegramService.send_proactive_message` is called with the correct parameters.
**And** the endpoint returns a `200 OK` response with a success message.

#### Examples

| `X-Akasa-API-Key` Header | `user_id` (Payload) | `message` (Payload) | `priority` (Payload) | `metadata` (Payload) | Expected API Response Body |
|---|---|---|---|---|---|
| `valid-api-key-123` | `"123456789"` | `"System maintenance scheduled"` | `"high"` | `{"maintenance_window": "2026-03-10T02:00:00Z"}` | `{"status": "success", "message": "Notification queued for delivery."}` |
| `valid-api-key-123` | `"987654321"` | `"Your report is ready."` | `"normal"` | `{}` | `{"status": "success", "message": "Notification queued for delivery."}` |
| `valid-api-key-123` | `"112233445"` | `"Deployment successful"` | `"normal"` | `{"deployment_id": "deploy-abc-789"}` | `{"status": "success", "message": "Notification queued for delivery."}` |

### Scenario 2: Authentication Failure

**Given** an invalid, missing, or expired `X-Akasa-API-Key` is provided in the request header.
**When** a `POST` request is sent to `/api/v1/notifications/send`.
**Then** the API key validation fails.
**And** the request is rejected immediately.
**And** the endpoint returns `401 Unauthorized`.

#### Examples

| `X-Akasa-API-Key` Header | Expected API Response Status Code | Expected API Response Body |
|---|---|---|
| `invalid-key-456` | `401` | `{"detail": "Invalid or missing API key"}` |
| `""` (empty string) | `401` | `{"detail": "Invalid or missing API key"}` |
| `null` (missing header) | `401` | `{"detail": "Invalid or missing API key"}` |

### Scenario 3: Bad Request - Invalid Payload

**Given** a valid `X-Akasa-API-Key` is provided in the request header.
**When** a `POST` request is sent to `/api/v1/notifications/send` with a payload that is missing required fields or has incorrect data types.
**Then** the payload validation fails.
**And** the request is rejected.
**And** the endpoint returns `400 Bad Request` with details about the validation error.

#### Examples

| `user_id` (Payload) | `message` (Payload) | `priority` (Payload) | `metadata` (Payload) | Expected API Response Status Code | Expected API Response Body |
|---|---|---|---|---|---|
| `null` | `"System update"` | `"normal"` | `{}` | `400` | `{"detail": "user_id is required"}` |
| `"123456789"` | `null` | `"high"` | `{}` | `400` | `{"detail": "message is required"}` |
| `"123456789"` | `"Test"` | `"urgent"` (invalid enum value) | `{}` | `400` | `{"detail": "priority must be one of 'high' or 'normal'"}` |
| `"123456789"` | `"Test"` | `"normal"` | `["invalid_metadata"]` (not an object) | `400` | `{"detail": "metadata must be an object"}` |

### Scenario 4: Internal Error during Notification Dispatch

**Given** a valid `X-Akasa-API-Key` is provided in the request header.
**And** the request payload is valid.
**When** a `POST` request is sent to `/api/v1/notifications/send`.
**And** `TelegramService.send_proactive_message` raises an exception (e.g., `UserChatIdNotFoundException` or `BotBlockedException`).
**Then** the exception is caught by the endpoint handler.
**And** the endpoint returns an appropriate HTTP error response (e.g., `400 Bad Request` for `UserChatIdNotFoundException`, `500 Internal Server Error` for `BotBlockedException` or other unexpected errors).

#### Examples

| `user_id` (Payload) | `message` (Payload) | `priority` (Payload) | `metadata` (Payload) | `TelegramService` Exception | Expected API Response Status Code | Expected API Response Body |
|---|---|---|---|---|---|---|
| `"unknown-user"` | `"Hello"` | `"normal"` | `{}` | `UserChatIdNotFoundException` | `400` | `{"detail": "User not found for notification"}` |
| `"blocked-user"` | `"Maintenance"` | `"high"` | `{}` | `BotBlockedException` | `500` | `{"detail": "Failed to send notification: Bot blocked by user."}` |
| `"user-with-error"` | `"Test"` | `"normal"` | `{}` | `RuntimeError("Unexpected issue")` | `500` | `{"detail": "An internal error occurred during notification dispatch."}` |