# Agent Watchdog — Akasa

## ภาพรวม

Watchdog script สำหรับดัก Error จาก **Antigravity IDE** และ **Zed IDE** แล้วแจ้งเตือนเข้า Telegram ผ่าน Akasa bot โดยอัตโนมัติ

เนื่องจาก AI Agent ที่ถูก Terminate ฉุกเฉินไม่สามารถเรียก `notify_task_complete` ได้ด้วยตัวเอง watchdog จึงทำหน้าที่เป็น External Observer คอยตรวจสอบ log file แบบ real-time

---

## ตำแหน่ง Log File ที่ Monitor

| IDE | Log Path | Pattern ที่ดัก |
|-----|----------|----------------|
| **Antigravity** | `~/.gemini/antigravity/daemon/ls_*.log` | `MCP_SERVER_INIT_ERROR`, `Got signal terminated`, `panic` |
| **Zed** | `~/Library/Logs/Zed/Zed.log` | `panic`, `agent.*error`, `crashed` |

---

## วิธีใช้งาน

```bash
# Start watchdog (รันใน background)
./scripts/watchdog.sh start

# หยุด watchdog
./scripts/watchdog.sh stop

# ดูสถานะ
./scripts/watchdog.sh status

# ทดสอบส่ง notification
./scripts/watchdog.sh test
```

---

## Requirements

Config ต้องมีใน `.env` ของโปรเจกต์:

```env
TELEGRAM_BOT_TOKEN=<โทเค็น Akasa bot>
AKASA_CHAT_ID=<Chat ID ของผู้ใช้ใน Telegram>
```

> [!NOTE]
> Script อ่านค่านี้จาก `.env` ที่ root ของ Akasa project อัตโนมัติ

---

## รายละเอียดการทำงาน

1. **Start** → fork process ไปรันใน background, บันทึก PID ที่ `/tmp/akasa_watchdog.pid`
2. **Zed Watcher** → `tail -F` ดู `Zed.log` แบบ real-time
3. **Antigravity Watcher** → Poll ทุก 5 วินาทีเพื่อหา `ls_*.log` ไฟล์ใหม่ (daemon สร้างใหม่ทุกครั้งที่ restart) แล้วสั่ง `tail -F` บนแต่ละไฟล์
4. **Cooldown** → ไม่ส่งซ้ำ Pattern เดิมภายใน 60 วินาที (กัน spam)
5. **Stop** → Kill process group ทั้งหมดแล้วลบ PID file

```
watchdog.sh start
   └── watch_loop() [background, PID บันทึกใน /tmp/akasa_watchdog.pid]
         ├── tail -F Zed.log    [sub-process]
         └── poll AG daemon dir [sub-process]
               └── tail -F ls_XXXX.log [ต่อไปเรื่อยๆ ตาม file ใหม่]
```

---

## Log Output

Watchdog บันทึกผลการตรวจจับที่ `/tmp/akasa_watchdog.log`

```bash
tail -f /tmp/akasa_watchdog.log
```

---

## ข้อจำกัด

| ข้อจำกัด | คำอธิบาย |
|----------|-----------|
| Pattern-based | ดักจาก log text เท่านั้น ไม่ได้ hook ระบบ OS |
| ไม่มี Context | ส่ง Telegram พร้อม log line สั้นๆ ไม่รู้ว่าตอนนั้นรัน Task อะไรอยู่ |
| **Ephemeral Error (Agent Terminated)** | **(Important)** ข้อความ `Agent terminated due to error` ที่แสดงบน UI ของแชท เป็นเพียง Internal State ของ Antigravity/Zed IDE เท่านั้น **ไม่ได้มีการเขียนลง Log file ใดๆ เลย** (ทดสอบค้นหาจากทั้ง `~/.gemini`, `Zed.log` และ *macOS OS Log* แล้วก็ไม่พบ) ส่งผลใหัสคริปต์นี้ไม่สามารถแจ้งเตือน Alert ประเภทนี้ได้ ต้องรอ Webhook API จากทาง Antigravity ในอนาคต |

---

## ดู Feature Doc ที่เกี่ยวข้อง

- [Feature 22 — IDE Integration for Command Queue](../features/22_issue-68_feat-ide-integration-for-command-queue-zed-antigravity-windsurf/)
- [Feature 16 — Antigravity IDE Action Confirmation](../features/16_issue-58_feature-antigravity-ide-action-confirmation-via-akasa-bot-telegram/)
