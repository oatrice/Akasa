# The Middle Way — Project Instructions

## Project Identity
- **Project Name:** `The Middle Way`
- ใช้ชื่อนี้เสมอเมื่อเรียก tool `notify_task_complete`

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
  project="The Middle Way",
  task="Deploy to production",
  status="retrying",
  retry_count=1,
  max_retries=3,
  message="<สาเหตุที่ล้มเหลว>"
)

# retry ครั้งที่ 2 ล้มเหลวอีก
notify_task_complete(
  project="The Middle Way",
  task="Deploy to production",
  status="retrying",
  retry_count=2,
  max_retries=3,
  message="<สาเหตุ>"
)

# retry ครบ limit → หยุด
notify_task_complete(
  project="The Middle Way",
  task="Deploy to production",
  status="limit_reached",
  max_retries=3,
  message="Gave up after 3 attempts. Last error: <สาเหตุ>"
)

# หรือ retry แล้วสำเร็จในครั้งที่ 2
notify_task_complete(
  project="The Middle Way",
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
  project="The Middle Way",
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
