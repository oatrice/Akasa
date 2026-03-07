# Task: Telegram Bot Webhook [Phase 1]

- [x] Fix parse error in `analysis.md` mermaid diagram
- [x] 🟥 RED: Create failing tests for Telegram Webhook (4 tests, all fail with 404)
- [x] 🟢 GREEN: Implement Configuration and Models
- [x] 🟢 GREEN: Implement Telegram Webhook router logic
- [x] ✨ REFACTOR: Tests cleaned up, code structure finalized
- [x] Update `.env.example`

## Code Review Fixes
- [x] Review #1 (OpenRouter): tests มีอยู่แล้วทั้ง 3 ข้อ ✅
  - [x] Missing API key → ValueError
  - [x] Server error 500/503 → HTTPError
  - [x] Malformed response JSON
- [x] Review #3 (Telegram Webhook): เพิ่ม 3 test cases + fix code ✅
  - [x] Malformed payload → 422
  - [x] Empty Secret Token bypass prevention
  - [x] Alternative update types (edited_message)
