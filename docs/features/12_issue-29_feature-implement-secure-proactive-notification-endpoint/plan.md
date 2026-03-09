# Implementation Plan: Secure Proactive Notification Endpoint

> **Refers to**: [Spec Link](./spec.md)
> **Status**: Draft

## 1. Architecture & Design
*High-level technical approach.*

This implementation will introduce a new router (`notifications.py`) to handle incoming notification requests. A Pydantic model will be defined for request payload validation. API key authentication will be implemented as a FastAPI dependency. The core logic will involve validating the API key, parsing and validating the request payload, and then invoking the existing `TelegramService.send_proactive_message` function. Appropriate HTTP responses will be returned for success, authentication failures, payload validation errors, and internal dispatch errors.

### Component View
- **New Components**:
    - `app/routers/notifications.py`: Contains the new API endpoint definition.
    - `app/schemas/notification.py`: Defines the Pydantic model for the notification request payload.
    - `app/core/security.py`: Will contain the dependency function for API key authentication (or this logic will be integrated into the router if a separate file is not idiomatic).
    - `tests/routers/test_notifications.py`: For integration tests of the new endpoint.
- **Modified Components**:
    - `app/main.py`: To include the new notification router.
    - `app/config.py`: To ensure the master API key is accessible (assuming it's loaded via settings).
- **Dependencies**: FastAPI, Pydantic, `httpx` (for `TelegramService` which is assumed functional), `pytest` for testing.

### Data Model Changes
```python
# Defined new data structures or database schema changes
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class NotificationPayload(BaseModel):
    user_id: str
    message: str
    priority: Optional[str] = Field("normal", enum=["high", "normal"])
    metadata: Optional[Dict[str, Any]] = {}

class ApiResponse(BaseModel):
    status: str
    message: str
```

---

## 2. Step-by-Step Implementation

### Step 1: Define Notification Payload Model
- **Description**: Create a Pydantic model to define and validate the structure of the incoming notification payload.
- **Files to Modify**: `app/schemas/notification.py` (new file)
- **Code**:
  - Create `app/schemas/notification.py`.
  - Define `NotificationPayload` model with `user_id`, `message`, `priority`, and `metadata` fields, including type hints and default values as per specification.
- **Verification**:
  - Unit tests for `NotificationPayload` to ensure it correctly validates valid and invalid payloads.

### Step 2: Implement API Key Authentication Dependency
- **Description**: Create a reusable dependency function to authenticate incoming requests by checking the `X-Akasa-API-Key` header.
- **Files to Modify**: `app/core/security.py` (new file, or integrate into router if no existing security module)
- **Code**:
  - Create `app/core/security.py` (or similar).
  - Define an `async` function `verify_api_key(api_key: str = Header(None))` that:
    - Retrieves the expected API key from `settings.AKASA_API_KEY`.
    - Compares the provided `api_key` with the expected key.
    - Raises `HTTPException(status_code=401, detail="Invalid or missing API key")` if validation fails.
- **Verification**:
  - Unit tests for `verify_api_key` dependency to check successful validation and failure cases.

### Step 3: Create Notification Router
- **Description**: Implement the API endpoint logic, including payload parsing, validation, authentication, and calling the `TelegramService`.
- **Files to Modify**: `app/routers/notifications.py` (new file)
- **Code**:
  - Create `app/routers/notifications.py`.
  - Import necessary modules: `FastAPI`, `HTTPException`, `Header`, `Depends`, `APIRouter`, `List`, `Dict`, `Any`, `Optional`.
  - Import `NotificationPayload` from `app.schemas.notification`.
  - Import `verify_api_key` dependency.
  - Import `TelegramService` (assuming `tg_service` instance is available).
  - Import `UserChatIdNotFoundException`, `BotBlockedException` from `app.exceptions`.
  - Instantiate `APIRouter`.
  - Define `POST /api/v1/notifications/send` route:
    - Use `depends=Depends(verify_api_key)` for authentication.
    - Use `response_model=ApiResponse` (assuming `ApiResponse` model exists or will be created).
    - Accept `payload: NotificationPayload` and `api_key: str = Header(...)`.
    - Inside the route function:
        - Log the incoming request.
        - Use a `try...except` block for robust error handling.
        - Call `tg_service.send_proactive_message(user_id=payload.user_id, message=payload.message)` (Note: `send_proactive_message` signature might need adjustment if it doesn't accept priority/metadata, or this logic needs to be handled before the call). *Self-correction: The spec implies `send_proactive_message` might not directly use priority/metadata, so this plan will pass user_id and message, and logging/handling of priority/metadata can be done within the router or a new layer if needed.*
        - Catch `UserChatIdNotFoundException` and `BotBlockedException`, raising appropriate `HTTPException`s (e.g., 400 for not found, 500 for blocked).
        - Catch generic `Exception` for unexpected errors, raising `HTTPException(status_code=500)`.
        - On success, return `{"status": "success", "message": "Notification queued for delivery."}`.
- **Verification**:
  - Unit tests for the router logic itself, mocking `TelegramService` and `verify_api_key`.

### Step 4: Register Router in Main Application
- **Description**: Add the new notification router to the main FastAPI application instance.
- **Files to Modify**: `app/main.py`
- **Code**:
  - Import the `notifications_router` from `app.routers.notifications`.
  - Include the router in the FastAPI app instance: `app.include_router(notifications_router, prefix="/api/v1")`.
- **Verification**:
  - Ensure the application starts without errors.
  - Verify the new route is listed when running `uvicorn app.main:app --reload` and checking `/docs`.

### Step 5: Add Tests for the New Endpoint
- **Description**: Create integration tests for the `/api/v1/notifications/send` endpoint covering all scenarios defined in the SBE.
- **Files to Modify**: `tests/routers/test_notifications.py` (new file)
- **Code**:
  - Use FastAPI's `TestClient` to make requests to the endpoint.
  - Mock `verify_api_key` dependency to control authentication outcomes.
  - Mock `TelegramService.send_proactive_message` to simulate its behavior (success, `UserChatIdNotFoundException`, `BotBlockedException`).
  - Write tests for:
    - Successful send with valid key and payload.
    - Authentication failure (missing/invalid key).
    - Bad request (invalid payload).
    - Internal errors from `TelegramService`.
- **Verification**:
  - Run `pytest` to ensure all new tests pass.

---

## 3. Verification Plan
*How will we verify success?*

### Automated Tests
- [ ] Unit tests for `NotificationPayload` model.
- [ ] Unit tests for `verify_api_key` dependency.
- [ ] Integration tests for the `/api/v1/notifications/send` endpoint in `tests/routers/test_notifications.py`, covering all SBE scenarios (happy path, auth failure, bad request, internal errors).

### Manual Verification
- **Step 1**: Ensure the application is running locally.
- **Step 2**: Use `curl` or an API client (like Postman/Insomnia) to send `POST` requests to `http://localhost:8000/api/v1/notifications/send`.
    - **Test Case**: Send a request with a valid API key and valid payload.
        - **Expected Result**: `200 OK` response with `{"status": "success", "message": "Notification queued for delivery."}`.
    - **Test Case**: Send a request with an invalid `X-Akasa-API-Key` header.
        - **Expected Result**: `401 Unauthorized` response.
    - **Test Case**: Send a request with a valid API key but a malformed payload (e.g., missing `user_id`).
        - **Expected Result**: `400 Bad Request` response with validation error details.
    - **Test Case**: Simulate `TelegramService` raising `UserChatIdNotFoundException` (requires mocking or a specific test setup if possible).
        - **Expected Result**: `400 Bad Request` response with `{"detail": "User not found for notification"}`.
    - **Test Case**: Simulate `TelegramService` raising `BotBlockedException` (requires mocking or specific test setup).
        - **Expected Result**: `500 Internal Server Error` response with `{"detail": "Failed to send notification: Bot blocked by user."}`.