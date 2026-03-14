# Analysis: Telegram → Local Tools Command Queue (Bidirectional Control)

> 📋 การวิเคราะห์ก่อนเริ่มพัฒนา Feature #66

---

## 📌 Feature Information

| รายการ | รายละเอียด |
|--------|-----------|
| **Feature Name** | Telegram → Local Tools Command Queue (Bidirectional Control) |
| **Issue URL** | [#66](https://github.com/oatrice/Akasa/issues/66) |
| **Date** | 2025-07-14 |
| **Analyst** | Claude Sonnet 4.6 (via Zed AI) |
| **Priority** | 🟡 Medium |
| **Status** | 📝 Draft |

---

## 1. Requirement Analysis

### 1.1 Problem Statement

```
The current Akasa system supports one-way communication: AI assistants notify users via Telegram and
request action confirmations (Allow/Deny). However, there is no mechanism for the user to initiate
commands from Telegram that execute on the local machine — in tools like Luma CLI, Gemini CLI, or
Zed (Antigravity) IDE. This gap prevents true bidirectional remote-development workflows.

The session "Manual Verification of Akasa MCP Notifications" surfaced this need when exploring how
Telegram could trigger local IDE/CLI actions after the MCP notification system was verified working.
```

### 1.2 User Stories

| # | As a | I want to | So that |
|---|------|-----------|---------|
| 1 | Developer | send a command from Telegram to trigger a Gemini CLI task | I can start AI work on my local machine while away from the desk |
| 2 | Developer | queue a Luma action from my phone | I don't need to open my laptop just to kick off a known workflow |
| 3 | Developer | receive the result of the queued command back in Telegram | I have a complete feedback loop without switching contexts |
| 4 | Developer | trust that only pre-approved commands can execute | No arbitrary code execution is possible even if Telegram is compromised |
| 5 | Developer | have stale/unprocessed commands auto-expire | Queued commands from hours ago don't accidentally execute later |

### 1.3 Acceptance Criteria

- [ ] **AC1:** A new Telegram command (e.g., `/queue <tool> <command>`) enqueues a command for a specific local tool
- [ ] **AC2:** Akasa backend stores the command in Redis with TTL, target tool, and requesting user_id
- [ ] **AC3:** A lightweight local polling daemon fetches and executes pending commands from the queue
- [ ] **AC4:** Only commands on a per-tool whitelist are permitted to execute
- [ ] **AC5:** Execution result/status is reported back to the user via Telegram notification
- [ ] **AC6:** Commands expire via Redis TTL (default: 5 minutes) if not consumed by the local daemon
- [ ] **AC7:** Only the authenticated owner's Telegram user_id may enqueue commands
- [ ] **AC8:** The daemon logs all activity (command received, executed, result) for audit purposes

---

## 2. Feature Analysis

### 2.1 User Flow

```mermaid
flowchart TD
    A[User sends /queue command via Telegram] --> B{Akasa Backend}
    B --> C[Validate user_id & command against whitelist]
    C -->|Invalid| D[Reply: Unauthorized or Unknown command]
    C -->|Valid| E[LPUSH to Redis: akasa:commands:{tool}]
    E --> F[Set TTL on queued item — default 5 min]
    E --> G[Respond to Telegram: Command queued ✅]
    H[Local Tool Daemon — polling loop] --> I{BRPOP from Redis queue}
    I -->|No item / TTL expired| H
    I -->|Item received| J[Validate command against local whitelist]
    J -->|Blocked| K[Log rejected command, notify Telegram]
    J -->|Allowed| L[Execute whitelisted command]
    L --> M{Execution Result}
    M -->|Success| N[POST /api/v1/notifications/task-complete]
    M -->|Failure| O[POST /api/v1/notifications/task-complete with error]
    N --> P[Telegram: ✅ Command completed — result shown]
    O --> Q[Telegram: ❌ Command failed — error shown]
```

### 2.2 System Architecture

```
[Telegram User]
     │  /queue gemini "summarize PR #123"
     ▼
[Akasa Backend — FastAPI]
     │  validate + enqueue
     ▼
[Redis List: akasa:commands:gemini]   ← TTL per item
     │  BRPOP (blocking pop, poll)
     ▼
[Local Daemon: scripts/local_tool_daemon.py]
     │  match against WHITELIST
     ▼
[Local Tool: Gemini CLI / Luma / Antigravity]
     │  stdout/stderr captured
     ▼
[Akasa Backend — POST /notifications/task-complete]
     │
     ▼
[Telegram: result notification]
```

### 2.3 Redis Schema

| Key Pattern | Type | TTL | Description |
|-------------|------|-----|-------------|
| `akasa:commands:{tool_name}` | List | Per item (set at enqueue) | Queue of pending commands per tool |
| `akasa:cmd_result:{correlation_id}` | Hash | 10 min | Stores execution result for retrieval |
| `akasa:cmd_whitelist:{tool_name}` | Set | None | Approved commands for the tool |

**Queue item payload (JSON string):**
```json
{
  "correlation_id": "uuid4",
  "user_id": 123456789,
  "tool": "gemini",
  "command": "summarize PR #123",
  "enqueued_at": "2025-07-14T10:00:00Z",
  "ttl_seconds": 300
}
```

### 2.4 Component Map

| Component | Path | Responsibility |
|-----------|------|---------------|
| Command Queue Service | `app/services/command_queue_service.py` | LPUSH / BRPOP operations, TTL management |
| Commands API Router | `app/api/v1/commands.py` | `POST /api/v1/commands` — enqueue endpoint |
| Telegram Command Handler | `app/services/chat_service.py` | Parse `/queue` command, call Commands API |
| Local Tool Daemon | `scripts/local_tool_daemon.py` | Polling loop, whitelist check, exec, report |
| Whitelist Config | `scripts/command_whitelist.yaml` | Per-tool approved command patterns |

---

## 3. Impact Analysis

### 3.1 Affected Components

| Component | Impact Level | Description |
|-----------|--------------|-------------|
| `chat_service.py` | 🟡 Medium | Add `/queue` command parsing and routing |
| Redis | 🟡 Medium | New key patterns for command queue |
| New: `command_queue_service.py` | 🔴 High | Core new service — enqueue/dequeue logic |
| New: `commands.py` router | 🟡 Medium | New FastAPI endpoint |
| New: `local_tool_daemon.py` | 🔴 High | New standalone daemon process |
| Notification service | 🟢 Low | Reuse existing task-complete notification flow |
| Tests | 🟡 Medium | New unit + integration tests required |

### 3.2 Breaking Changes

- [ ] **None expected** — this is a net-new feature using new Redis keys and new endpoints

### 3.3 Backward Compatibility

```
No existing endpoints or Redis keys are modified. The /queue Telegram command is new and does not
conflict with existing commands. The daemon is a separate process that does not affect the main
FastAPI application lifecycle.
```

---

## 4. Feasibility Analysis

### 4.1 Technical Feasibility

| คำถาม | คำตอบ | หมายเหตุ |
|-------|-------|----------|
| เทคโนโลยีรองรับหรือไม่? | ✅ | Redis Lists + BRPOP is a proven queue pattern |
| ทีมมี Skills เพียงพอหรือไม่? | ✅ | Team already uses Redis, FastAPI, Telegram bot |
| Infrastructure รองรับหรือไม่? | ✅ | Redis already deployed; daemon runs locally |
| Local daemon feasible on macOS? | ✅ | Simple Python script; can run as launchd service or bg process |

### 4.2 Transport Option Comparison

| Option | Pros | Cons | Recommendation |
|--------|------|------|---------------|
| **Redis List (BRPOP)** | Simple, reliable, TTL support, no persistent connection | Polling interval adds slight latency | ✅ **Recommended** |
| Redis Pub/Sub | Real-time, no latency | No persistence, messages lost if daemon offline | Future upgrade path |
| WebSocket/SSE | Real-time, bidirectional | Requires open port on local machine (security risk) | ❌ Not recommended |

### 4.3 Time Feasibility

| ประเด็น | รายละเอียด |
|--------|-----------|
| **Estimated Effort** | ~8 days |
| **Breakdown** | Redis schema + service (2d), FastAPI + Telegram handler (1d), Daemon (2d), Security + tests (2d), Docs (1d) |
| **Feasible?** | ✅ |

---

## 5. Security Analysis

### 5.1 Sensitive Data

| ข้อมูล | Sensitivity Level | Protection Method |
|--------|------------------|-------------------|
| Telegram user_id | 🟡 Sensitive | Validated against `ALLOWED_TELEGRAM_USER_IDS` env var |
| Queued command payloads | 🟡 Sensitive | No credentials/tokens in queue; Redis auth + network ACL |
| Local tool execution | 🔴 Critical | Whitelist-only execution; no shell=True; args as list |
| Execution output/results | 🟡 Sensitive | Avoid leaking secrets in output; sanitize before Telegram |

### 5.2 Attack Vectors

| Vector | Risk Level | Mitigation |
|--------|-----------|------------|
| Arbitrary command injection via Telegram | 🔴 High | Strict whitelist — only exact pre-approved commands match |
| Unauthorized user enqueuing commands | 🔴 High | Validate Telegram user_id at API layer before enqueue |
| Stale command execution (replay) | 🟡 Medium | Redis TTL per item; daemon checks `enqueued_at` freshness |
| Redis queue poisoning | 🟡 Medium | Redis password + bind to 127.0.0.1; TLS if remote |
| Output exfiltration via Telegram | 🟢 Low | Sanitize stdout before forwarding; length-limit responses |

### 5.3 Whitelist Design

```yaml
# scripts/command_whitelist.yaml
tools:
  gemini:
    allowed_patterns:
      - "summarize PR #*"
      - "review branch *"
      - "run tests"
  luma:
    allowed_patterns:
      - "update roadmap *"
      - "list issues"
  antigravity:
    allowed_patterns:
      - "open project *"
      - "run diagnostics"
```

---

## 6. Performance & Scalability

### 6.1 Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Enqueue latency (API → Redis) | < 50ms | Simple LPUSH operation |
| Daemon poll interval | 1–2 seconds | BRPOP with timeout |
| Command pickup latency | < 2 seconds | From enqueue to daemon pickup |
| End-to-end (Telegram → result) | < 30 seconds | Depends on command execution time |

### 6.2 Scalability Notes

- Single-user system initially; one daemon per local machine
- Future: multiple tool daemons running in parallel (one per tool type)
- Redis List naturally supports multiple consumers if needed (worker pool pattern)

---

## 7. Gap Analysis

| ด้าน | As-Is | To-Be | Gap |
|------|-------|-------|-----|
| Telegram → Local | ❌ Not possible | ✅ Via Redis queue | Full implementation required |
| Command security | N/A | Whitelist + user auth | Whitelist config + validation logic |
| Local execution feedback | N/A | Async result via Telegram | Result reporting pipeline |
| Daemon lifecycle | N/A | macOS background process | launchd plist or manual startup script |

---

## 8. Risk Analysis

| Risk | Probability | Impact | Score | Mitigation |
|------|-------------|--------|-------|------------|
| Whitelist bypass via crafted input | 🟡 Medium | 🔴 High | 6 | Exact-match or safe regex patterns only; no shell interpretation |
| Daemon not running (commands queue up) | 🟡 Medium | 🟡 Medium | 4 | TTL auto-expires; Telegram warns if queue grows stale |
| Redis unavailable | 🟢 Low | 🟡 Medium | 2 | Graceful error response to Telegram; existing Redis HA mitigates |
| Output too large for Telegram | 🟢 Low | 🟢 Low | 1 | Truncate output; offer file attachment for long results |

> **Risk Score:** Probability × Impact (High=3, Medium=2, Low=1)

---

## 9. Session Context (Source Analysis)

> This feature was identified and scoped during the session:
> **"Manual Verification of Akasa MCP Notifications"**

### Key Findings from Session

| Topic | Decision |
|-------|----------|
| Transport mechanism | Redis List (BRPOP) preferred over WebSocket/SSE for security |
| Zed/Gemini startup timing | Daemon should be independent of IDE/MCP initialization |
| Security model | Whitelist + user_id auth + TTL is minimum viable security |
| Feedback loop | Reuse existing `/api/v1/notifications/task-complete` for results |
| Real-time upgrade | Redis Pub/Sub is a viable future upgrade for < 1s latency |

### Related Fixes Completed in Same Session

| Issue | Fix |
|-------|-----|
| MCP initialization timeout (Zed) | Fixed path resolution + stdin handling |
| Telegram inline keyboard stale after Allow/Deny | Fixed callback flow to update/remove keyboard |
| Log overwriting | Fixed to append mode with PID prefix |
| #33 Async Deployment Service | ✅ Implemented |
| #34 Post-Build Notification | ✅ Implemented |

---

## 10. Summary & Recommendations

### 10.1 Summary

| หมวด | Status | Key Findings |
|------|--------|--------------|
| Requirement | ✅ Clear | Bidirectional control is well-understood from session analysis |
| Architecture | ✅ Decided | Redis List (poll-based) is safe and proven |
| Security | ⚠️ Critical | Whitelist design and user_id auth are non-negotiable before ship |
| Feasibility | ✅ Feasible | All technology already in stack; ~8 days effort |
| Risk | ⚠️ Medium | Whitelist bypass is primary concern; mitigated by design |

### 10.2 Recommendations

1. **Start with whitelist config design** — define the initial allowed commands for each tool before writing any code
2. **Implement daemon as a standalone script** — keep it decoupled from the FastAPI app for reliability and independent restarts
3. **Reuse existing notification endpoint** — avoid creating a new result-reporting channel; `POST /api/v1/notifications/task-complete` is sufficient
4. **Add `--dry-run` mode to daemon** — useful for testing whitelist matching without actual execution
5. **Plan for launchd/systemd integration** — document how to auto-start the daemon on macOS login

### 10.3 Next Steps

- [ ] Finalize `command_whitelist.yaml` schema and initial entries for Gemini, Luma, Antigravity
- [ ] Design Redis key schema and TTL strategy
- [ ] Implement `command_queue_service.py` with enqueue/dequeue/TTL operations
- [ ] Add `POST /api/v1/commands` endpoint with user_id validation
- [ ] Implement `/queue` Telegram command parsing in `chat_service.py`
- [ ] Build `scripts/local_tool_daemon.py` with polling loop and whitelist enforcement
- [ ] Write unit tests for queue service + whitelist matching
- [ ] Write integration test: Telegram command → Redis → daemon → notification
- [ ] Document daemon startup procedure for macOS (launchd plist)

---

## 📎 Appendix

### Related Issues

| Issue | Title | Status |
|-------|-------|--------|
| [#66](https://github.com/oatrice/Akasa/issues/66) | Telegram → Local Tools Command Queue (Bidirectional Control) | 🔲 Open |
| [#61](https://github.com/oatrice/Akasa/issues/61) | Task Completion Notification for AI Assistants (MCP) | ✅ Closed |
| [#58](https://github.com/oatrice/Akasa/issues/58) | Antigravity IDE Action Confirmation via Akasa Bot | ✅ Closed |
| [#49](https://github.com/oatrice/Akasa/issues/49) | Remote Action Confirmation via Akasa Bot | ✅ Closed |
| [#34](https://github.com/oatrice/Akasa/issues/34) | Post-Build Notification System with URL Verification | ✅ Closed |
| [#33](https://github.com/oatrice/Akasa/issues/33) | Async Deployment Service for Web & Backend | ✅ Closed |

### Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Analyst | Claude Sonnet 4.6 | 2025-07-14 | ✅ |
| Tech Lead | — | — | ⬜ |
| PM | — | — | ⬜ |