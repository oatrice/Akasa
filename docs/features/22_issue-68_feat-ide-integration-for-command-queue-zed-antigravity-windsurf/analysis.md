# Analysis: IDE Integration for Command Queue

| Item | Value |
|---|---|
| Feature | IDE Integration for Command Queue |
| Issue | #68 |
| Date | 2026-03-18 |
| Priority | High |

## 1. Current State (As-Is)

- `local_tool_daemon` เดิม execute ได้จริงเฉพาะ `gemini` CLI
- โครงสร้าง whitelist เดิมเน้นตรวจชื่อ command เป็นหลัก
- ยังไม่มี protocol-aware dispatch (`cli/http/mcp`)
- tracing ยังไม่ครบเมื่อ command หมด TTL ตอน dequeue
- result payload ของ daemon ใช้ `duration` แต่ API model ใช้ `duration_seconds`

## 2. Target State (To-Be)

- daemon dispatch ได้ตาม `execution.type`
- whitelist มี execution metadata แบบ config-driven
- antigravity ใช้ MCP (`stdio`), windsurf ใช้ HTTP, zed ใช้ CLI
- path policy รองรับ relative/absolute/line:col อย่างปลอดภัย
- retry policy สำหรับ HTTP/MCP
- trace lifecycle ชัดเจนและตรวจย้อนหลังได้

## 3. Tradeoff Decisions

### 3.1 Zed Command Shape
- Option A: `command=open_file + args.path`
- Option B: `command=<path>`

Decision: **A**
- ดีต่อ whitelist validation, analytics, extension ในอนาคต
- ลด ambiguity ระหว่าง action name กับ payload

### 3.2 Whitelist Evolution
- Option A: ขยายแบบ backward-compatible
- Option B: เปลี่ยน schema ใหม่ทั้งหมด

Decision: **A**
- ลดความเสี่ยง breaking change
- rollout ปลอดภัยกว่าในระบบที่ใช้งานอยู่แล้ว

### 3.3 Endpoint Granularity
- Option A: endpoint ระดับ tool
- Option B: endpoint ระดับ command

Decision: **Hybrid**
- ใช้ defaults ระดับ tool เพื่อความง่าย
- รองรับ override ระดับ command เมื่อ endpoint แตกต่าง

## 4. Risks and Mitigation

- Risk: Command injection / unsafe execution
  - Mitigation: strict whitelist + no shell execution
- Risk: Path traversal
  - Mitigation: resolve path + allowed root checks
- Risk: SSRF via HTTP tools
  - Mitigation: localhost host allowlist
- Risk: flaky local IDE API/MCP process
  - Mitigation: configurable retry + backoff + timeout

## 5. Implementation Notes

- เพิ่ม raw whitelist parser และ merge defaults/overrides
- refactor daemon เป็น protocol-aware handlers
- เพิ่ม status transitions: `picked_up -> running -> success|failed|expired`
- fallback update status หาก report result endpoint ไม่พร้อมใช้งาน
- ปรับ result payload เป็น `duration_seconds`

## 6. Open Follow-up Items

- เพิ่ม test เฉพาะ retry behavior ของ HTTP/MCP ให้ละเอียดขึ้น
- ทดสอบ E2E ด้วย IDE จริง (zed/windsurf/antigravity)
- พิจารณา connection reuse สำหรับ MCP หากมี high throughput
