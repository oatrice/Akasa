# Implementation Plan: IDE Integration for Command Queue

> Refers to: `spec.md`
> Status: Updated after implementation pass

## 1. Design Choices

- Canonical command format: `command` = action name, `args` = structured payload
- Whitelist strategy: backward-compatible hybrid schema
  - tool-level defaults
  - command-level override
- Endpoint strategy: hybrid
  - defaults at tool level
  - override at command level when needed

## 2. Work Breakdown

### Step 1: Whitelist Schema Upgrade
- Add execution metadata (`cli|http|mcp`) in `config/command_whitelist.yaml`
- Keep `allowed_commands` for compatibility with existing validation flow

### Step 2: Command Queue Service Update
- Add raw whitelist cache loader
- Keep old flat whitelist API for compatibility
- Enhance `get_command_whitelist_entry()` to return merged execution config + allowed args

### Step 3: Local Daemon Refactor
- Add protocol dispatch by `execution.type`
- Implement CLI handler:
  - positional/flag arg styles
  - path validation against `allowed_paths`
- Implement HTTP handler:
  - localhost host allowlist
  - timeout/retries/backoff/retry statuses
- Implement MCP handler (stdio JSON-RPC):
  - initialize + tools/call flow
  - timeout/retries/backoff

### Step 4: Observability & Traceability
- Mark status `picked_up` and `running` before execution
- On TTL expiry, mark command `expired`
- If result reporting fails, fallback to direct Redis status update
- Send duration as `duration_seconds`

### Step 5: Tests
- Update daemon tests for:
  - success/failure/expired flows
  - duration_seconds payload
  - path + line/column acceptance
- Update whitelist service tests for merged execution defaults behavior

## 3. Verification Checklist

- [ ] Unit tests pass in project runtime environment
- [x] Python syntax check passes for modified files
- [x] Config and docs aligned with implementation direction
- [x] TTL-expired command has explicit trace path (`expired`)

## 4. Follow-up

- Run full test suite in env that has project dependencies (`fastapi`, `pydantic_settings`, etc.)
- Add dedicated HTTP/MCP unit tests for retry behavior edge cases
