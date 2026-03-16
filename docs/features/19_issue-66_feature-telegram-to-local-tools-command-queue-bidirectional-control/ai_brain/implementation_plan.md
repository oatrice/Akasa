# Feature #66 — Telegram → Local Tools Command Queue (ส่วนที่เหลือ)

## Current State

Phase 1 (Redis Queue Service) **เสร็จแล้ว** — มีไฟล์เหล่านี้พร้อมใช้งาน:

| File | Status |
|------|--------|
| `app/services/command_queue_service.py` | ✅ Complete (enqueue, dequeue, rate limit, whitelist, status mgmt) |
| `app/models/command.py` | ✅ Complete (all Pydantic models) |
| `app/config.py` | ✅ Settings added (daemon secret, TTL, rate limit, allowed user IDs) |
| `config/command_whitelist.yaml` | ✅ Complete (gemini, luma, zed tools) |

---

## Proposed Changes

### Phase 2: FastAPI Commands Router + Telegram Handler (✅ เสร็จแล้ว)

#### [NEW] [commands.py](file:///Users/oatrice/Software-projects/Akasa/app/routers/commands.py)

สร้าง router ใหม่สำหรับ command queue API (เสร็จแล้ว):
- `POST /api/v1/commands` — Enqueue command (validate user_id, whitelist, rate limit → call `enqueue_command()`)
- `GET /api/v1/commands/{command_id}` — Get command status
- `POST /api/v1/commands/{command_id}/result` — Daemon reports result (validate `X-Daemon-Secret` header)
  - Update status → send Telegram notification with result

Security:
- Enqueue: `verify_api_key` dependency (reuse from notifications router)
- Result: `X-Daemon-Secret` header validation

---

#### [MODIFY] [main.py](file:///Users/oatrice/Software-projects/Akasa/app/main.py)

Import และ include `commands.router` ที่ `prefix="/api/v1"` (เสร็จแล้ว)

---

#### [MODIFY] [chat_service.py](file:///Users/oatrice/Software-projects/Akasa/app/services/chat_service.py)

เพิ่ม `/queue` command handler ใน `_handle_command()` (เสร็จแล้ว):
- Parse `/queue <tool> <command> [args_json]`
- Validate user → call `enqueue_command()` → reply ด้วย ⏳ confirmation message
- Handle errors: whitelist rejection, rate limit, Redis unavailable

---

### Phase 3: Local Tool Daemon

#### [NEW] [local_tool_daemon.py](file:///Users/oatrice/Software-projects/Akasa/scripts/local_tool_daemon.py)

Standalone Python script สำหรับ poll Redis queue:
1. BRPOP from `akasa:commands:{tool}` with timeout
2. Check meta key (TTL sentinel) — skip if expired
3. Execute whitelisted command via subprocess (shell=False)
4. POST result to `/api/v1/commands/{id}/result`
5. Audit log all activity

> [!IMPORTANT]
> Daemon เป็น **Phase 3** ซึ่งยังไม่จำเป็นต้อง implement ใน sprint นี้ได้
> สามารถ focus ที่ Phase 2 (API + Telegram) ก่อน แล้วค่อยทำ Daemon ทีหลัง

---

### Phase 5: Tests (TDD — Red → Green → Refactor)

#### [NEW] [test_command_queue_service.py](file:///Users/oatrice/Software-projects/Akasa/tests/services/test_command_queue_service.py)

Unit tests สำหรับ `CommandQueueService`:
- Whitelist loading + validation
- `enqueue_command()` success / whitelist rejection / unknown tool
- `dequeue_command()` success / timeout
- `check_rate_limit()` within limit / exceeded
- `is_meta_key_alive()` exists / expired
- `update_command_status()` various transitions
- `mark_command_expired()`

#### [NEW] [test_commands.py](file:///Users/oatrice/Software-projects/Akasa/tests/routers/test_commands.py)

Router tests สำหรับ `/api/v1/commands` (✅ เสร็จแล้ว):
- POST /commands — happy path, whitelist rejection (400), unauthorized (401), rate limit (429), Redis down (503)
- GET /commands/{id} — found / not found (404)
- POST /commands/{id}/result — success, invalid daemon secret (401), unknown command_id

---

## User Review Required

> [!IMPORTANT]
> **เลือก scope**: ต้องการให้ implement ทุก Phase (2-6) ใน session นี้ หรือ implement เฉพาะ Phase 2 + 5 (API + Tests) ก่อน แล้วค่อยทำ Daemon ทีหลัง?

> [!WARNING]
> Phase 3 (Local Daemon) ต้องรันเป็น standalone process บน macOS — ต้องตั้ง env vars เพิ่ม (AKASA_DAEMON_SECRET, REDIS_URL) ควรทดสอบ end-to-end แยกจาก unit tests

---

## Verification Plan

### Automated Tests

```bash
# Run all existing tests first to ensure no regressions
cd /Users/oatrice/Software-projects/Akasa
python3 -m pytest tests/ -v

# Run new command queue service tests
python3 -m pytest tests/services/test_command_queue_service.py -v

# Run new commands router tests
python3 -m pytest tests/routers/test_commands.py -v
```

### Manual Verification

1. **Telegram `/queue` command** — ส่ง `/queue gemini run_task {"task": "summarize_pr"}` ใน Telegram → ดูว่ามี ⏳ confirmation กลับมา
2. **Whitelist rejection** — ส่ง `/queue gemini delete_all {}` → ดูว่ามีข้อความ ❌ rejection
3. **API endpoint** — `curl -X POST http://localhost:8000/api/v1/commands -H "X-Akasa-API-Key: ..." -d '{"tool":"gemini","command":"run_task"}'`
