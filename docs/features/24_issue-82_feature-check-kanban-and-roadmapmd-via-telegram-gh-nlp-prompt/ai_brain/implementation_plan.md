# Luma CLI — เพิ่ม Telegram Notification เมื่อ Action เสร็จสิ้น

## สาเหตุของปัญหา

Luma CLI (Python) ไม่มีการเชื่อมต่อกับ Akasa Backend เลย จึง **ไม่เคยส่ง notification ไป Telegram** เมื่อทำงานเสร็จ

ระบบ `notify_task_complete` ทำงานผ่าน Akasa MCP Server → Akasa Backend (`POST /api/v1/notifications/task-complete`) → Telegram Bot แต่ Luma เรียก LLM (Gemini CLI) ผ่าน subprocess โดยตรง ไม่ได้ผ่าน MCP protocol

## Proposed Changes

### Notifier Module

#### [NEW] [notifier.py](file:///Users/oatrice/Software-projects/Luma/luma_core/notifier.py)

สร้าง module ใหม่สำหรับส่ง notification ไป Akasa Backend:

- ฟังก์ชัน `notify_task_complete(project, task, status, ...)` — เรียก `POST /api/v1/notifications/task-complete`
- ใช้ `requests` (sync) เนื่องจาก Luma ทั้งระบบเป็น sync
- อ่าน env vars: `AKASA_API_URL`, `AKASA_API_KEY`, `AKASA_CHAT_ID` จาก `.env`
- **ถ้า env vars ไม่ได้ตั้ง → skip อย่างเงียบ (print warning ครั้งเดียว)** ไม่ crash

---

### Config Changes

#### [MODIFY] [config.py](file:///Users/oatrice/Software-projects/Luma/luma_core/config.py)

เพิ่ม Akasa config vars:
```python
AKASA_API_URL = os.getenv("AKASA_API_URL", "http://localhost:8000")
AKASA_API_KEY = os.getenv("AKASA_API_KEY", "default-dev-key")
AKASA_CHAT_ID = os.getenv("AKASA_CHAT_ID", "")
```

---

### Main Loop Integration

#### [MODIFY] [main.py](file:///Users/oatrice/Software-projects/Luma/main.py)

เพิ่มการเรียก `notifier.notify_task_complete()` หลังจากแต่ละ action ที่ "ทำงานจริง" เสร็จ (เช่น code review, generate spec, create PR ฯลฯ) โดย wrap ใน helper function:

```python
def run_action_with_notification(action_name, action_func, *args, **kwargs):
    """Run an action and send notification on completion."""
    start = time.time()
    try:
        result = action_func(*args, **kwargs)
        duration = f"{time.time() - start:.0f}s"
        notifier.notify_task_complete(
            project=project["name"],
            task=action_name,
            status="success",
            duration=duration
        )
        return result
    except Exception as e:
        notifier.notify_task_complete(
            project=project["name"],
            task=action_name,
            status="failure",
            message=str(e)
        )
        raise
```

---

### Env File Updates

#### [MODIFY] [.env.example](file:///Users/oatrice/Software-projects/Luma/.env.example)

เพิ่ม:
```
AKASA_API_URL=http://localhost:8000
AKASA_API_KEY=default-dev-key
AKASA_CHAT_ID=your_telegram_chat_id
```

---

## User Review Required

> [!IMPORTANT]
> **ต้องตั้ง env vars ใน `.env` ของ Luma:** `AKASA_API_URL`, `AKASA_API_KEY`, `AKASA_CHAT_ID`
> ถ้าไม่ตั้ง ระบบจะ skip notification อย่างเงียบเฉย (ไม่ crash)

> [!NOTE]
> dependency `requests` ไม่ต้องเพิ่ม เพราะ `langchain-core` ที่มีอยู่แล้วจะ pull `requests` เข้ามาเป็น transitive dependency อยู่แล้ว — จะตรวจสอบอีกทีตอน implement

## Verification Plan

### Automated Tests

สร้างไฟล์ test ใหม่ `tests/test_notifier.py` (TDD):

```bash
cd /Users/oatrice/Software-projects/Luma && python -m pytest tests/test_notifier.py -v
```

Test cases:
1. 🟥 `test_notify_sends_correct_payload` — mock `requests.post`, ตรวจ payload ที่ส่งไป
2. 🟥 `test_notify_skips_when_no_chat_id` — ถ้า `AKASA_CHAT_ID` ว่าง ต้อง skip ไม่ crash
3. 🟥 `test_notify_handles_network_error` — ถ้า API ล้มเหลว ต้อง catch ไม่ crash Luma

### Manual Verification

1. ตั้ง env vars ใน Luma `.env` แล้วรัน action (เช่น Code Review)
2. ตรวจดูว่ามี notification เข้า Telegram หรือไม่
