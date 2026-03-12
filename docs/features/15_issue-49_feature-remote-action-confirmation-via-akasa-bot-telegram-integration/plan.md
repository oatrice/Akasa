# Implementation Plan: Remote Action Confirmation via Akasa Bot

> **Refers to**: [Spec Link](./spec.md)
> **Status**: Draft

## 1. Architecture & Design
The implementation will introduce a new notification pathway to the Akasa backend, enabling external clients like Gemini CLI to request real-time user confirmation for sensitive actions. The system will use Redis for state management to track requests from initiation to resolution and the Telegram Bot API for user interaction.

The flow is as follows:
1.  **Initiation**: Gemini CLI sends a `POST` request to a new `/notifications/send` endpoint.
2.  **Stateful Processing**: The backend generates a unique `request_id`, stores the action details in Redis with a `pending` status, and sends a notification to the user's Telegram via `TelegramService`.
3.  **User Interaction**: The user receives a Telegram message with `Allow` and `Deny` inline buttons. Pressing a button sends a `callback_query` to the existing Telegram webhook.
4.  **Callback Handling**: The webhook handler identifies the `callback_query`, updates the request status in Redis to `allowed` or `denied`, and edits the original Telegram message to reflect the decision.
5.  **Resolution**: The Gemini CLI client polls a new `/notifications/requests/{request_id}` endpoint until the status changes from `pending`, then proceeds or cancels the action based on the result.

### Component View
- **Modified Components**:
    - `app/services/telegram_service.py`: To support sending messages with inline keyboards for confirmation.
    - `app/services/redis_service.py`: To add specific methods for creating, retrieving, and updating action request states.
    - `app/routers/telegram.py`: To handle `callback_query` updates from the new inline keyboards.
- **New Components**:
    - `app/routers/notifications.py`: A new FastAPI router to expose endpoints for sending notification requests and polling for their status.
    - `app/models/notification.py`: Will contain Pydantic models for the notification request payload and the state data stored in Redis.
- **Dependencies**: No new external libraries are required. We will leverage existing `redis-py` and `python-telegram-bot` libraries.

### Data Model Changes
```python
# app/models/notification.py

from pydantic import BaseModel, Field
from typing import Literal, Optional
import datetime

class ActionRequestMetadata(BaseModel):
    """Metadata for a remote action confirmation request."""
    request_id: str
    command: str
    cwd: str
    type: str = "shell_command_confirmation"

class NotificationRequest(BaseModel):
    """Payload from the client (Gemini CLI) to request a notification."""
    chat_id: str
    message: str
    metadata: ActionRequestMetadata

class ActionRequestState(BaseModel):
    """Data structure for storing the state of an action request in Redis."""
    status: Literal["pending", "allowed", "denied"] = "pending"
    command: str
    cwd: str
    requested_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    decided_by: Optional[str] = None
    decided_at: Optional[datetime.datetime] = None

```

---

## 2. Step-by-Step Implementation

### Step 1: Data Models and Redis Service Enhancement
- **Description**: Define the required Pydantic models and extend `RedisService` to handle the lifecycle of an action request.
- **Code**:
    - **Create `app/models/notification.py`**: Implement `ActionRequestMetadata`, `NotificationRequest`, and `ActionRequestState` Pydantic models as defined above.
    - **Modify `app/services/redis_service.py`**:
        - Add `set_action_request(request_id: str, state: ActionRequestState)`.
        - Add `get_action_request(request_id: str) -> Optional[ActionRequestState]`.
- **Tests**:
    - **Create `tests/services/test_redis_service_action_requests.py`**:
        - Write unit tests to verify that `ActionRequestState` objects can be correctly serialized, stored, retrieved, and deserialized.

### Step 2: Enhance Telegram Service
- **Description**: Add a method to `TelegramService` to send messages that include inline confirmation keyboards.
- **Code**:
    - **Modify `app/services/telegram_service.py`**:
        - Implement `send_confirmation_message(chat_id: str, message: str, request_id: str)`.
        - This method will construct an `InlineKeyboardMarkup` with two `InlineKeyboardButton`s ("✅ Allow", "❌ Deny").
        - The `callback_data` for each button must be structured to be easily parsed, e.g., `"confirm:<request_id>:allow"` and `"confirm:<request_id>:deny"`.
- **Tests**:
    - **Modify `tests/services/test_telegram_service.py`**:
        - Add a test that mocks the `bot.send_message` call and verifies that it's called with the correct `chat_id`, `text`, and `reply_markup` containing the proper keyboard layout and `callback_data`.

### Step 3: Create Notification Endpoints
- **Description**: Create the new router and implement the endpoints for initiating a request and polling for its status.
- **Code**:
    - **Create `app/routers/notifications.py`**:
        - Add a new `APIRouter`.
        - Implement `POST /send`:
            1.  Accepts a `NotificationRequest` payload.
            2.  Initializes an `ActionRequestState` model.
            3.  Calls `redis_service.set_action_request`.
            4.  Calls `telegram_service.send_confirmation_message`.
            5.  Returns `{"request_id": metadata.request_id}`.
        - Implement `GET /requests/{request_id}`:
            1.  Calls `redis_service.get_action_request`.
            2.  Returns the retrieved `ActionRequestState` object or a 404 error if not found.
    - **Modify `app/main.py`**: Mount the new notification router.
- **Tests**:
    - **Create `tests/routers/test_notifications.py`**:
        - Write unit tests for both `/send` and `/requests/{request_id}` endpoints, mocking the service dependencies.

### Step 4: Implement Telegram Callback Logic
- **Description**: Update the Telegram webhook to handle the `callback_query` from the confirmation buttons.
- **Code**:
    - **Modify `app/routers/telegram.py`**:
        - In the webhook handler, add logic to detect if the `update` contains a `callback_query`.
        - If the `callback_data` starts with `"confirm:"`:
            1.  Parse the `request_id` and decision (`allow`/`deny`).
            2.  Fetch the `ActionRequestState` from Redis.
            3.  If the status is `pending`, update it with the decision, `decided_by` (from `update.callback_query.from_user.username`), and `decided_at`.
            4.  Save the updated state back to Redis.
            5.  Use `update.callback_query.edit_message_text` to update the original message, confirming the action taken and removing the inline keyboard.
- **Tests**:
    - **Modify `tests/routers/test_telegram.py`**:
        - Add a new test case that sends a mock `Update` object containing a `CallbackQuery` to the webhook endpoint.
        - Verify that the `RedisService` and `edit_message_text` methods are called with the expected arguments.

---

## 3. Verification Plan
*How will we verify success?*

### Automated Tests
- [ ] **Redis Service**: `tests/services/test_redis_service_action_requests.py` is created and all tests pass.
- [ ] **Telegram Service**: `tests/services/test_telegram_service.py` is updated and all tests pass.
- [ ] **Notifications Router**: `tests/routers/test_notifications.py` is created and all tests pass.
- [ ] **Telegram Router**: `tests/routers/test_telegram.py` is updated with callback tests and all tests pass.

### Manual Verification
- [ ] **End-to-End Happy Path (Allow)**:
    1.  Start the Akasa backend server.
    2.  Use a tool like `curl` to `POST` a valid `NotificationRequest` to the `/api/v1/notifications/send` endpoint.
    3.  Verify the bot sends a message to the specified `chat_id` with "✅ Allow" and "❌ Deny" buttons.
    4.  Use `curl` to `GET` the status from `/api/v1/notifications/requests/{request_id}` and verify it is `pending`.
    5.  Click the "✅ Allow" button in Telegram.
    6.  Verify the message text is updated to show "Allowed" and the buttons are removed.
    7.  Poll the status endpoint again and verify the status is now `allowed`.
- [ ] **End-to-End Denial Path (Deny)**:
    1.  Repeat steps 1-4 from the "Allow" path.
    2.  Click the "❌ Deny" button in Telegram.
    3.  Verify the message text is updated to show "Denied" and the buttons are removed.
    4.  Poll the status endpoint again and verify the status is now `denied`.
- [ ] **End-to-End Edge Case (Double-Click)**:
    1. After clicking "Allow" or "Deny" once, confirm that the Telegram client shows a notification (e.g., a small loading icon on the button) and that clicking again has no effect on the state in Redis.