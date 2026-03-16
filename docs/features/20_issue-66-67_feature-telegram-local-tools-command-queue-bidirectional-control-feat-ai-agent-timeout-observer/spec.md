# Specification Document

## 1. Introduction

This document outlines the specifications for two related features aimed at enhancing the integration between Telegram and local development tools within the Akasa system. It details the implementation of a bidirectional command queue for controlling local tools from Telegram (Issue #66) and a mechanism for monitoring AI agent task timeouts (Issue #67).

## 2. Goals

*   **Telegram to Local Tools Command Queue (Issue #66):** To enable users to seamlessly initiate actions on local development tools (such as Luma, Gemini CLI, and Zed IDE) directly from Telegram, creating a remote-to-local workflow.
*   **AI Agent Timeout Observer (Issue #67):** To ensure the reliability and responsiveness of AI agents by detecting and alerting users when tasks become stalled or time out, preventing silent failures.

## 3. User Stories / Journeys

*   **As a developer,** I want to trigger a specific Gemini CLI task from my phone via Telegram, so that I can manage my development environment remotely without needing to be at my desk.
*   **As a developer,** I want to be alerted via Telegram if an AI agent task I initiated is stuck or has timed out, so that I can investigate and resolve the issue promptly.

## 4. Features

### 4.1. Telegram to Local Tools Command Queue (Feature #66)

*   **Functionality:** This feature allows authenticated Telegram users to send commands to local development tools.
*   **Mechanism:**
    *   Commands sent from Telegram are first processed by the Akasa backend.
    *   Valid commands are enqueued into a Redis list, identified by the target tool (e.g., `akasa:commands:gemini_cli`).
    *   A lightweight local polling daemon (e.g., `scripts/local_tool_daemon.py`) continuously monitors these Redis queues.
    *   Upon retrieving a command, the daemon executes the corresponding action on the local tool.
    *   Execution results are reported back to the Akasa backend.
    *   The Akasa backend then forwards the result as a notification back to the Telegram user.
*   **Security:**
    *   **Command Whitelisting:** Only pre-approved commands are allowed to be enqueued, preventing arbitrary command execution.
    *   **User Authentication/Authorization:** Commands can only be queued by the whitelisted Telegram `user_id` associated with the local environment.
    *   **Command Expiration (TTL):** Each enqueued command has a Time-To-Live (TTL) set (defaulting to 5 minutes) to automatically expire and be removed from the queue if not processed within that timeframe.

### 4.2. AI Agent Timeout Observer (Feature #67)

*   **Functionality:** This feature introduces a monitoring system to detect when AI agent tasks become unresponsive or stall.
*   **Mechanism:**
    *   AI agents are expected to report a new status, "starting," when a task is initiated. This status, along with a timestamp, is stored in Redis (e.g., `akasa:agent_status:{agent_id}`).
    *   A background task within the Akasa system periodically polls the status of active AI agent tasks in Redis.
    *   If a task remains in the "starting" state for longer than a configurable duration (e.g., 15 minutes), the system identifies it as a timeout.
*   **Alerting:** Upon detecting a timeout, a critical alert notification is immediately sent to the associated Telegram user, informing them of the stalled agent and prompting investigation.

## 5. Specification by Example (SBE)

### 5.1. Scenario: Triggering a Gemini CLI task from Telegram

*   **Description:** A developer uses their Telegram client to remotely queue and execute a specific Gemini CLI task on their local development machine.
*   **Preconditions:**
    *   Akasa backend is running and connected to Redis.
    *   The Local Tool Daemon is running, configured to poll the Redis queue, and has access to the Gemini CLI.
    *   The user's Telegram ID is recognized and whitelisted by the Akasa backend.
    *   The command `run_task --task_id 123` is included in the Gemini CLI's whitelist of executable commands.
*   **Examples:**

| Step | User Action (Telegram) | Akasa Backend Action | Redis Action | Local Tool Daemon Action | Telegram Notification | Expected Outcome |
|------|------------------------|----------------------|--------------|--------------------------|-----------------------|------------------|
| 1    | User sends `/gemini run_task --task_id 123` command. | Receives command, authenticates user (`owner_id`), validates command against Gemini CLI whitelist. | Enqueues a JSON object `{ "user_id": "owner_id", "tool": "gemini_cli", "command": "run_task --task_id 123", "ttl": 300 }` to the list `akasa:commands:gemini_cli`. | N/A | None | The command is successfully received and queued in Redis with an expiration time. |
| 2    | N/A | N/A | N/A | Polls the `akasa:commands:gemini_cli` list, retrieves the enqueued command. Executes `gemini run_task --task_id 123` locally. Reports the execution status (e.g., `success`, `failure`) back to Akasa Backend. | N/A | The command is picked up by the daemon and executed. |
| 3    | N/A | Receives execution result from the daemon. | N/A | N/A | Sends a Telegram message to the user: "Gemini CLI task 123 completed successfully." (or an appropriate failure message). | User receives a timely notification of the Gemini CLI task's outcome. |

### 5.2. Scenario: AI Agent Task Timeout Detection and Alerting

*   **Description:** An AI agent task is initiated but fails to report progress or completion within a predefined timeout period, triggering a critical alert to the user.
*   **Preconditions:**
    *   Akasa backend is running and connected to Redis.
    *   The AI agent is configured to report its status to Redis using keys like `akasa:agent_status:{agent_id}`.
    *   The background timeout observer task is active and configured with a timeout threshold of 15 minutes.
*   **Examples:**

| Step | System Action (AI Agent) | Redis Action | Background Timeout Observer Action | Telegram Notification | Expected Outcome |
|------|--------------------------|--------------|----------------------------------|-----------------------|------------------|
| 1    | Initiates a complex analysis task. Reports its status as "starting" along with a current timestamp to Redis. | Stores a status record: `{ "agent_id": "ai-analyst-001", "status": "starting", "timestamp": "2026-03-14T10:00:00Z" }` in `akasa:agent_status:ai-analyst-001`. | N/A | N/A | The AI agent's initial status is successfully recorded. |
| 2    | Fails to report any further status updates or completion notifications within the next 15 minutes (e.g., due to a server crash or an unhandled error). | N/A | At 2026-03-14T10:15:00Z, the observer checks `akasa:agent_status:ai-analyst-001`. It detects that the task has remained in the "starting" state since 10:00:00Z, exceeding the 15-minute threshold. It triggers an alert generation process. | Sends a Telegram message to the user: "CRITICAL ALERT: AI Agent 'ai-analyst-001' has timed out. Please investigate its status." | The user receives an immediate critical alert about the stalled AI agent. |

### 5.3. Scenario: Command Expiration Due to Stale Queue Entry

*   **Description:** A command is successfully enqueued by a user via Telegram but is never picked up by the Local Tool Daemon before its Time-To-Live (TTL) expires.
*   **Preconditions:**
    *   Akasa backend is running and connected to Redis.
    *   The Local Tool Daemon is either offline or experiencing significant delays in its polling cycle, such that its polling interval exceeds the command TTL.
    *   The command TTL is configured to 5 minutes (300 seconds).
*   **Examples:**

| Step | User Action (Telegram) | Akasa Backend Action | Redis Action | Local Tool Daemon Action | Telegram Notification | Expected Outcome |
|------|------------------------|----------------------|--------------|--------------------------|-----------------------|------------------|
| 1    | User sends `/luma run_job --job_id 456` command. | Validates the user and command against the Luma tool's whitelist. | Enqueues a JSON object `{ "user_id": "owner_id", "tool": "luma", "command": "run_job --job_id 456", "ttl": 300 }` to the list `akasa:commands:luma`. | N/A | None | The command is successfully enqueued with an expiration time set. |
| 2    | N/A | N/A | After 5 minutes, Redis automatically purges the command entry from the `akasa:commands:luma` list as its TTL has expired. | N/A (The daemon has not yet polled or is delayed) | N/A | The stale command is automatically removed from the queue, preventing it from being executed later. |
| 3    | N/A | N/A | N/A | The Local Tool Daemon eventually polls the `akasa:commands:luma` list and finds it empty. | N/A | The daemon does not find any commands to execute. The user does not receive a completion notification, implying the action was not performed due to the expiration. |

## 6. Security Considerations

*   **Arbitrary Command Execution:** This risk is mitigated by a strict command whitelist configured within the Akasa system. Only commands explicitly defined as safe and necessary will be permitted for execution.
*   **Unauthorized Access:** Commands can only be initiated by the whitelisted Telegram `user_id` associated with the local development environment, ensuring that only authorized users can control local tools.
*   **Stale Commands:** The implementation of Redis TTL for enqueued commands automatically purges outdated instructions that are not processed within a defined timeframe (defaulting to 5 minutes). This prevents the execution of stale requests that may no longer be relevant or could cause unintended side effects.
*   **Sensitive Data:** The system must ensure that no sensitive information, such as API tokens or credentials, is directly stored within the Redis command queue payload. Any required sensitive data should be managed through secure, external configurations or secrets management systems.

## 7. Future Enhancements

*   **Real-time Communication:** The system could be enhanced by exploring real-time communication protocols like Redis Pub/Sub or WebSockets. This could offer lower latency for command delivery and status updates, providing a more immediate user experience. However, careful consideration must be given to the increased complexity in connection management and potential security implications.
*   **Advanced Agent Status Reporting:** Implementing more granular agent status reporting (e.g., 'running', 'processing_step_X', 'completed', 'failed_with_error_code') would provide richer monitoring capabilities and enable more sophisticated diagnostic alerts.