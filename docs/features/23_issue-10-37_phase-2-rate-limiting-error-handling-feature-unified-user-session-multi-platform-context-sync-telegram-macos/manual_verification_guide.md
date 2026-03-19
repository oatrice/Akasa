# Manual Verification Guide

This guide is aligned to feature 23:
- incremental cross-platform `active_project` sync between Telegram and macOS/local tools,
- inbound Telegram message rate limiting,
- friendly LLM error handling.

It follows the product contract in
[spec.md](/Users/oatrice/Software-projects/Akasa/docs/features/23_issue-10-37_phase-2-rate-limiting-error-handling-feature-unified-user-session-multi-platform-context-sync-telegram-macos/spec.md)
and the implementation flow in
[plan.md](/Users/oatrice/Software-projects/Akasa/docs/features/23_issue-10-37_phase-2-rate-limiting-error-handling-feature-unified-user-session-multi-platform-context-sync-telegram-macos/plan.md).

## Preconditions

- Backend is running, for example at `http://127.0.0.1:8000`
- Redis is running and reachable
- Telegram bot is connected to the owner chat used by Akasa
- `AKASA_API_KEY`, `AKASA_CHAT_ID`, and Telegram settings are configured
- If you want to verify local queued commands too, the local daemon is running

Example local variables:

```bash
export BASE_URL=http://127.0.0.1:8000
export AKASA_KEY='YOUR_AKASA_API_KEY'
```

## 1. Verify Initial Shared Project State

### Step 1
Read the current local sync state from macOS:

```bash
curl -H "X-Akasa-API-Key: $AKASA_KEY" \
  "$BASE_URL/api/v1/context/project"
```

### Expected Result
- The API returns `200`
- The response includes `active_project`
- If nothing has been changed yet, the value is typically `default`

### Step 2
In Telegram, send:

```text
/project
```

### Expected Result
- Telegram shows the same current project name as the API returned
- The usage text includes `/project select <name>` and `/project status [name]`

## 2. Verify Telegram -> macOS Context Sync

### Step 1
In Telegram, switch project:

```text
/project select akasa
```

### Expected Result
- Akasa confirms the project switch

### Step 2
Read the sync API again from macOS:

```bash
curl -H "X-Akasa-API-Key: $AKASA_KEY" \
  "$BASE_URL/api/v1/context/project"
```

### Expected Result
- The API returns `200`
- The response is:

```json
{
  "active_project": "akasa"
}
```

## 3. Verify macOS -> Telegram Context Sync

### Step 1
Update the shared project from macOS:

```bash
curl -X PUT \
  -H "X-Akasa-API-Key: $AKASA_KEY" \
  -H "Content-Type: application/json" \
  -d '{"active_project":"release-notes"}' \
  "$BASE_URL/api/v1/context/project"
```

### Expected Result
- The API returns `200`
- The response echoes:

```json
{
  "active_project": "release-notes"
}
```

### Step 2
In Telegram, send:

```text
/project
```

### Expected Result
- Telegram now shows `release-notes` as the current project

## 4. Verify API Auth and Validation

### Step 1
Call the context API without the API key:

```bash
curl -i "$BASE_URL/api/v1/context/project"
```

### Expected Result
- The API returns `401`

### Step 2
Call the update API with an empty project:

```bash
curl -i -X PUT \
  -H "X-Akasa-API-Key: $AKASA_KEY" \
  -H "Content-Type: application/json" \
  -d '{"active_project":"   "}' \
  "$BASE_URL/api/v1/context/project"
```

### Expected Result
- The API returns `422`
- The request is rejected before any state change

## 5. Verify Telegram Inbound Rate Limiting

### Step 1
Send more than the configured number of Telegram messages in the active rate window

Default config in this repo:
- `TELEGRAM_MESSAGE_RATE_LIMIT=5`
- `TELEGRAM_MESSAGE_RATE_WINDOW_SECONDS=60`

### Expected Result
- Akasa sends a friendly slow-down message
- The blocked message is not processed by the LLM
- The conversation remains intact after the rate window expires

## 6. Verify Friendly LLM Failure Handling

### Step 1
Temporarily force an upstream failure on the Telegram chat LLM path in local development

Examples:
- use an invalid OpenRouter API key,
- point the provider base URL to an invalid endpoint,
- or simulate timeout/failure via local configuration if available

### Step 2
Send a normal non-command chat message in Telegram

### Expected Result
- Akasa replies with a friendly fallback message
- The user does not see a raw traceback
- The fallback fits one of these categories:
  - timeout
  - temporary upstream failure
  - malformed response
  - insufficient credits / invalid provider setup

### Step 3
Restore healthy configuration and send another normal chat message

### Expected Result
- Normal LLM replies resume without requiring project re-linking

## 7. Verify Telegram Project Status Views

### Step 1
In Telegram, save a note:

```text
/note Continue feature 23 verification
```

### Step 2
Check detailed status:

```text
/project status
/projects overview
```

### Expected Result
- `/project status` shows the current task note
- `/projects overview` shows the active project and recent activity summary
- The active project shown there matches the shared `active_project` from the sync API

## 8. Optional Repo-Specific Extension: Bound Project Path

This is a repo extension beyond the original v1 spec contract. Use it if you also want to verify the newer project-path support.

### Step 1
Bind a path from Telegram:

```text
/project bind akasa /Users/oatrice/Software-projects/Akasa
```

### Expected Result
- Akasa confirms the bind

### Step 2
Read the path from Telegram:

```text
/project path akasa
```

### Expected Result
- Akasa shows the bound folder path

### Step 3
Read the API from macOS:

```bash
curl -H "X-Akasa-API-Key: $AKASA_KEY" \
  "$BASE_URL/api/v1/context/project"
```

### Expected Result
- If the current project is `akasa`, the response may include:

```json
{
  "active_project": "akasa",
  "project_path": "/Users/oatrice/Software-projects/Akasa"
}
```

## 9. Supporting Diagnostics: Queue and Gemini CLI

This section is not the core feature 23 contract, but it is useful when local queued commands are part of your test environment.

### Step 1
Keep the daemon terminal open

### Step 2
Enqueue a command from Telegram or macOS:

```text
/queue gemini check_status {"model":"flash"}
```

### Expected Result
- The daemon prints `DEQUEUED cmd_xxx`
- The log includes:
  - `queued_at`
  - `dequeued_at`
  - `queue_wait_ms`
- After execution, the daemon prints `COMPLETED cmd_xxx`
- That log includes:
  - `status`
  - `exit_code`
  - `run_duration_ms`
  - `total_latency_ms`

### Step 3
If you want to verify Gemini model fallback, run:

```text
/queue gemini check_status {"model":"pro","fallback_model":"flash"}
```

### Expected Result
- If the primary model is quota-limited, the daemon retries with the fallback model
- Telegram shows a readable summary rather than only a raw quota error

## Notes

- Some automated tests still emit environment warnings because this workspace currently uses Python 3.9 and `google.generativeai`.
- Gemini CLI may print extra operational lines such as cached credential or MCP refresh logs. Those lines are CLI noise, not necessarily failures.
