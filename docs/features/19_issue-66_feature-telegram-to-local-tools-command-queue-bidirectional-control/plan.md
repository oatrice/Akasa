# 📋 Implementation Plan

> Feature: Telegram → Local Tools Command Queue (Bidirectional Control)
> Issue: [#66](https://github.com/oatrice/Akasa/issues/66)

---

## 🎯 Objective

สร้างระบบ bidirectional control ระหว่าง Telegram กับ local development tools (Luma, Gemini CLI, Antigravity/Zed IDE) ผ่าน Redis-backed command queue ให้ผู้ใช้สามารถ trigger actions ใน local tools จาก Telegram ได้

---

## 📐 Architecture Overview

```
[Telegram User]
     │  /queue <tool> <command>
     ▼
[Akasa Backend (FastAPI)]
     │  enqueue + validate
     ▼
[Redis Command Queue]
     │  BRPOP (blocking poll)
     │  key: akasa:commands:{tool_name}
     ▼
[Local Tool Daemon] (scripts/local_tool_daemon.py)
     │  execute whitelisted command
     ▼
[Akasa Backend — POST /api/v1/notifications/task-complete]
     │  report result
     ▼
[Telegram User] ← ✅/❌ result notification
```

---

## 🗂️ Phase Breakdown

### Phase 1 — Redis Queue Service (Backend)

**Estimated: 2 days**

#### 1.1 Redis Schema Design

```
Key format : akasa:commands:{tool_name}   (Redis List)
Item format : JSON string

{
  "command_id": "uuid4",
  "tool": "gemini" | "luma" | "zed",
  "command": "list_issues",          # whitelisted command key
  "args": {...},                     # optional structured args
  "user_id": 123456789,              # Telegram user_id
  "queued_at": "2025-01-01T00:00:00Z",
  "ttl_seconds": 300
}
```

**TTL strategy:** Use Redis `EXPIRE` on a companion key `akasa:commands:{tool}:meta:{command_id}` to track expiry. Daemon checks meta key before executing — if missing (expired), skip.

#### 1.2 Create `app/services/command_queue_service.py`

| Method | Description |
|--------|-------------|
| `enqueue_command(tool, command, args, user_id)` | Push command to Redis list + set TTL meta key |
| `dequeue_command(tool, timeout)` | BRPOP with timeout, return parsed payload |
| `mark_command_expired(command_id)` | Delete meta key to signal expiry |
| `get_pending_count(tool)` | LLEN for queue monitoring |

#### 1.3 Command Whitelist Config

File: `app/config/command_whitelist.py`

```python
COMMAND_WHITELIST = {
    "gemini": ["list_issues", "summarize_session", "run_task"],
    "luma": ["list_issues", "update_issue", "create_issue"],
    "zed": ["open_file", "run_task", "show_notification"],
}
```

---

### Phase 2 — FastAPI Endpoint + Telegram Command

**Estimated: 1 day**

#### 2.1 New API Route: `POST /api/v1/commands`

File: `app/api/v1/commands.py`

**Request body:**
```json
{
  "tool": "gemini",
  "command": "list_issues",
  "args": {},
  "user_id": 123456789
}
```

**Response:**
```json
{
  "command_id": "uuid4",
  "status": "queued",
  "tool": "gemini",
  "expires_in": 300
}
```

**Validation:**
- `tool` must be in whitelist keys
- `command` must be in `COMMAND_WHITELIST[tool]`
- `user_id` must match authenticated owner

#### 2.2 Telegram Bot Command Handler

Parse `/queue <tool> <command> [args...]` in the existing Telegram webhook handler.

```
/queue gemini list_issues
/queue luma update_issue 42 done
/queue zed open_file src/main.py
```

Handler calls `POST /api/v1/commands` internally via `CommandQueueService`.

---

### Phase 3 — Local Tool Daemon

**Estimated: 2 days**

#### 3.1 Create `scripts/local_tool_daemon.py`

**Core loop:**
1. Connect to Redis (URL from env)
2. BRPOP `akasa:commands:{tool}` with 5s timeout
3. Parse payload, check TTL meta key (skip if expired)
4. Validate command against local whitelist
5. Execute via subprocess or direct function call
6. POST result to `http://localhost:8000/api/v1/notifications/task-complete`
7. Loop

**Example execution map:**
```python
EXECUTORS = {
    "gemini": {
        "list_issues": lambda args: run_gh_cli(["issue", "list"]),
        "summarize_session": lambda args: call_gemini_summary(args),
    },
    "luma": {
        "list_issues": lambda args: run_luma_cli(["issue", "list"]),
    },
    "zed": {
        "open_file": lambda args: open_in_zed(args["path"]),
    },
}
```

#### 3.2 Daemon Startup Script

```bash
# scripts/start_daemon.sh
#!/bin/bash
source venv/bin/activate
python scripts/local_tool_daemon.py --tool gemini &
python scripts/local_tool_daemon.py --tool luma &
```

#### 3.3 Daemon Configuration (`.env` additions)

```
DAEMON_TOOL=gemini          # which tool this daemon handles
DAEMON_POLL_TIMEOUT=5       # BRPOP timeout seconds
DAEMON_API_BASE=http://localhost:8000
DAEMON_API_KEY=<internal_key>
```

---

### Phase 4 — Security Hardening

**Estimated: 2 days**

#### 4.1 User Authorization

- Maintain `ALLOWED_TELEGRAM_USER_IDS` in `.env` (comma-separated)
- FastAPI dependency: check `user_id` against allowed list before enqueuing
- Reject with 403 if not in whitelist

#### 4.2 Command Injection Prevention

- Never pass raw string args to `shell=True`
- Use `subprocess.run([...], shell=False)` with pre-validated arg lists
- Structured `args` schema per command (Pydantic models)

#### 4.3 Rate Limiting

- Max 10 commands per user per minute (Redis counter + TTL)
- Return 429 if exceeded

#### 4.4 Audit Logging

- Log every command enqueue/execute/expire/reject to structured log
- Include: `command_id`, `tool`, `command`, `user_id`, `timestamp`, `outcome`

---

### Phase 5 — Tests

**Estimated: 2 days**

#### 5.1 Unit Tests

| Test File | Coverage |
|-----------|---------|
| `tests/test_command_queue_service.py` | enqueue, dequeue, TTL expiry, whitelist validation |
| `tests/test_commands_api.py` | FastAPI endpoint — happy path, unauthorized, invalid command |
| `tests/test_local_daemon.py` | daemon loop logic, executor map, result reporting |

#### 5.2 Integration Tests

| Scenario | Expected Result |
|----------|----------------|
| Valid command queued + daemon picks up | Result notification sent to Telegram |
| Command TTL expires before pickup | Daemon skips, no execution, log entry |
| Unauthorized user_id | 403 response, nothing enqueued |
| Non-whitelisted command | 422 response |
| Redis unavailable | 503 + graceful error handling |

---

### Phase 6 — Docs & Roadmap

**Estimated: 1 day**

- [ ] Update `docs/ROADMAP.md` — add #66 to Phase 4
- [ ] Create `docs/features/19_.../spec.md`
- [ ] Create `docs/features/19_.../analysis.md`
- [ ] Create `docs/features/19_.../sbe.md`
- [ ] Add daemon setup instructions to `README.md`

---

## 📁 New Files Summary

```
app/
├── api/v1/
│   └── commands.py                    # NEW: FastAPI router
├── services/
│   └── command_queue_service.py       # NEW: Redis queue operations
├── config/
│   └── command_whitelist.py           # NEW: Whitelist config
└── models/
    └── command.py                     # NEW: Pydantic models for commands

scripts/
├── local_tool_daemon.py               # NEW: Polling daemon
└── start_daemon.sh                    # NEW: Startup convenience script

tests/
├── test_command_queue_service.py      # NEW
├── test_commands_api.py               # NEW
└── test_local_daemon.py               # NEW

docs/features/19_issue-66_.../
├── plan.md           ← this file
├── analysis.md
├── spec.md
├── sbe.md
└── ai_brain/
    └── session_analysis.md
```

---

## ⏱️ Timeline

| Phase | Task | Days | Status |
|-------|------|------|--------|
| 1 | Redis Queue Service | 2 | 🔲 Todo |
| 2 | FastAPI Endpoint + Telegram | 1 | 🔲 Todo |
| 3 | Local Tool Daemon | 2 | 🔲 Todo |
| 4 | Security Hardening | 2 | 🔲 Todo |
| 5 | Tests | 2 | 🔲 Todo |
| 6 | Docs & Roadmap | 1 | 🔲 Todo |
| **Total** | | **10 days** | |

---

## 🔗 Dependencies

| Dependency | Reason |
|------------|--------|
| Redis (already in stack) | Command queue storage |
| `redis-py` (already installed) | Python Redis client |
| `subprocess` (stdlib) | Local command execution |
| FastAPI `Depends` | Auth middleware |
| Pydantic v2 | Command payload validation |

---

## ✅ Definition of Done

- [ ] All 6 phases implemented
- [ ] All new tests pass (unit + integration)
- [ ] Security review completed
- [ ] No arbitrary shell commands possible
- [ ] Daemon can be started and stopped cleanly
- [ ] Telegram `/queue` command working end-to-end
- [ ] Result notification arrives in Telegram within 10 seconds
- [ ] ROADMAP.md updated