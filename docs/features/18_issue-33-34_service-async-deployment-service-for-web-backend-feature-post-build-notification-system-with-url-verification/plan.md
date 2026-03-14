# Implementation Plan: Asynchronous Deployment Service with Post-Build Notification and URL Verification

> **Refers to**: [Spec Link](./spec.md)
> **Status**: Draft

## 1. Architecture & Design
This feature introduces an asynchronous deployment mechanism, leveraging a task queue for background processing, Redis for transient status storage, and Telegram for notifications. The core will be a new set of API endpoints that interact with these new services.

### Component View
- **Modified Components**:
    *   `app/main.py`: To register new API routers.
    *   `app/dependencies.py` (or similar): To inject Redis client, Celery app, Telegram bot client.
- **New Components**:
    *   `app/api/endpoints/deployments.py`: New API router for `/deploy` and `/status` endpoints.
    *   `app/core/status_store.py`: Module for interacting with Redis to store and retrieve deployment statuses.
    *   `app/core/notification_service.py`: Module for sending Telegram notifications.
    *   `app/tasks/deployment_tasks.py`: Celery tasks for executing background deployments.
    *   `app/schemas/deployment.py`: Pydantic models for request/response bodies and internal data structures.
    *   `celery_app.py`: Configuration and instantiation of the Celery application.
    *   `Dockerfile` (or `docker-compose.yml`): To include Celery worker service and Redis.
- **Dependencies**:
    *   `redis-py`: Python client for Redis.
    *   `celery`: Asynchronous task queue.
    *   `python-telegram-bot`: Telegram Bot API wrapper.
    *   `python-dotenv` (for local development): To manage environment variables.
    *   `subprocess` (built-in): For executing external deployment commands (`vercel deploy`, `render-cli deploy`).

### Data Model Changes
```python
# app/schemas/deployment.py
from enum import Enum
from typing import Optional
from pydantic import BaseModel

class DeploymentStatusEnum(str, Enum):
    PENDING = "PENDING"
    BUILDING = "BUILDING"
    DEPLOYING = "DEPLOYING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

class DeploymentRequest(BaseModel):
    service_name: str # e.g., "Web", "Backend"

class DeploymentInitiatedResponse(BaseModel):
    status: str
    deployment_id: str

class DeploymentStatusResponse(BaseModel):
    deployment_id: str
    status: DeploymentStatusEnum
    service_name: str
    url: Optional[str] = None
    error: Optional[str] = None
    timestamp: str # ISO format

# Internal representation for Redis storage
# No explicit ORM model, but a dict structure will be stored in Redis
# Key: f"deployment:{deployment_id}"
# Value: JSON string of DeploymentStatusResponse
```

---

## 2. Step-by-Step Implementation

### Step 1: Core Infrastructure Setup (Redis, Celery, Telegram Bot)
- **Docs**:
    *   Update `README.md` with instructions for running Redis and Celery worker.
    *   Document required environment variables (e.g., `REDIS_URL`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`).
- **Code**:
    *   **`celery_app.py`**: Initialize Celery app, configure Redis as broker and backend.
    *   **`requirements.txt`**: Add `redis`, `celery`, `python-telegram-bot`.
    *   **`Dockerfile` / `docker-compose.yml`**: Add Redis service and Celery worker service.
    *   **`app/core/config.py`**: Define `Settings` class to load environment variables for Redis URL, Telegram token/chat ID.
    *   **`app/dependencies.py`**: Create functions to provide `Redis` client and `Telegram.Bot` instance as dependencies.
- **Tests**:
    *   **`tests/test_infra.py`**:
        *   Verify Redis connection.
        *   Verify Celery app can be initialized and worker starts (basic sanity check, not full task execution yet).
        *   Verify Telegram bot client can be initialized.

### Step 2: Deployment Status Management (FR2.1, FR2.2)
- **Docs**: Document the Redis key structure and data format for deployment statuses.
- **Code**:
    *   **`app/schemas/deployment.py`**: Define `DeploymentStatusEnum` and `DeploymentStatusResponse` (as above).
    *   **`app/core/status_store.py`**:
        *   Create `StatusStore` class with methods:
            *   `set_status(deployment_id: str, service_name: str, status: DeploymentStatusEnum, url: Optional[str] = None, error: Optional[str] = None)`: Stores/updates status in Redis.
            *   `get_status(deployment_id: str) -> Optional[DeploymentStatusResponse]`: Retrieves status from Redis.
        *   Use `json.dumps` and `json.loads` for storing/retrieving `DeploymentStatusResponse` objects.
- **Tests**:
    *   **`tests/core/test_status_store.py`**:
        *   Unit tests for `StatusStore.set_status` and `get_status` (mocking Redis client).
        *   Integration test: Use a real Redis instance (e.g., via `pytest-redis`) to verify persistence and retrieval.

### Step 3: Telegram Notification Service (FR3.1 - FR3.6)
- **Docs**: Document the expected message formats for success and failure, including inline keyboard structure.
- **Code**:
    *   **`app/core/notification_service.py`**:
        *   Create `NotificationService` class.
        *   Method: `send_deployment_notification(deployment_id: str, service_name: str, status: DeploymentStatusEnum, url: Optional[str] = None, error: Optional[str] = None)`
        *   Implement logic to construct Telegram messages:
            *   For `SUCCESS`: "Deployment of {service_name} Successful!" with an inline keyboard button `[View {service_name}]({url})`.
            *   For `FAILED`: "Deployment of {service_name} Failed! Error: {error_summary}."
        *   Use `telegram.Bot.send_message` and `telegram.InlineKeyboardMarkup`/`InlineKeyboardButton`.
- **Tests**:
    *   **`tests/core/test_notification_service.py`**:
        *   Unit tests for `NotificationService.send_deployment_notification` (mocking `telegram.Bot` and verifying `send_message` calls with correct arguments, including `reply_markup`).
        *   Verify message content and button structure for both success and failure scenarios.

### Step 4: Asynchronous Deployment Task (FR1.3, FR2.2)
- **Docs**: Document how service names map to actual shell commands and how URLs are extracted.
- **Code**:
    *   **`app/tasks/deployment_tasks.py`**:
        *   Create a Celery task `deploy_service_task(deployment_id: str, service_name: str, telegram_chat_id: str)`.
        *   Inside the task:
            1.  Get `StatusStore` and `NotificationService` instances.
            2.  Update status to `BUILDING` via `StatusStore.set_status`.
            3.  Map `service_name` to actual shell commands (e.g., `vercel deploy` for "Web", `render-cli deploy` for "Backend").
            4.  Execute command using `subprocess.run`.
            5.  Update status to `DEPLOYING` (optional, can go directly to SUCCESS/FAILED after build).
            6.  **Parse output**: Extract deployed URL from `stdout` if successful (e.g., regex for Vercel URLs).
            7.  If `subprocess.run` returns success:
                *   Update status to `SUCCESS` with the extracted URL.
            8.  If `subprocess.run` returns failure:
                *   Update status to `FAILED` with error details from `stderr`.
            9.  Call `NotificationService.send_deployment_notification` with final status, URL (if successful), and error (if failed).
- **Tests**:
    *   **`tests/tasks/test_deployment_tasks.py`**:
        *   Unit tests for `deploy_service_task` (mocking `subprocess.run`, `StatusStore`, `NotificationService`).
        *   Verify status updates at different stages.
        *   Verify correct command execution.
        *   Verify URL extraction logic.
        *   Verify `NotificationService` is called with correct parameters.
        *   Integration test: Run a Celery worker in a test environment, enqueue a task, verify Redis status updates and (mocked) Telegram notification.

### Step 5: API Endpoints for Deployment Initiation and Status Query (FR1.1, FR1.2, FR2.3)
- **Docs**: Document the `/deploy` and `/status/{deployment_id}` API endpoints, including request/response schemas.
- **Code**:
    *   **`app/api/endpoints/deployments.py`**:
        *   Create a FastAPI `APIRouter`.
        *   **`POST /deploy`**:
            *   Accept `DeploymentRequest` (e.g., `{"service_name": "Web"}`).
            *   Generate a unique `deployment_id` (e.g., `uuid.uuid4()`).
            *   Store initial `PENDING` status in Redis using `StatusStore.set_status`.
            *   Enqueue `deploy_service_task.delay(deployment_id, service_name, TELEGRAM_CHAT_ID)`.
            *   Return `DeploymentInitiatedResponse`.
        *   **`GET /status/{deployment_id}`**:
            *   Accept `deployment_id` as a path parameter.
            *   Retrieve status from Redis using `StatusStore.get_status`.
            *   Return `DeploymentStatusResponse` or 404 if not found.
    *   **`app/main.py`**: Include the new `deployments_router`.
- **Tests**:
    *   **`tests/api/test_deployments.py`**:
        *   Integration tests for `POST /deploy`:
            *   Verify immediate `202 Accepted` response with `deployment_id`.
            *   Verify initial `PENDING` status in Redis.
            *   Verify Celery task is enqueued (mock Celery or inspect queue).
        *   Integration tests for `GET /status/{deployment_id}`:
            *   Verify correct status retrieval for PENDING, BUILDING, SUCCESS, FAILED states (by pre-populating Redis).
            *   Verify 404 for non-existent `deployment_id`.

---

## 3. Verification Plan
### Automated Tests
- [x] Unit Tests:
    *   `tests/core/test_status_store.py`: Test `set_status`, `get_status` methods.
    *   `tests/core/test_notification_service.py`: Test message formatting and Telegram API calls.
    *   `tests/tasks/test_deployment_tasks.py`: Test `deploy_service_task` logic, `subprocess` calls, status updates, URL extraction, and notification triggers.
- [x] Integration Tests:
    *   `tests/api/test_deployments.py`: Test `/deploy` and `/status` endpoints, verifying interaction with Redis and Celery.
    *   End-to-End Test (using a test Celery worker and mocked external commands/Telegram):
        *   Initiate deployment via API.
        *   Query status at various stages.
        *   Verify final status and URL/error in Redis.
        *   Verify Telegram notification content (mocking Telegram API).

### Manual Verification
- [x] **Scenario 1: Successful Web Service Deployment and Notification**
    *   Send a `POST /deploy` request for "Web" service.
    *   Verify immediate `202` response with `deployment_id`.
    *   Query `GET /status/{deployment_id}` periodically, observing status changes: PENDING -> BUILDING -> DEPLOYING -> SUCCESS.
    *   Verify a Telegram message is received with "Deployment of Web Service Successful!" and a clickable "View Web Service" button leading to a valid URL.
    *   Click the URL to verify the deployed service (if a mock service is available).
- [x] **Scenario 2: Failed Backend Service Deployment and Notification**
    *   Modify the `deploy_service_task` to simulate a failure for "Backend" service (e.g., force `subprocess.run` to return non-zero exit code).
    *   Send a `POST /deploy` request for "Backend" service.
    *   Verify immediate `202` response with `deployment_id`.
    *   Query `GET /status/{deployment_id}` periodically, observing status changes: PENDING -> BUILDING -> FAILED.
    *   Verify a Telegram message is received with "Deployment of Backend Service Failed!" and relevant error information (no URL button).
- [x] **Scenario 3: Checking Deployment Status**
    *   Initiate a deployment for "Web" service.
    *   Immediately query `GET /status/{deployment_id}` to see "PENDING" or "BUILDING".
    *   Wait a short while, then query again to see "BUILDING" or "DEPLOYING".
    *   After completion, query again to see "SUCCESS" (or "FAILED" if it failed).
    *   Verify the returned JSON matches the expected `DeploymentStatusResponse` schema.

> [!IMPORTANT]
> **Android Build Policy**: This feature is backend-focused and does not involve Android client-side implementation. The Android build policy is not applicable here.