# Feature #66 — Telegram → Local Tools Command Queue

## Analysis
- [x] อ่าน feature docs (analysis, plan, spec, sbe, session_analysis)
- [x] สำรวจ codebase ปัจจุบัน
- [x] ประเมิน progress — ดูว่ามีอะไร implement ไปแล้ว

## Phase 1 — Redis Queue Service ✅ (เสร็จแล้ว)
- [x] `app/services/command_queue_service.py` — enqueue, dequeue, TTL, rate limit, whitelist
- [x] `app/models/command.py` — Pydantic models
- [x] `app/config.py` — Feature #66 settings
- [x] `config/command_whitelist.yaml` — whitelist config

## Phase 2 — FastAPI Endpoint + Telegram Command
- [x] `app/routers/commands.py` — POST /api/v1/commands, GET /api/v1/commands/{id}, POST /api/v1/commands/{id}/result
- [x] Register router ใน `app/main.py`
- [x] `/queue` command handler ใน `app/services/chat_service.py`

## Phase 3 — Local Tool Daemon
- [x] `scripts/local_tool_daemon.py` — polling loop + whitelist check + execute + report result

## Phase 4 — Telegram Refactoring & Escaping
  - [x] Refactor `TelegramService.send_message`
    - [x] Fix MarkdownV2 escaping logic (Red -> Green)
    - [x] Implement generic `send_message` helper
  - [x] Address MarkdownV2 Escaping Issues
    - [x] Fix missing escaping in `commands.py`
    - [x] Fix over-escaping (`\.`, `\!`) in services
    - [x] Fix backslash and backtick escaping inside code blocks (HTTP 400 Bad Request error)
  - [x] Fix Newline Characters (`\n` vs `\\n`)

## Phase 5 — Security Hardening
- [x] User authorization (validate user_id)
- [x] Daemon secret header validation
- [x] Rate limiting (integrated ใน command_queue_service แล้ว)

## Phase 6 — Tests (TDD)
- [x] Unit tests: `tests/services/test_command_queue_service.py` (32 passed)
- [x] Router tests: `tests/routers/test_commands.py`
- [x] Daemon tests: `tests/scripts/test_local_tool_daemon.py`

## Phase 7 — Docs & Cleanup
- [x] Update feature docs ตามสถานะจริง
- [x] Update plan.md status
