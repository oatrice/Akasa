# Implementation Plan: Telegram Integration for Local Tools & AI Agent Monitoring

> **Refers to**: [Spec Link](./spec.md)
> **Status**: Draft

## 1. Architecture & Design
*This plan outlines the technical approach for implementing a bidirectional command queue between Telegram and local development tools, and a mechanism for monitoring AI agent task timeouts within the Akasa system.*

### Component View

-   **Modified Components**:
    *   **Akasa Backend**:
        *   Telegram Bot Handler: To parse incoming commands, authenticate users, and validate commands.
        *   Redis Integration: For enqueuing commands and managing AI agent status.
        *   Notification Service: To send Telegram alerts for command results and agent timeouts.
    *   **Redis**: Used as the central message broker for command queues and agent status storage.
    *   **AI Agents**: Will be modified to report their "starting" status to Redis.

-   **New Components**:
    *   `scripts/local_tool_daemon.py`: A new lightweight Python daemon responsible for polling Redis command queues and executing local tool commands.
    *   **Akasa Backend - Background Timeout Observer**: A new background task/service within the Akasa backend to periodically check AI agent statuses in Redis for timeouts.

-   **Dependencies**:
    *   Redis (for command queues and status storage)
    *   Telegram Bot API (for command reception and notification delivery)
    *   Python libraries for Redis client, subprocess execution (for local daemon).

### Data Model Changes

```python
# Redis Key Structures:

# 1. Telegram to Local Tools Command Queue (Feature #66)
# Key: akasa:commands:{tool_name} (e.g., akasa:commands:gemini_cli, akasa:commands:luma)
# Type: Redis List (LPUSH/BRPOP)
# Value: JSON string representing the command payload.
# Example Payload:
{
    "user_id": "telegram_user_id_123",  # Whitelisted Telegram user ID
    "tool": "gemini_cli",               # Target local tool
    "command": "run_task --task_id 123", # Command string to execute
    "ttl": 300,                         # Time-To-Live in seconds (for Redis expiration, though list items don't expire directly, this is for daemon to respect)
    "timestamp": "2026-03-14T10:00:00Z" # Timestamp of command enqueue
}

# 2. AI Agent Timeout Observer (Feature #67)
# Key: akasa:agent_status:{agent_id} (e.g., akasa:agent_status:ai-analyst-001)
# Type: Redis Hash or String (depending on complexity, Hash is more flexible)
# Value: JSON string or Hash fields representing agent status.
# Example Payload (as a String for simplicity, or Hash for more fields):
{
    "agent_id": "ai-analyst-001",
    "status": "starting",               # Current status (e.g., "starting", "running", "completed", "failed")
    "timestamp": "2026-03-14T10:00:00Z" # Last status update timestamp
}
# Note: For Redis String, SETEX can be used to provide an explicit TTL for the status key itself.
```

---

## 2. Step-by-Step Implementation

### Step 1: Akasa Backend - Telegram Command Ingestion & Whitelisting
-   **Docs**: Update Akasa backend API documentation for new Telegram command endpoints and expected payloads.
-   **Code**:
    *   Modify the Akasa backend's Telegram message handler to recognize new commands (e.g., `/gemini`, `/luma`).
    *   Implement user authentication/authorization: Verify `user_id` against a whitelist of authorized users.
    *   Implement command whitelisting: Define a configurable whitelist of allowed commands and arguments for each local tool (e.g., `gemini_cli: ["run_task", "list_tasks"]`). Reject any commands not on the whitelist.
    *   **Files**: `akasa/backend/telegram_handler.py`, `akasa/backend/config.py` (for whitelists).
-   **Tests**:
    *   Unit tests for `telegram_handler.py` to verify user authentication, command parsing, and whitelisting logic.
    *   Test cases for valid and invalid users, valid and invalid commands.

### Step 2: Akasa Backend - Enqueue Command to Redis with TTL
-   **Docs**: Document the Redis queue structure and command payload format.
-   **Code**:
    *   Upon successful validation (Step 1), construct the command JSON payload.
    *   Use `RPUSH` to enqueue the command JSON string into the appropriate Redis list (e.g., `akasa:commands:gemini_cli`).
    *   The `ttl` field in the JSON payload will be used by the daemon, not Redis's native TTL for list items.
    *   **Files**: `akasa/backend/command_queue_service.py` (new service), `akasa/backend/redis_client.py`.
-   **Tests**:
    *   Unit tests for `command_queue_service.py` to ensure correct JSON payload creation and successful `RPUSH` to Redis.
    *   Mock Redis client to verify interactions.

### Step 3: Local Tool Daemon - Redis Polling & Command Execution
-   **Docs**: Create a `README.md` for `scripts/local_tool_daemon.py` explaining setup, configuration, and usage.
-   **Code**:
    *   Create `scripts/local_tool_daemon.py`.
    *   Implement a continuous polling loop using `BLPOP` (blocking left pop) on the configured Redis command queues (e.g., `akasa:commands:gemini_cli`, `akasa:commands:luma`). This will block until a command is available.
    *   Upon retrieving a command, parse the JSON payload.
    *   Check the `ttl` field in the payload against the current time. If expired, log and discard the command.
    *   Execute the `command` using `subprocess.run()` or similar, ensuring proper sanitization and error handling.
    *   **Files**: `scripts/local_tool_daemon.py`, `scripts/daemon_config.py`.
-   **Tests**:
    *   Unit tests for `local_tool_daemon.py` to verify Redis polling, command parsing, TTL check, and subprocess execution (mock `subprocess`).
    *   Test cases for expired commands, valid commands, and commands leading to execution errors.

### Step 4: Local Tool Daemon - Report Execution Results to Akasa Backend
-   **Docs**: Define the API endpoint for the daemon to report results.
-   **Code**:
    *   After executing a command (Step 3), capture the `stdout`, `stderr`, and exit code.
    *   Send an HTTP POST request to a dedicated Akasa backend endpoint with the execution results (success/failure, output, original command ID/timestamp for correlation).
    *   Implement retry logic for reporting results in case of network issues.
    *   **Files**: `scripts/local_tool_daemon.py`.
-   **Tests**:
    *   Unit tests for the daemon's result reporting function, mocking HTTP requests to the backend.

### Step 5: Akasa Backend - Forward Execution Results to Telegram
-   **Docs**: Update Telegram notification documentation.
-   **Code**:
    *   Create a new Akasa backend API endpoint to receive execution results from the local daemon.
    *   Process the results and format a user-friendly message.
    *   Use the Akasa backend's Telegram notification service to send the message to the original `user_id` (retrieved from the command payload or correlated via an ID).
    *   **Files**: `akasa/backend/daemon_callback_handler.py` (new endpoint), `akasa/backend/notification_service.py`.
-   **Tests**:
    *   Unit tests for `daemon_callback_handler.py` to verify result processing and interaction with the notification service.
    *   Integration tests: Simulate a full command flow from Telegram to daemon and back to Telegram notification.

### Step 6: AI Agents - Implement "starting" status reporting to Redis
-   **Docs**: Document the expected Redis key and payload format for AI agent status.
-   **Code**:
    *   Modify existing AI agent codebases to report a "starting" status to Redis (`akasa:agent_status:{agent_id}`) at the beginning of a task.
    *   Include `agent_id`, `status: "starting"`, and `timestamp` in the Redis value.
    *   Use `SETEX` to set a TTL on the Redis key itself (e.g., 2x the expected timeout duration) to automatically clean up stale status entries.
    *   **Files**: `akasa/agents/{agent_name}/main.py` (or relevant entry point).
-   **Tests**:
    *   Unit tests within agent projects to verify correct Redis status reporting.
    *   Mock Redis client to ensure `SETEX` and correct payload.

### Step 7: Akasa Backend - Implement Background Timeout Observer
-   **Docs**: Document the configuration for the timeout threshold.
-   **Code**:
    *   Create a new background task/service within the Akasa backend (e.g., a Celery task, a dedicated thread, or a cron job).
    *   This observer will periodically scan Redis for keys matching `akasa:agent_status:*`.
    *   For each active agent status, check if `status` is "starting" and if `timestamp` indicates it has exceeded the configurable timeout duration (e.g., 15 minutes).
    *   If a timeout is detected, mark the agent as timed out (e.g., by updating its status in Redis to "timed_out" to prevent duplicate alerts).
    *   **Files**: `akasa/backend/agent_timeout_observer.py` (new service), `akasa/backend/config.py` (for timeout threshold).
-   **Tests**:
    *   Unit tests for `agent_timeout_observer.py` to verify status parsing, timestamp comparison, and timeout detection logic.
    *   Test cases for agents within and beyond the timeout threshold.

### Step 8: Akasa Backend - Alerting via Telegram for Timeouts
-   **Docs**: Document the format of timeout alert messages.
-   **Code**:
    *   When a timeout is detected (Step 7), use the Akasa backend's Telegram notification service to send a "CRITICAL ALERT" message to the associated Telegram user.
    *   The alert message should include the `agent_id` and a clear indication of the timeout.
    *   **Files**: `akasa/backend/agent_timeout_observer.py`, `akasa/backend/notification_service.py`.
-   **Tests**:
    *   Unit tests for the observer's alerting mechanism, mocking the notification service.
    *   Integration tests: Simulate an agent starting, timing out, and the user receiving a Telegram alert.

---

## 3. Verification Plan
*Verification will cover both automated and manual testing to ensure the robustness and correctness of the new features.*

### Automated Tests
-   [x] **Unit Tests**:
    *   `akasa/backend/telegram_handler.py`: Command parsing, user auth, command whitelisting.
    *   `akasa/backend/command_queue_service.py`: Redis enqueue logic, payload formatting.
    *   `scripts/local_tool_daemon.py`: Redis polling, command execution (mock subprocess), TTL check, result reporting (mock HTTP).
    *   `akasa/backend/daemon_callback_handler.py`: Result processing, notification triggering.
    *   `akasa/agents/{agent_name}/main.py`: Agent status reporting to Redis.
    *   `akasa/backend/agent_timeout_observer.py`: Timeout detection, status update, alert triggering (mock notification).
-   [ ] **Integration Tests**:
    *   **Telegram to Local Tools Flow**:
        *   Send a Telegram command -> Akasa Backend processes -> Command enqueued in Redis -> Local Daemon picks up & executes -> Daemon reports result to Akasa Backend -> Akasa Backend sends Telegram notification.
        *   Test command expiration: Enqueue a command, ensure daemon doesn't pick it up after TTL.
        *   Test unauthorized user/command rejection.
    *   **AI Agent Timeout Flow**:
        *   AI Agent reports "starting" status to Redis -> Background Observer detects timeout after configured duration -> Akasa Backend sends critical Telegram alert.
        *   Test agent reporting "completed" status before timeout, ensuring no alert is sent.

### Manual Verification
-   [ ] **Scenario 5.1: Triggering a Gemini CLI task from Telegram**
    *   **Preconditions**: Akasa backend, Redis, and `local_tool_daemon.py` running. User's Telegram ID whitelisted. `gemini run_task --task_id 123` whitelisted.
    *   **Steps**:
        1.  Send `/gemini run_task --task_id 123` from Telegram.
        2.  Observe Redis queue `akasa:commands:gemini_cli` for the enqueued command.
        3.  Verify `local_tool_daemon.py` logs show command retrieval and execution.
        4.  Receive "Gemini CLI task 123 completed successfully." (or failure) notification in Telegram.
-   [ ] **Scenario 5.2: AI Agent Task Timeout Detection and Alerting**
    *   **Preconditions**: Akasa backend, Redis, and Timeout Observer running. Timeout threshold set to a short duration for testing (e.g., 1 minute).
    *   **Steps**:
        1.  Manually simulate an AI agent reporting `{ "agent_id": "test-agent-001", "status": "starting", "timestamp": "current_time" }` to `akasa:agent_status:test-agent-001` in Redis.
        2.  Wait for the configured timeout duration.
        3.  Receive "CRITICAL ALERT: AI Agent 'test-agent-001' has timed out." notification in Telegram.
        4.  Verify Redis status for `test-agent-001` is updated to "timed_out".
-   [ ] **Scenario 5.3: Command Expiration Due to Stale Queue Entry**
    *   **Preconditions**: Akasa backend and Redis running. `local_tool_daemon.py` is *not* running or significantly delayed. Command TTL set to a short duration (e.g., 1 minute).
    *   **Steps**:
        1.  Send `/luma run_job --job_id 456` from Telegram.
        2.  Observe Redis queue `akasa:commands:luma` for the enqueued command.
        3.  Wait for the command's TTL to expire (e.g., 1 minute).
        4.  Verify the command is no longer in the Redis queue.
        5.  Start `local_tool_daemon.py`. Verify it does not pick up the expired command.
        6.  Confirm no Telegram notification is received for this command (as it was never executed).