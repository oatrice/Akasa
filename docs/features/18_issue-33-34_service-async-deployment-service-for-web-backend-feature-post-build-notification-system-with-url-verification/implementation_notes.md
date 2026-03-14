# Implementation Notes — Issue #33 & #34
# Async Deployment Service + Post-Build Notification System

**Date:** 2026-03-14
**Status:** ✅ Complete
**Branch:** `feat/33-34-async-deploy-service`

---

## 1. What Was Built

### New Files

| File | Purpose |
|---|---|
| `app/models/deployment.py` | Pydantic models: `DeploymentRequest`, `DeploymentRecord`, `DeploymentResponse`, `DeploymentStatusResponse` |
| `app/services/deploy_service.py` | Core async logic: create, save, get deployment + `run_deployment()` background task |
| `app/routers/deployments.py` | FastAPI router: `POST /api/v1/deployments` (202), `GET /api/v1/deployments/{id}` |
| `tests/services/test_deploy_service.py` | 47 unit tests for service layer |
| `tests/routers/test_deployments.py` | 20 router-level tests |
| `tests/services/test_telegram_service_deployment.py` | 34 tests for `send_deployment_notification` |

### Modified Files

| File | Change |
|---|---|
| `app/main.py` | Register `deployments.router` under `/api/v1` |
| `app/services/telegram_service.py` | Add `send_deployment_notification()` method |

---

## 2. API Contracts

### `POST /api/v1/deployments`

**Request:**
```json
{
  "command": "vercel deploy --prod",
  "cwd": "/home/user/my-app",
  "project": "MyApp",
  "chat_id": "123456789"
}
```

**Response — 202 Accepted:**
```json
{
  "deployment_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending"
}
```

- `chat_id` is optional — falls back to `settings.AKASA_CHAT_ID` for Telegram notification
- Returns immediately; actual deployment runs in `BackgroundTasks`

### `GET /api/v1/deployments/{deployment_id}`

**Response — 200 OK (terminal state):**
```json
{
  "deployment_id": "550e8400-...",
  "status": "success",
  "url": "https://my-app.vercel.app",
  "stdout": "Deployed to https://my-app.vercel.app\n",
  "stderr": "",
  "exit_code": 0,
  "started_at": "2026-03-14T10:00:00+00:00",
  "finished_at": "2026-03-14T10:01:30+00:00"
}
```

**Status lifecycle:** `pending` → `running` → `success` | `failed`

---

## 3. Security Fix (from Code Review)

**Vulnerability:** Original implementation used `asyncio.create_subprocess_shell()` with a raw user-provided command string — a classic command injection risk.

```python
# ❌ Before (vulnerable)
proc = await asyncio.create_subprocess_shell(
    record.command,   # user input passed directly to shell
    ...
)

# ✅ After (safe)
import shlex
command_parts = shlex.split(record.command)
proc = await asyncio.create_subprocess_exec(
    *command_parts,   # args parsed safely, no shell invoked
    ...
)
```

**Why this matters:**
- `create_subprocess_shell` passes the string to `/bin/sh -c`, which interprets metacharacters like `;`, `&&`, `|`, `$(...)`
- An attacker could send `"vercel deploy; rm -rf /tmp/secrets"` and both commands would execute
- `create_subprocess_exec` does **not** invoke a shell — metacharacters are treated as literal arguments
- `shlex.split` handles quoted strings correctly (e.g., `'echo "hello world"'` → `["echo", "hello world"]`)

**Tests added:** `TestCommandInjectionPrevention` class (11 tests) verifying:
- `shlex.split` behaviour for `;`, `&&`, `|`
- `create_subprocess_exec` is called, not `create_subprocess_shell`
- Args are passed as a list, not a raw string
- Quoted paths with spaces parsed correctly

---

## 4. Issue #34 — Telegram Notification Flow

When `run_deployment()` completes (success or failure), it calls `_notify_deployment()` callback, which calls `tg_service.send_deployment_notification()`.

### Message Format

**Success with URL:**
```
✅ Deployment Succeeded!

Project: MyApp
Command: `vercel deploy --prod`
Duration: 1m 30s
URL: https://my-app.vercel.app

[🔗 Open Deployment]  ← inline keyboard URL button
```

**Failure:**
```
❌ Deployment Failed!

Project: MyApp
Command: `vercel deploy --prod`
Duration: 12s
Error: Error: authentication required. Run `vercel login`.
```

### Key Design Decisions for Notification

- **URL button type**: Uses `{"url": "..."}` (opens browser directly) — NOT `callback_data` (which would ping the server again)
- **URL in text AND button**: URL appears as `*URL:*` line in message body AND as the button, so it's accessible even if the button disappears after inline keyboard update
- **stderr truncated to 200 chars**: Shows the tail of stderr (most relevant) to fit Telegram message limits
- **Duration computed from timestamps**: `finished_at - started_at` formatted as `Xs` or `Xm Ys`
- **No button when no URL**: If the deploy output contains no HTTPS URL, message is sent without `reply_markup`

### URL Extraction Regex

```python
re.search(r"https://[^\s\"'<>\)\]]+", text)
```

Handles output from Vercel CLI, Render CLI, Railway, Netlify, and custom deploy scripts.
Trailing punctuation (`.`, `,`, `;`, `:`) is stripped to avoid broken URLs.

---

## 5. Design Decision: BackgroundTasks vs Celery

The `plan.md` originally specified **Celery** for the task queue. We implemented **FastAPI BackgroundTasks** instead.

| Concern | BackgroundTasks | Celery |
|---|---|---|
| Setup complexity | Zero (built-in) | Requires broker + worker process |
| Task persistence | ❌ Lost on worker crash | ✅ Survives crashes |
| Retry mechanism | ❌ Manual only | ✅ Built-in with backoff |
| Monitoring | ❌ None | ✅ Flower dashboard |
| Scale workers independently | ❌ | ✅ |
| Current scale suitability | ✅ Sufficient | Overkill for now |

**Decision rationale:** BackgroundTasks is sufficient at current scale (few developers, infrequent deploys). The Redis-backed `DeploymentRecord` provides visibility into task state even without Celery. The main risk is **orphaned deployments**: if the FastAPI worker crashes mid-deploy, `status` stays `"running"` in Redis indefinitely.

**Mitigation (future):** Add a sweep job that marks deployments stuck in `"running"` for >N minutes as `"failed"`. Migrate to Celery if concurrent deployments or retry requirements increase.

**`plan.md` status:** Plan reflects the Celery design and has not been updated. It documents the intended long-term architecture. `analysis.md` already noted BackgroundTasks as sufficient for normal load.

---

## 6. Test Coverage Summary

### `test_deploy_service.py` — 47 tests across 5 classes

| Class | What it tests |
|---|---|
| `TestExtractUrl` | URL parsing edge cases (trailing chars, none found, multiple) |
| `TestRedisRoundTrip` | save/get deployment, TTL, corrupt JSON |
| `TestCreateDeployment` | record initialisation, unique IDs, Redis persistence |
| `TestRunDeployment` | subprocess execution, stdout capture, URL extraction, callbacks, transitions |
| `TestCommandInjectionPrevention` | security: shlex.split behaviour, exec vs shell, injection scenarios |

### `test_deployments.py` — 20 tests across 2 classes

| Class | What it tests |
|---|---|
| `TestStartDeployment` | 202 response, arg forwarding, auth (401/422), background task registration |
| `TestGetDeploymentStatus` | 200/404/401, field completeness per lifecycle state |

### `test_telegram_service_deployment.py` — 34 tests

| Group | What it tests |
|---|---|
| Success path | ✅ emoji, title, project, command in message |
| URL button | Present/absent based on `url`, `url` key (not `callback_data`), URL in text + button |
| Failure path | ❌ emoji, title, stderr preview (truncated), no button when no URL |
| Duration | Seconds, minutes+seconds, missing timestamps, only one timestamp, 0s |
| Payload contract | MarkdownV2, chat_id, endpoint URL, timeout set |
| Error propagation | 4xx, 429, network error all propagate |
| Sanity | ✅ message has no ❌, ❌ message has no "Succeeded" |

### `test_deploy_service.py` — additional classes

| Class | What it tests |
|---|---|
| `TestExtractUrlRealWorldCLI` | Vercel, Render, Railway, Netlify real output patterns; port, hash, query, parens |
| `TestStatusTransitions` | Transition order (running→success/failed), timestamp ordering, stdout/URL timing, Redis save count |

---

## 7. Known Limitations

1. **No timeout on subprocess**: A deployment command that hangs forever will block the background task indefinitely. Consider adding `asyncio.wait_for(proc.communicate(), timeout=N)`.

2. **No retry**: If the deploy command fails transiently (e.g., network blip), there is no automatic retry. The caller must re-POST to start a new deployment.

3. **Orphaned deployments**: See §5. If the worker dies, `status = "running"` stays in Redis for 24 hours until TTL expires.

4. **Single URL extraction**: Only the first HTTPS URL is extracted from output. Vercel sometimes outputs both an inspect URL and a production URL — the inspect URL is returned, not the production one. A future improvement could prefer URLs matching known patterns (e.g., `.vercel.app` over `vercel.com/team/...`).

5. **`plan.md` not updated**: The plan still describes the Celery architecture. Update it if BackgroundTasks is confirmed as the long-term approach.