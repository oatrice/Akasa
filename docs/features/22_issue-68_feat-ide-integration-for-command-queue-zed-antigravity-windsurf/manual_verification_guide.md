# Manual Verification Guide: Issue #68 IDE Integration

## Scope

คู่มือนี้ครอบคลุมการทดสอบ manual สำหรับ execution 3 แบบ:
- CLI (`zed`)
- HTTP (`windsurf`)
- MCP (`antigravity`)

รวมทั้ง lifecycle tracing (`picked_up`, `running`, `success|failed|expired`) และ `duration_seconds` contract.

## Prerequisites

- รัน backend และ Redis ได้
- ตั้งค่า `.env` ให้ครบ (`AKASA_DAEMON_SECRET`, `REDIS_URL`, ฯลฯ)
- รัน daemon:

```bash
python3 scripts/local_tool_daemon.py
```

## A. Zed CLI Path Validation

1. ส่ง command ที่ถูกต้อง (`open_file` + relative path)
```json
{
  "tool": "zed",
  "command": "open_file",
  "args": {"path": "README.md"}
}
```
Expected:
- daemon execute สำเร็จ
- status เป็น `success`
- result มี `duration_seconds`

2. ส่ง command ที่เป็น line/column
```json
{
  "tool": "zed",
  "command": "open_file",
  "args": {"path": "docs/features/22_issue-68_feat-ide-integration-for-command-queue-zed-antigravity-windsurf/spec.md:10:5"}
}
```
Expected:
- ผ่าน validation
- execute สำเร็จ

3. ส่ง command path traversal
```json
{
  "tool": "zed",
  "command": "open_file",
  "args": {"path": "../../etc/passwd"}
}
```
Expected:
- ถูก reject
- status เป็น `failed`
- output อธิบายว่า path อยู่นอก `allowed_paths`

## B. Windsurf HTTP Retry + Host Guard

1. รัน mock server local ที่ตอบ 503 ครั้งแรก และ 200 ครั้งถัดไป
2. ส่ง command `windsurf.execute_code`
Expected:
- daemon retry ตาม `retries/backoff`
- สุดท้าย `success` (ถ้ารอบหลัง 200)

3. แก้ endpoint host เป็น non-localhost แล้วส่ง command
Expected:
- daemon reject ก่อนยิง request
- output ระบุ host ไม่อยู่ใน allowlist

## C. Antigravity MCP

1. ส่ง `antigravity.notify_pending_review`
Expected:
- daemon เรียก MCP (initialize + tools/call)
- ได้ผลลัพธ์กลับและ report `success`

2. เปลี่ยน `server_command` เป็น path ที่ไม่มีจริง แล้วส่ง command
Expected:
- report `failed`
- output ระบุ `MCP server command not found`

## D. TTL Expired Trace

1. enqueue command ด้วย TTL สั้นมาก แล้วรอให้หมดอายุ
2. ให้ daemon dequeue หลัง TTL หมด
Expected:
- command ไม่ถูก execute
- status ถูก mark เป็น `expired`
- มี log ระบุ expired before execution

## E. Result Contract

ตรวจ payload ไปที่ `/api/v1/commands/{id}/result`:
- ต้องมี field `duration_seconds`
- ไม่ใช้ field `duration`

## Suggested Automated Commands

```bash
.venv/bin/python -m pytest
```

หมายเหตุ:
- integration GitHub tests อาจ fail หาก `gh auth` token ไม่ valid หรือไม่มี network
