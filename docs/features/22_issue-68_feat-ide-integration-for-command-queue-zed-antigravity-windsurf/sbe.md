# SBE: IDE Integration for Command Queue

> Created: 2026-03-18
> Issue: #68

## Feature

`local_tool_daemon` ต้อง execute command จาก queue ตาม protocol ที่กำหนดใน whitelist (`cli`, `http`, `mcp`) พร้อม validation, retry, และ traceability.

## Scenario 1: Zed CLI Open File (line/column supported)

**Given** daemon กำลังรัน และ whitelist กำหนด `zed.open_file` แบบ CLI positional
**When** queue ได้รับ payload:
```json
{
  "tool": "zed",
  "command": "open_file",
  "args": {"path": "docs/plan.md:10:5"}
}
```
**Then** daemon รันคำสั่ง `zed docs/plan.md:10:5` และ report `success`

### Examples

| tool | command | args | expected |
|---|---|---|---|
| zed | open_file | `{ "path": "README.md" }` | Execute `zed README.md` |
| zed | open_file | `{ "path": "/Users/oatrice/Software-projects/Akasa/app/main.py" }` | Allowed (inside root) |
| zed | open_file | `{ "path": "../../secret.txt" }` | Rejected (outside allowed root) |

## Scenario 2: Antigravity MCP Tool Call

**Given** whitelist กำหนด `antigravity` เป็น `mcp` ผ่าน `server_command`
**When** queue ได้รับ payload:
```json
{
  "tool": "antigravity",
  "command": "notify_task_complete",
  "args": {"project": "Akasa", "task": "Implement queue", "status": "success"}
}
```
**Then** daemon เรียก MCP JSON-RPC (`initialize` + `tools/call`) และ report ผลลัพธ์

### Examples

| tool | command | args | expected |
|---|---|---|---|
| antigravity | request_remote_approval | `{ "command": "git push", "cwd": "." }` | MCP tools/call success |
| antigravity | notify_pending_review | `{ "project": "Akasa", "task": "Refactor daemon" }` | MCP tools/call success |

## Scenario 3: Windsurf HTTP with Retry

**Given** whitelist กำหนด `windsurf` เป็น HTTP และมี retry policy
**When** queue ได้รับ payload:
```json
{
  "tool": "windsurf",
  "command": "execute_code",
  "args": {"code": "print('hello')"}
}
```
**Then** daemon ส่ง request ไป endpoint local, retry ตาม policy หาก network error/สถานะที่ retry ได้, แล้ว report final status

### Examples

| tool | command | condition | expected |
|---|---|---|---|
| windsurf | execute_code | HTTP 503 ครั้งแรก | retry แล้วสำเร็จ |
| windsurf | open_file | host ไม่ใช่ localhost | reject ก่อนยิง request |

## Scenario 4: TTL Expired Command Trace

**Given** daemon dequeue เจอ command แต่ meta key หมดอายุแล้ว
**When** daemon ตรวจ `akasa:cmd_meta:{command_id}` ไม่พบ
**Then** daemon ไม่ execute และ mark status เป็น `expired` เพื่อ trace ย้อนหลัง

### Examples

| condition | expected |
|---|---|
| meta key missing at dequeue time | status=`expired`, no tool execution |

## Scenario 5: Result Contract

**Given** command execute เสร็จ
**When** daemon รายงานผลกลับ backend
**Then** payload ต้องใช้ `duration_seconds` แทน `duration`

### Examples

| status | payload field |
|---|---|
| success | `{"status":"success","duration_seconds":0.4,...}` |
| failed | `{"status":"failed","duration_seconds":1.2,...}` |
