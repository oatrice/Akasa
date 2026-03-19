# Task: Luma CLI — Telegram Notification

- [x] Investigate Luma CLI missing Telegram notification
- [x] Create implementation plan
- [x] Implement with TDD
  - [x] 🟥 RED: Write failing tests (`tests/test_notifier.py`) — 5 tests
  - [x] 🟢 GREEN: Implement `luma_core/notifier.py`
  - [x] ✨ REFACTOR: Centralize config via `luma_core.config`
  - [x] Modify `luma_core/config.py` — add AKASA env vars
  - [x] Modify `main.py` — wrap 8 actions with `run_with_notify`
  - [x] Modify `.env.example` — add AKASA vars
- [x] Verify all tests pass (5/5 ✅)
- [ ] Ensure Luma `.env` has AKASA vars set
