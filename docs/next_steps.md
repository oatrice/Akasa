# 🔮 Next Steps — Akasa Project Planning

**Last Updated:** 2026-03-14
**Session:** Issue #33/#34 implementation + code review fixes + CI stabilization

---

## 📊 Current Progress Snapshot

| Phase | Done | Todo | Total | % |
|---|---|---|---|---|
| Phase 1 — Foundation | 4 | 1 | 5 | 80% |
| Phase 2 — Chat Experience | 5 | 2 | 7 | 71% |
| Phase 3 — Remote Dev Core | 4 | 0 | 4 | 100% ✅ |
| Phase 4 — Orchestration & Build | 7 | 0 | 7 | 100% ✅ |
| Phase 5 — Mobile Visual | 0 | 2 | 2 | 0% |
| Phase 6 — Scale & Cross-Platform | 0 | 7 | 7 | 0% |
| **Total** | **20** | **12** | **32** | **63%** |

**Key milestone:** Phases 3 and 4 are fully complete — the entire async deployment + notification pipeline is operational.

---

## ✅ Completed This Session

| Issue | What Was Done |
|---|---|
| #33 | `deploy_service.py` — BackgroundTasks + Redis state, `asyncio.create_subprocess_exec` + shlex security fix |
| #34 | `send_deployment_notification()` — Telegram inline keyboard URL button, success/failure formatting |
| CI fix | `conftest.py` autouse fixture — `tg_service.client` closed by lifespan no longer breaks subsequent tests |
| Warnings fix | `MagicMock` replaces `AsyncMock` for sync `raise_for_status()` — 44 RuntimeWarnings eliminated |
| Luma CLI | `action_update_roadmap` patched to accept comma-separated issue numbers (`"33, 34"`) |
| ROADMAP.md | Sync'd with GitHub: #33 #34 #53 #61 marked ✅, #37 added to Phase 6, Progress Summary table added |
| Docs | `implementation_notes.md`, `celery_vs_backgroundtasks.md`, `python_mocking_pitfalls.md` updated |

---

## 🔮 Recommended Issues — Priority Order

### 🥇 #37 — Unified User Session & Multi-Platform Context Sync

**GitHub:** https://github.com/oatrice/Akasa/issues/37
**Phase:** 6
**Labels:** enhancement, service

**Why first:**
The project now has deep per-project context (Redis), multi-IDE integration (Zed, Antigravity), and a full notification pipeline. But the context is siloed — Telegram chat knows what project you're on, but the IDE doesn't, and vice versa. This issue is the **glue** that binds everything built in Phases 3–4 into a coherent cross-platform experience.

**What it involves:**
- Unified User ID: link Telegram `user_id` to a `developer_profile` identifier (could be machine hostname + Telegram ID)
- Update Redis schema: store `current_project` under a global user key, not just `chat_id`
- New Sync API endpoint: `GET /api/v1/session` and `PATCH /api/v1/session` — lets macOS tools read/write active project
- macOS CLI reads from Sync API on startup to set current context

**Dependencies:** None — builds on existing Redis schema and API patterns.

**Estimated scope:** Medium. New endpoint + Redis schema migration + small CLI change.

---

### 🥈 #35 + #36 — Mobile Screenshot Service + Remote UI Control

**GitHub:** https://github.com/oatrice/Akasa/issues/35, /36
**Phase:** 5
**Labels:** enhancement, mobile

**Why second:**
These are the most **unique** features in the roadmap — no comparable tool chains screenshot capture directly into a developer chat bot. The deployment service (#33/#34) is now live; the natural completion is "deploy → get screenshot → verify UI without touching your device."

**Issue #35 — ADB & Simctl Screenshot Service:**
- New `app/services/mobile_service.py`
- Android: `adb exec-out screencap -p` → bytes → Telegram `sendPhoto`
- iOS: `xcrun simctl io booted screenshot /tmp/screen.png` → Telegram `sendPhoto`
- Expose as chat command `/screenshot` or MCP tool `take_screenshot`

**Issue #36 — Remote UI Control:**
- Map chat commands (e.g., `/tap 200 400`, `/swipe up`) to `adb shell input tap x y`
- Optional: integrate Maestro CLI (`maestro test flow.yaml`) as an MCP tool
- Allows full manual-verify loop from Telegram without touching the device

**Dependency:** Requires Android emulator or connected device for #35 to be testable end-to-end. Can be mocked in unit tests.

**Suggested order:** #35 first (read-only, lower risk), then #36 (writes to device).

---

### 🥉 #5 — Deploy MVP

**GitHub:** https://github.com/oatrice/Akasa/issues/5
**Phase:** 1 (long overdue)

**Why third:**
This is a Phase 1 issue that has been deferred since the beginning. Everything runs on `localhost:8000` — the Telegram webhook, the MCP server, Luma CI. Without a real deployment:
- The bot only works when your laptop is on
- The Luma CI pipeline cannot reach the backend from GitHub Actions
- Ngrok sessions expire and break the webhook

**What it involves:**
- Deploy FastAPI app to Railway or Render (free tier sufficient)
- Set all env vars (`TELEGRAM_BOT_TOKEN`, `REDIS_URL`, `AKASA_API_KEY`, `AKASA_CHAT_ID`, etc.)
- Register the real domain as the Telegram webhook: `POST https://api.telegram.org/bot{TOKEN}/setWebhook`
- Update `AKASA_API_URL` in Luma CLI and MCP server configs

**Effort:** Low–Medium (1–2 hours). No code changes needed — purely infra and config.

---

### 4️⃣ #10 — Rate Limiting + Error Handling

**GitHub:** https://github.com/oatrice/Akasa/issues/10
**Phase:** 2

**Why fourth:**
Now that Phase 4 is complete (deployment, notifications, action approval), the API surface is much larger than Phase 2. Without rate limiting:
- The `/api/v1/deployments` endpoint can be abused to spawn unlimited subprocesses
- The `/api/v1/actions/request` endpoint can be spammed, flooding Telegram
- The LLM endpoint has no protection against runaway costs

**What it involves:**
- Add `slowapi` (fastapi rate limiter) or a Redis-based token bucket
- Apply different limits per route: e.g., `10/minute` for chat, `2/minute` for deployments
- Improve LLM error responses: distinguish rate-limit (429), credits exhausted, model unavailable
- Add global exception handler to return consistent `{"detail": "..."}` format

**Effort:** Medium. Mostly middleware and error-handling boilerplate.

---

## ⏭️ Defer for Now

| Issue | Reason |
|---|---|
| **#28** Web Dashboard | Requires a full frontend stack (React/Next.js). Significant scope increase — do after core backend is stable and deployed. |
| **#11** GitHub API (read code, review PR) | `GithubService` already exists for basic ops. Deep code-reading requires designing a chunking/context strategy. Good candidate after #37 (session sync provides the context layer it needs). |
| **#12** Code Sandbox | Requires sandboxing infrastructure (Docker, Firecracker, or a managed sandbox API). Security-critical. Not worth rushing. |
| **#15** WhatsApp | Requires Meta Business API approval and a verified phone number. External dependency with long lead time. |
| **#9** LINE Bot | Low priority given Telegram is fully featured. LINE API is similar to Telegram but with a separate webhook. |
| **#14** Analytics | Nice-to-have. Can be approximated with Redis counters for now. |
| **#16** Custom instructions per user | Good UX improvement but not blocking anything. Implement after #37 (user profile infrastructure). |

---

## 🧭 Decision Framework

When choosing the next issue, ask:

1. **Does it make existing features more useful?**
   → Prefer integration/glue issues (#37) over greenfield features.

2. **Does it unblock other issues?**
   → #37 unblocks #16 (custom instructions need a user profile). #5 unblocks CI/CD.

3. **Is it a unique differentiator?**
   → #35/#36 (mobile screenshot + control) are not available in any comparable tool.

4. **Is it a production risk?**
   → #5 (deploy) and #10 (rate limiting) reduce risk before expanding scope.

5. **Does it require external dependencies or approvals?**
   → Deprioritize anything blocked by Meta (#15), hardware (#35 needs a device), or significant frontend scope (#28).

---

## 🗓️ Suggested Sprint Order

```
Sprint 1:  #37  — Unified User Session (ties existing features together)
Sprint 2:  #5   — Deploy MVP to production (unblocks everything)
Sprint 3:  #35  — Mobile Screenshot Service (read-only, low risk)
Sprint 4:  #36  — Remote UI Control (builds on #35)
Sprint 5:  #10  — Rate Limiting + Error Handling (production hardening)
Backlog:   #11, #16, #28, #12, #14, #9, #15
```

---

## 📎 Related Documents

- [`docs/ROADMAP.md`](./ROADMAP.md) — full issue list with statuses
- [`docs/technical_notes/celery_vs_backgroundtasks.md`](./technical_notes/celery_vs_backgroundtasks.md) — deployment architecture trade-offs
- [`docs/features/18_.../implementation_notes.md`](./features/18_issue-33-34_service-async-deployment-service-for-web-backend-feature-post-build-notification-system-with-url-verification/implementation_notes.md) — #33/#34 implementation details