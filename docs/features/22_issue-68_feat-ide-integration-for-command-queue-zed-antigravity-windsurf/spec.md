# Specification: IDE Integration for Command Queue (Zed, Antigravity, Windsurf)

| Item | Value |
|---|---|
| Feature | IDE Integration for Command Queue |
| Issue | #68 |
| Version | v1.1.0 |
| Date | 2026-03-18 |
| Status | Draft |

## 1. Executive Summary

ขยาย `local_tool_daemon` ให้รองรับการ execute แบบหลายโปรโตคอลผ่าน Command Queue:
- `CLI` สำหรับ Zed/Gemini/Luma
- `HTTP` สำหรับ Windsurf
- `MCP (stdio)` สำหรับ Antigravity

จุดสำคัญคือความปลอดภัย (whitelist + path constraints + localhost-only HTTP), ความยืดหยุ่นของ config, และความสามารถในการ trace สถานะย้อนหลัง.

## 2. Scope

### In Scope
- รองรับ tool execution แบบ `cli`, `http`, `mcp`
- รองรับ `antigravity` ผ่าน MCP เป็นหลัก
- รองรับ `windsurf` ผ่าน HTTP local endpoint
- รองรับ `zed open_file` พร้อม path ที่เป็น:
  - relative path
  - absolute path (เมื่ออยู่ใต้ allowed roots)
  - `file:line` และ `file:line:column`
- Retry policy สำหรับ HTTP/MCP
- Traceability ของ lifecycle (`picked_up`, `running`, `success|failed|expired`)
- แก้ payload result ให้ใช้ `duration_seconds`

### Out of Scope
- MCP transport อื่นนอกจาก `stdio`
- Auto-discovery endpoint จาก IDE
- Distributed daemon orchestration หลายเครื่อง

## 3. Canonical Command Contract

### 3.1 Queue Payload (Backend -> Daemon)
```json
{
  "command_id": "cmd_abc123",
  "tool": "zed",
  "command": "open_file",
  "args": {
    "path": "docs/spec.md:12:5"
  }
}
```

### 3.2 Result Payload (Daemon -> Backend)
```json
{
  "status": "success",
  "output": "...",
  "exit_code": 0,
  "duration_seconds": 0.42
}
```

หมายเหตุ: `duration_seconds` เป็น canonical field (ไม่ใช้ `duration`).

## 4. Whitelist Configuration

ใช้โครงสร้างแบบ hybrid:
- `tools.<tool>.defaults.execution` สำหรับค่ากลางระดับ tool
- `tools.<tool>.allowed_commands[*].execution` สำหรับ override ราย command

ตัวอย่าง:
```yaml
tools:
  zed:
    defaults:
      execution:
        type: cli
        executable: zed
        include_command_name: false
        argument_style: positional
        positional_args: [path]
        path_arg_keys: [path]
        allowed_paths:
          - /Users/oatrice/Software-projects/Akasa
    allowed_commands:
      - name: open_file
        allowed_args: [path]
```

## 5. Execution Semantics

### 5.1 CLI
- ประกอบ command จาก whitelist config
- รองรับ `flags` และ `positional` argument style
- ไม่ใช้ shell execution (`create_subprocess_exec`)

### 5.2 HTTP
- ส่ง request ตาม `method`, `endpoint`, `headers`
- ป้องกัน SSRF ด้วย allowlist host (`localhost`, `127.0.0.1`, `::1`)
- รองรับ retry สำหรับ network error และสถานะที่กำหนด (`retry_statuses`)

### 5.3 MCP
- เริ่ม MCP server ผ่าน `server_command` (stdio)
- ส่ง JSON-RPC: `initialize`, `notifications/initialized`, `tools/call`
- ใช้ command name เป็น MCP tool name โดย default
- รองรับ retry สำหรับ transport/protocol failures

## 6. Security Requirements

- คำสั่งต้องอยู่ใน whitelist เท่านั้น
- args ต้องอยู่ใน `allowed_args`
- สำหรับ path args:
  - รับ relative/absolute/line:col ได้
  - resolve path จริงก่อน validate
  - ต้องอยู่ใต้ `allowed_paths`
- HTTP endpoint ต้องเป็น localhost-only ตาม whitelist

## 7. Reliability and Traceability

- เมื่อ dequeued แล้ว meta key หมดอายุ ต้อง:
  - ไม่ execute
  - mark status เป็น `expired`
  - เก็บ log สำหรับ trace
- ก่อน execute ให้ mark `picked_up` และ `running`
- เมื่อ report result ไป backend ไม่สำเร็จ ให้ fallback update status ตรงใน Redis

## 8. Functional Requirements

- FR-001: รองรับ Zed ผ่าน CLI (`open_file`)
- FR-002: รองรับ Windsurf ผ่าน HTTP
- FR-003: รองรับ Antigravity ผ่าน MCP (`stdio`)
- FR-004: รองรับ retry policy สำหรับ HTTP/MCP
- FR-005: เปลี่ยน result field เป็น `duration_seconds`
- FR-006: TTL-expired command ต้องถูก mark เป็น `expired` เพื่อ trace ภายหลัง

## 9. Definition of Done

- Daemon execute ได้ตาม `execution.type` (`cli|http|mcp`)
- Whitelist schema ใหม่ใช้งานได้และไม่ทำลาย flow เดิม
- Zed path policy รองรับ relative/absolute/line:col ตาม allowed roots
- HTTP/MCP retry ทำงานตาม config
- `duration_seconds` ถูกส่งไป endpoint result
- TTL-expired command ถูก mark และ trace ได้
