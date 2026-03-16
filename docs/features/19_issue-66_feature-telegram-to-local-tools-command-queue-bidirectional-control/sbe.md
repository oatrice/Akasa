# SBE: Telegram → Local Tools Command Queue (Bidirectional Control)

> 📖 Scenario-Based Examples สำหรับ Feature #66
> ใช้สำหรับกำหนด acceptance criteria แบบ concrete examples

---

## 📌 Feature Information

| รายการ | รายละเอียด |
|--------|-----------|
| **Feature Name** | Telegram → Local Tools Command Queue (Bidirectional Control) |
| **Issue URL** | [#66](https://github.com/oatrice/Akasa/issues/66) |
| **Date** | 2025-07-14 |

---

## 🎭 Scenarios

---

### Scenario 1 — Happy Path: Queue a Gemini CLI task from Telegram

**Context:** Developer is away from the desk and wants to start a Gemini summarization task remotely.

**Given** the user is authenticated (user_id `123456789` is in `ALLOWED_TELEGRAM_USER_IDS`)
**And** the Akasa backend is running at `http://localhost:8000`
**And** the local Gemini daemon is running (`python scripts/local_tool_daemon.py --tool gemini`)
**And** `"run_task"` is in the whitelist for tool `"gemini"`

**When** the user sends the Telegram message:
```
/queue gemini run_task {"task": "summarize_pr", "pr_number": 66}
```

**Then** the bot immediately replies:
```
⏳ Command queued!
ID: cmd_abc123
Tool: gemini
Command: run_task
Expires in: 5 minutes
```

**And** within 2 seconds the daemon picks up the command from Redis
**And** the daemon executes the whitelisted task
**And** the bot sends a follow-up notification:
```
✅ gemini › run_task completed

Output:
PR #66 Summary: Implements bidirectional Telegram → local tools command queue...

Duration: 8.2s
```

---

### Scenario 2 — Happy Path: Queue a Luma issue update from mobile

**Context:** Developer wants to update a Luma issue status from their phone.

**Given** the user is authenticated
**And** the Luma daemon is running
**And** `"update_issue"` is in the whitelist for tool `"luma"`

**When** the user sends:
```
/queue luma update_issue {"issue_id": 42, "status": "done"}
```

**Then** the bot replies:
```
⏳ Command queued!
ID: cmd_def456
Tool: luma
Command: update_issue
Expires in: 5 minutes
```

**And** the daemon executes the update
**And** the bot notifies:
```
✅ luma › update_issue completed

Issue #42 marked as done.
Duration: 1.3s
```

---

### Scenario 3 — Happy Path: Open a file in Zed IDE remotely

**Context:** Developer is reviewing code via Telegram and wants to open a specific file in their local Zed IDE.

**Given** the user is authenticated
**And** the Zed daemon is running
**And** `"open_file"` is in the whitelist for tool `"zed"`

**When** the user sends:
```
/queue zed open_file {"path": "app/services/command_queue_service.py"}
```

**Then** the bot replies:
```
⏳ Command queued!
ID: cmd_ghi789
Tool: zed
Command: open_file
```

**And** Zed IDE opens the file on the developer's local machine
**And** the bot notifies:
```
✅ zed › open_file completed

Opened: app/services/command_queue_service.py
```

---

### Scenario 4 — Non-whitelisted Command Rejected

**Context:** User attempts to run a command not on the approved whitelist.

**Given** the user is authenticated
**And** `"delete_branch"` is NOT in the whitelist for tool `"gemini"`

**When** the user sends:
```
/queue gemini delete_branch {"branch": "main"}
```

**Then** the bot replies immediately:
```
❌ Command not allowed

'delete_branch' is not in the approved command list for gemini.

Allowed commands:
• run_task
• list_issues
• summarize_session
• check_status
```

**And** nothing is pushed to Redis
**And** the API returns HTTP 400 with body:
```json
{
  "error": "command_not_whitelisted",
  "message": "Command 'delete_branch' is not in the whitelist for tool 'gemini'",
  "allowed_commands": ["run_task", "list_issues", "summarize_session", "check_status"]
}
```

---

### Scenario 5 — Unauthorized User Rejected

**Context:** An unknown Telegram user ID tries to queue a command.

**Given** user_id `999999999` is NOT in `ALLOWED_TELEGRAM_USER_IDS`

**When** user `999999999` sends:
```
/queue gemini list_issues
```

**Then** the bot replies:
```
🚫 Unauthorized

You are not authorized to queue commands.
```

**And** the API returns HTTP 403:
```json
{
  "error": "unauthorized_user",
  "message": "User ID 999999999 is not authorized to queue commands"
}
```

**And** nothing is pushed to Redis
**And** the attempt is logged for audit purposes

---

### Scenario 6 — Command Expires Before Daemon Picks It Up

**Context:** Developer queues a command but the local daemon is offline; command expires after TTL.

**Given** the user is authenticated
**And** the Gemini daemon is NOT running
**And** TTL is set to 300 seconds (5 minutes)

**When** the user sends:
```
/queue gemini run_task {"task": "summarize_pr", "pr_number": 66}
```

**Then** the bot confirms the queue:
```
⏳ Command queued!
ID: cmd_jkl012
Expires in: 5 minutes
```

**And** 5 minutes pass with no daemon pickup
**And** the Redis TTL expires, removing the meta key

**When** the daemon eventually comes online and calls BRPOP
**Then** the daemon finds the payload in the queue
**But** the daemon checks the meta key `akasa:commands:gemini:meta:cmd_jkl012` and finds it missing (expired)
**And** the daemon skips execution with log entry:
```
[SKIP] cmd_jkl012 — TTL expired (meta key not found)
```

**And** the user receives a Telegram notification:
```
⏰ Command expired

cmd_jkl012 (gemini › run_task) was not executed — it expired after 5 minutes.
Queue your command again when the daemon is ready.
```

---

### Scenario 7 — Command Execution Fails (Non-zero exit code)

**Context:** The daemon picks up a valid command, but the tool execution fails.

**Given** the daemon is running
**And** the command is valid and not expired

**When** the Gemini CLI exits with a non-zero exit code:
```
Error: OpenRouter credits exhausted. Please top up your account.
```

**Then** the daemon captures the stderr/stdout
**And** reports failure to `POST /api/v1/notifications/task-complete`
**And** the bot notifies:
```
❌ gemini › run_task failed

Error:
OpenRouter credits exhausted. Please top up your account.

Exit code: 1
Duration: 2.1s
```

---

### Scenario 8 — Redis Unavailable at Enqueue Time

**Context:** The Akasa backend cannot reach Redis when trying to enqueue a command.

**Given** Redis is down or unreachable

**When** the user sends a `/queue` command via Telegram

**Then** the bot replies:
```
⚠️ Service temporarily unavailable

Could not queue your command — please try again in a moment.
```

**And** the API returns HTTP 503:
```json
{
  "error": "redis_unavailable",
  "message": "Could not connect to the command queue. Please try again shortly."
}
```

**And** no crash or unhandled exception occurs in the backend

---

### Scenario 9 — Multiple Commands Queued (FIFO Order)

**Context:** Developer queues three Luma commands in quick succession.

**Given** all three commands are whitelisted
**And** the Luma daemon is running

**When** the user sends:
```
/queue luma list_issues
/queue luma update_issue {"issue_id": 10, "status": "in_progress"}
/queue luma update_issue {"issue_id": 11, "status": "done"}
```

**Then** each command is queued immediately in order
**And** the daemon processes them sequentially (FIFO — BRPOP from tail of list)
**And** each result notification arrives in order:

```
✅ luma › list_issues completed — 5 open issues found
✅ luma › update_issue completed — Issue #10 marked in_progress
✅ luma › update_issue completed — Issue #11 marked done
```

---

### Scenario 10 — Rate Limit Exceeded

**Context:** A user tries to flood the queue with too many commands.

**Given** the rate limit is 10 commands per user per minute

**When** the user sends 11 `/queue` commands within 60 seconds

**Then** the first 10 are accepted normally
**And** on the 11th command, the bot replies:
```
🚦 Rate limit reached

You've sent too many commands. Please wait before queueing more.
Limit: 10 commands per minute
```

**And** the API returns HTTP 429:
```json
{
  "error": "rate_limit_exceeded",
  "message": "Command rate limit reached. Max 10 commands per minute.",
  "retry_after_seconds": 42
}
```

---

## 📊 Scenario Summary

| # | Scenario | Expected Outcome | AC |
|---|----------|------------------|----|
| 1 | Valid Gemini task queued + executed | ✅ Notification with result | AC1, AC3, AC4, AC6 |
| 2 | Valid Luma update queued + executed | ✅ Notification with result | AC1, AC3, AC4 |
| 3 | Valid Zed open file | ✅ File opened + notification | AC1, AC3, AC4 |
| 4 | Non-whitelisted command | ❌ 400 rejected | AC2 |
| 5 | Unauthorized user | 🚫 403 rejected | AC3 |
| 6 | Command expires (daemon offline) | ⏰ Skip + expiry notification | AC5 |
| 7 | Command fails (non-zero exit) | ❌ Failure notification | AC6 |
| 8 | Redis unavailable | ⚠️ 503 graceful error | AC1 |
| 9 | Multiple commands — FIFO order | ✅ Processed in order | AC4 |
| 10 | Rate limit exceeded | 🚦 429 rejected | AC7 |

---

## 🔐 Security Scenarios

### Scenario S1 — Injection Attempt via Args

**Given** the whitelist only allows `"run_task"` for Gemini
**When** the user sends:
```
/queue gemini run_task {"task": "; rm -rf /"}
```
**Then** the args are validated against the Pydantic schema for `run_task`
**And** the `task` field only accepts values from an allowed enum (`["summarize_pr", "review_branch", "check_status"]`)
**And** the command is rejected with 400 — malicious string never reaches subprocess

---

### Scenario S2 — Tampered Command ID (Result Spoofing)

**Given** the daemon reports a result via `POST /api/v1/commands/{command_id}/result`
**When** an attacker sends a spoofed result with a forged `command_id`
**Then** the endpoint requires `X-Daemon-Secret` header matching `AKASA_DAEMON_SECRET`
**And** unauthenticated result reports return HTTP 401
**And** no notification is sent to Telegram

---

*SBE version: 1.0 — 2025*