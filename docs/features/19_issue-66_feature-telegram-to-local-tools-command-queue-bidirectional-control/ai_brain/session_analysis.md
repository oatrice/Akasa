# Session Analysis: Manual Verification of Akasa MCP Notifications

> 📝 บันทึกการวิเคราะห์จาก session ที่นำไปสู่การสร้าง Feature #66

---

## 📌 Session Information

| รายการ | รายละเอียด |
|--------|-----------|
| **Session Title** | Manual Verification of Akasa MCP Notifications |
| **Date** | 2025-07-14 |
| **Session Thread** | [zed:///agent/thread/7b0b5f0f-b9e9-4ecf-a791-be55c442f076](zed:///agent/thread/7b0b5f0f-b9e9-4ecf-a791-be55c442f076) |
| **Outcome** | Feature #66 created — Telegram → Local Tools Command Queue |
| **Related Issues Completed** | #33, #34 (Async Deployment + Post-Build Notification) |

---

## 1. Session Overview

Session นี้เริ่มต้นจากการ **verify ว่า MCP notifications ทำงานถูกต้อง** เมื่อถูก invoke จาก Zed IDE และ Gemini CLI จากนั้นขยายไปสู่การอภิปรายเรื่อง **Bidirectional Control** — ความสามารถที่ให้ผู้ใช้ส่งคำสั่งจาก Telegram ไปยัง local tools

### ประเด็นหลักที่ถูกพูดถึง

1. **MCP Server Initialization Issues** — ปัญหา startup timeout เมื่อถูก invoke จาก IDE
2. **Telegram Inline Keyboard Stale State** — keyboard ไม่ถูก update หลัง Allow/Deny
3. **Async Deployment (#33) + Post-Build Notification (#34)** — implement และ test ครบ
4. **Bidirectional Control Architecture** — architecture discussion สำหรับ Telegram → Local Tools

---

## 2. Root Causes Identified & Fixed

### 2.1 MCP Startup from Zed IDE

| ปัญหา | Root Cause | Fix Applied |
|-------|-----------|-------------|
| MCP script ไม่ start | Relative path ไม่ resolve ได้จาก Zed context | เปลี่ยนเป็น absolute path |
| Initialization timeout 60s | Stdin handling ต่างกันระหว่าง Zed vs terminal | ปรับ stdin handling สำหรับ Zed context |
| Log ถูก overwrite | Log file open ใน write mode | เปลี่ยนเป็น append mode + PID prefix |
| Zed vs Gemini log confusion | ทั้งสอง instance เขียน log เดียวกัน | แยก log file per PID/context |

### 2.2 Telegram Inline Keyboard

| ปัญหา | Root Cause | Fix Applied |
|-------|-----------|-------------|
| Keyboard ยังแสดงอยู่หลัง Allow/Deny | Callback handler ไม่ edit/delete message | Fix callback flow ให้ remove/update keyboard |
| User กด Allow แล้ว button ยัง active | `answer_callback_query` ไม่ถูก call | เพิ่ม `answer_callback_query` ทุก callback |

---

## 3. Features Completed in Session

### 3.1 Async Deployment Service (#33) ✅

```
Implementation:
- app/services/deploy_service.py
- POST /api/v1/deployments
- GET  /api/v1/deployments/{deployment_id}
- Redis-backed state: pending → in_progress → success/failed
- BackgroundTasks สำหรับ non-blocking execution
```

**Test Coverage Added:**
- Unit tests สำหรับ Redis state management
- Unit tests สำหรับ deployment workflow
- Integration tests สำหรับ API endpoints

### 3.2 Post-Build Notification (#34) ✅

```
Implementation:
- Telegram inline keyboard with deployed URL
- URL extraction จาก deployment output (regex patterns)
- Notification sent on both success and failure
- TelegramService extended: send_notification_with_keyboard()
```

**Test Coverage Added:**
- Unit tests สำหรับ URL extraction patterns
- Unit tests สำหรับ Telegram notification + inline keyboard
- Total tests: 245 → 337 (92 new tests)

---

## 4. Architecture Discussion: Bidirectional Control

### 4.1 Problem Identified

หลังจาก implement #33 และ #34 เสร็จ ผู้ใช้ตั้งคำถามว่า:

> "ถ้าเราต้องการให้ Telegram trigger actions ใน local tools ได้ เช่น Luma, Gemini, Zed — จะทำอย่างไร?"

### 4.2 Options Evaluated

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| **Redis List (BRPOP)** | Simple, reliable, TTL, ไม่ต้องการ persistent connection | Poll-based (latency 1-2s) | ✅ **เลือกใช้** |
| Redis Pub/Sub | Real-time push | ข้อความหายถ้า daemon offline | Future upgrade |
| WebSocket/SSE | Real-time, bidirectional | ต้องเปิด port จาก local machine สู่ internet | ❌ Security risk |
| Direct HTTP callback | Simple concept | Local machine ต้องการ public IP | ❌ ไม่ practical |

### 4.3 Architectural Decisions Made

```
1. Transport: Redis List (LPUSH/BRPOP) — poll-based, safe, proven

2. Security:
   - Command whitelist (ไม่อนุญาต arbitrary execution)
   - Telegram user_id validation (owner-only)
   - Redis TTL per command item (default 5 min)
   - subprocess.run() with shell=False เสมอ

3. Component isolation:
   - Daemon เป็น standalone process
   - ไม่ผูกกับ FastAPI lifecycle
   - Start/stop independently

4. Result reporting:
   - Reuse POST /api/v1/notifications/task-complete
   - ไม่สร้าง notification channel ใหม่

5. Daemon ≠ IDE plugin:
   - Daemon เป็น lightweight Python script
   - ไม่ขึ้นกับ Zed/Gemini initialization timing
   - รันเป็น background process ใน macOS
```

### 4.4 Security Model

```
Layers of protection:
1. Telegram → Akasa: user_id validated against ALLOWED_TELEGRAM_USER_IDS
2. Akasa → Redis: command validated against COMMAND_WHITELIST before enqueue
3. Redis → Daemon: daemon validates TTL meta key before execution
4. Daemon → OS: subprocess.run(args_list, shell=False) — no shell injection
5. Daemon → Telegram: sanitize output before forwarding (no secret leakage)
```

---

## 5. Test Suite Status (End of Session)

| Phase | Tests | Status |
|-------|-------|--------|
| Initial baseline | 245 | ✅ All pass |
| After #33 + #34 implementation | 337 | ✅ All pass (92 new) |
| Coverage areas added | Redis state, deployment workflow, URL extraction, Telegram notifications | ✅ |

---

## 6. Key Technical Observations

### 6.1 MCP Server Behavior in Different Contexts

```
Context       │ Startup Time │ Path Resolution │ Log Behavior
──────────────┼──────────────┼─────────────────┼─────────────────
Terminal      │ Fast (<1s)   │ Works with rel. │ Normal
Zed IDE       │ Slow (up to  │ Requires abs.   │ Needs append
              │ 60s timeout) │ path            │ mode + PID
Gemini CLI    │ Moderate     │ Requires abs.   │ Separate log
              │              │ path            │ per session
```

### 6.2 Redis as Universal Integration Layer

Session นี้ reinforced ว่า Redis เป็น **central integration bus** ที่เหมาะสมสำหรับ Akasa:
- Conversation history → Redis Hash
- Deployment status → Redis Hash
- Command queue → Redis List (new in #66)
- Rate limiting → Redis Counter + TTL

### 6.3 Notification Reuse Pattern

Pattern ที่ emerge จาก #33, #34, และ #66:
```
Any async operation → completes → POST /api/v1/notifications/task-complete
                                → Telegram notification
```
Pattern นี้ควร standardize เป็น convention สำหรับ features ใหม่ทุกตัว

---

## 7. Issues Identified for Future Work

| Issue | Description | Priority |
|-------|-------------|----------|
| **#66 (this)** | Telegram → Local Tools Command Queue | 🟡 Medium |
| MCP daemon startup | Consider launchd plist สำหรับ auto-start MCP server | 🟢 Low |
| Multi-issue Luma update | Fix `action_update_roadmap` สำหรับ multiple issue IDs | 🟢 Low |
| Command result size limit | Telegram message มี 4096 char limit — ต้อง truncate long output | 🟢 Low |

---

## 8. Lessons Learned

| Lesson | Application |
|--------|-------------|
| Path resolution ต่างกันระหว่าง IDE context และ terminal | Always use `pathlib.Path(__file__).parent.absolute()` ใน scripts |
| Inline keyboard ต้องถูก update/remove หลัง user interaction | ทุก callback handler ต้อง call `edit_message_reply_markup` หรือ `answer_callback_query` |
| Append log mode สำคัญมาก | Log file ที่ถูก overwrite ทำให้ debug ยาก โดยเฉพาะ multi-process |
| Security whitelist must come first | อย่า implement execution logic ก่อน whitelist — ทำ whitelist config ก่อนเสมอ |
| Decouple daemon from app lifecycle | Daemon ที่ tight-coupled กับ FastAPI startup จะ fail เมื่อ app restart |

---

## 9. References

| Document | Path |
|----------|------|
| Feature Analysis | `docs/features/19_.../analysis.md` |
| Technical Spec | `docs/features/19_.../spec.md` |
| Implementation Plan | `docs/features/19_.../plan.md` |
| Roadmap | `docs/ROADMAP.md` |
| GitHub Issue #66 | https://github.com/oatrice/Akasa/issues/66 |
| Related Issue #33 | https://github.com/oatrice/Akasa/issues/33 |
| Related Issue #34 | https://github.com/oatrice/Akasa/issues/34 |
| Related Issue #61 | https://github.com/oatrice/Akasa/issues/61 |