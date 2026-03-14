# SBE: Telegram to Local Tools Bidirectional Command Control & AI Agent Timeout Observer

> 📅 Created: 2026-03-14
> 🔗 Issue: https://github.com/oatrice/Akasa/issues/66

---

## Feature: Telegram to Local Tools Bidirectional Command Control & AI Agent Timeout Observer

This feature enables users to send commands from Telegram to local development tools (e.g., Luma, Gemini CLI, Zed IDE) via a Redis-backed command queue, allowing for bidirectional control. Local tool daemons poll the queue, execute whitelisted commands, and report results back to Telegram. Additionally, a timeout observer monitors AI Agent tasks, alerting users via Telegram if an agent fails to report completion within a specified timeframe.

### Scenario: Happy Path - Successful Local Tool Command Execution

**Given** an authenticated Telegram user (`user_id: 12345`), a running `gemini-cli` local tool daemon, and `gemini-cli:run_tests` is a whitelisted command
**When** the user sends the Telegram command `/akasa gemini-cli run_tests --project my_app`
**Then** the Akasa backend enqueues the command to `akasa:commands:gemini-cli` with a 5-minute TTL, the `gemini-cli` daemon picks up and executes `run_tests --project my_app`, and the execution result `Tests passed for my_app.` is reported back to the user via Telegram

#### Examples

| telegram_command | tool_target | command_payload | expected_telegram_notification |
|-------------------------------------|-------------|-----------------------------------|-----------------------------------------------------------------|
| `/akasa luma generate_image --prompt "cat"` | `luma` | `generate_image --prompt "cat"` | `Luma: Image generation started. ID: abc123def` |
| `/akasa gemini-cli deploy --env staging` | `gemini-cli` | `deploy --env staging` | `Gemini CLI: Deployment to staging initiated. Status: SUCCESS` |
| `/akasa antigravity open_file --path /src/main.py` | `antigravity` | `open_file --path /src/main.py` | `Antigravity: Opened /src/main.py in Zed IDE.` |
| `/akasa luma analyze_code --repo akasa` | `luma` | `analyze_code --repo akasa` | `Luma: Code analysis for Akasa repository complete. Found 0 critical issues.` |

### Scenario: Edge Case - Command Expiration Due to Inactivity

**Given** an authenticated Telegram user (`user_id: 67890`), a command `luma:generate_report` is whitelisted, and the `luma` local tool daemon is currently offline
**When** the user sends the Telegram command `/akasa luma generate_report`, and 5 minutes pass without the command being picked up by the `luma` daemon
**Then** the command is automatically removed from the `akasa:commands:luma` Redis queue by its TTL, and no execution occurs

#### Examples

| telegram_command | tool_target | command_payload | time_elapsed_minutes | expected_redis_queue_state |
|-------------------------------------|-------------|---------------------------------|----------------------|--------------------------------------------|
| `/akasa gemini-cli build --target release` | `gemini-cli` | `build --target release` | 6 | Command no longer in `akasa:commands:gemini-cli` |
| `/akasa luma optimize_model` | `luma` | `optimize_model` | 5 | Command no longer in `akasa:commands:luma` |
| `/akasa antigravity restart_server` | `antigravity` | `restart_server` | 7 | Command no longer in `akasa:commands:antigravity` |

### Scenario: Error Handling - Invalid Command or Unauthorized Access

**Given** the Akasa backend is running and configured with a command whitelist and authorized user IDs
**When** an unauthorized Telegram user (`user_id: 99999`) sends the command `/akasa luma generate_image --prompt "dog"` OR an authorized user (`user_id: 12345`) sends the command `/akasa luma unknown_command`
**Then** the command is rejected, not enqueued, and an appropriate error message is sent back to the user via Telegram

#### Examples

| telegram_user_id | telegram_command | command_whitelisted | user_authorized | expected_telegram_error |
|------------------|-------------------------------------|---------------------|-----------------|-----------------------------------------------------------------|
| `99999` (unauthorized) | `/akasa luma generate_image` | `true` | `false` | `Error: You are not authorized to use this feature.` |
| `12345` (authorized) | `/akasa luma unknown_command` | `false` | `true` | `Error: Command 'unknown_command' for tool 'luma' is not whitelisted.` |
| `12345` (authorized) | `/akasa non_existent_tool do_something` | `false` | `true` | `Error: Tool 'non_existent_tool' is not recognized or configured.` |
| `99999` (unauthorized) | `/akasa gemini-cli deploy` | `true` | `false` | `Error: You are not authorized to use this feature.` |

### Scenario: AI Agent Timeout Detection and Alert

**Given** an AI Agent (e.g., Antigravity IDE) starts a task and reports its 'starting' status to Redis with a timestamp, and a background task is configured to check for timeouts every 5 minutes with a 15-minute timeout threshold
**When** the AI Agent fails to report completion or any status update, and its 'starting' status in Redis persists for more than 15 minutes
**Then** the background task detects the timeout, updates the task status to 'timed_out', and sends an alert notification `AI Agent 'Antigravity IDE' task 'code_review_pr_123' has timed out after 15 minutes.` to the configured Telegram user

#### Examples

| agent_name | task_id | initial_status_timestamp | current_time | timeout_threshold_minutes | expected_telegram_alert |
|-------------------|--------------------------|--------------------------|--------------------------|---------------------------|-----------------------------------------------------------------------------------------------------------------------------------|
| `Antigravity IDE` | `code_review_pr_123` | `2026-03-14 10:00:00` | `2026-03-14 10:16:00` | `15` | `AI Agent 'Antigravity IDE' task 'code_review_pr_123' has timed out after 15 minutes.` |
| `Luma Agent` | `data_ingestion_job_456` | `2026-03-14 11:30:00` | `2026-03-14 11:47:00` | `15` | `AI Agent 'Luma Agent' task 'data_ingestion_job_456' has timed out after 15 minutes.` |
| `Gemini CLI Agent` | `model_training_789` | `2026-03-14 13:00:00` | `2026-03-14 13:18:00` | `15` | `AI Agent 'Gemini CLI Agent' task 'model_training_789' has timed out after 15 minutes.` |