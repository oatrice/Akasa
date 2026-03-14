# Akasa — Project Instructions

## Project Identity
- **Project Name:** `Akasa`
- ใช้ชื่อนี้เสมอเมื่อเรียก tool `notify_task_complete`

## ✏️ Review Pending Notification (Required — Zed AI Agent)

**เมื่อ AI ใน Zed Agent mode ทำการ generate หรือแก้ไขไฟล์เสร็จแล้ว และกำลังรอให้ผู้ใช้กด Accept / Reject ใน editor ให้เรียกใช้ tool `notify_pending_review` ทันทีก่อนที่จะหยุดรอ**

### เมื่อไหร่ต้องเรียก `notify_pending_review`

| สถานการณ์ | ต้องเรียกไหม? |
|-----------|-------------|
| แก้ไข / สร้างไฟล์ใหม่เสร็จแล้ว รอ Accept/Reject | ✅ **ต้องเรียกเสมอ** |
| Implement feature หรือ fix bug เสร็จ รอ review | ✅ **ต้องเรียกเสมอ** |
| Generate code หลายไฟล์เสร็จ | ✅ **ต้องเรียกเสมอ** |
| Refactor / rename เสร็จ รอยืนยัน | ✅ **ต้องเรียกเสมอ** |
| แค่ตอบคำถาม ไม่ได้แก้ไขไฟล์ | ❌ ไม่ต้องเรียก |
| เรียก `request_remote_approval` แล้ว (รอ Allow/Deny) | ❌ ไม่ต้องเรียกซ้ำ |

### วิธีใช้:

```
notify_pending_review(
  project="Akasa",
  task="<สรุปสั้นๆ ว่า implement / แก้ไขอะไร>",
  files_changed=["app/services/foo.py", "app/routers/bar.py"],  # optional
  summary="<คำอธิบายสั้นๆ เกี่ยวกับการเปลี่ยนแปลง>"             # optional
)
```

### ตัวอย่าง:

```
# หลัง implement feature ใหม่
notify_pending_review(
  project="Akasa",
  task="Implement command queue service (Feature #66)",
  files_changed=[
    "app/services/command_queue_service.py",
    "app/routers/commands.py",
    "app/models/command.py"
  ],
  summary="Added Redis-backed command queue with whitelist validation and TTL"
)

# หลัง fix bug
notify_pending_review(
  project="Akasa",
  task="Fix Redis connection timeout in deploy_service",
  files_changed=["app/services/deploy_service.py"]
)
```

> **หมายเหตุ:** `notify_pending_review` เป็น **fire-and-forget** — ไม่ block รอผล ไม่เหมือน `request_remote_approval`
> ใช้เพื่อแจ้งผู้ใช้ให้กลับมาเปิด Zed เพื่อ Accept/Reject changes เท่านั้น

---

## 🔔 Task Completion Notification (Required)
**เมื่อทำงานที่ได้รับมอบหมายเสร็จสิ้น ให้เรียกใช้ tool `notify_task_complete` เป็น action สุดท้ายเสมอ**

### Status ที่ใช้ได้:

| status | ใช้เมื่อ | emoji |
|--------|---------|-------|
| `success` | งานสำเร็จสมบูรณ์ | ✅ |
| `failure` | งานล้มเหลว ไม่ retry แล้ว | ❌ |
| `partial` | สำเร็จบางส่วน มี warning | ⚠️ |
| `retrying` | ล้มเหลวแต่กำลัง retry | 🔄 |
| `limit_reached` | retry ครบ limit แล้ว หยุด | 🚫 |

### Retry Pattern — ใช้เมื่องานล้มเหลวและต้อง retry:

```
# ครั้งแรกล้มเหลว → ลอง retry
notify_task_complete(
  project="Akasa",
  task="Deploy to production",
  status="retrying",
  retry_count=1,
  max_retries=3,
  message="<สาเหตุที่ล้มเหลว>"
)

# retry ครั้งที่ 2 ล้มเหลวอีก
notify_task_complete(
  project="Akasa",
  task="Deploy to production",
  status="retrying",
  retry_count=2,
  max_retries=3,
  message="<สาเหตุ>"
)

# retry ครบ limit → หยุด
notify_task_complete(
  project="Akasa",
  task="Deploy to production",
  status="limit_reached",
  max_retries=3,
  message="Gave up after 3 attempts. Last error: <สาเหตุ>"
)

# หรือ retry แล้วสำเร็จในครั้งที่ 2
notify_task_complete(
  project="Akasa",
  task="Deploy to production",
  status="success",
  retry_count=2,
  max_retries=3,
  duration="<เวลาทั้งหมด>"
)
```

### Default (งานทั่วไป ไม่ retry):
```
notify_task_complete(
  project="Akasa",
  task="<สรุปสั้นๆ ว่างานคืออะไร>",
  status="success" | "failure" | "partial",
  duration="<เวลาโดยประมาณ>",     # optional
  message="<รายละเอียดเพิ่มเติม>", # optional
  link="<URL ที่เกี่ยวข้อง>"       # optional
)
```

---

## ⚙️ Prerequisites
Akasa backend ต้องรันอยู่ที่ `http://localhost:8000`
