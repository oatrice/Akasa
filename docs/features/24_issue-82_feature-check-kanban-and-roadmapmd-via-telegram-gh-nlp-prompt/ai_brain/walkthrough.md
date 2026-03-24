# Walkthrough: Luma CLI — Telegram Notification

## สิ่งที่ทำ

เพิ่มความสามารถให้ Luma CLI ส่ง notification ไป Telegram ผ่าน Akasa Backend เมื่อ action (เช่น Code Review, Generate Spec, Create PR ฯลฯ) ทำงานเสร็จสิ้น

## ไฟล์ที่เปลี่ยนแปลง

| File | Action | Description |
|------|--------|-------------|
| [notifier.py](file:///Users/oatrice/Software-projects/Luma/luma_core/notifier.py) | **NEW** | Module สำหรับส่ง POST ไป Akasa Backend |
| [test_notifier.py](file:///Users/oatrice/Software-projects/Luma/tests/test_notifier.py) | **NEW** | 5 test cases (TDD) |
| [config.py](file:///Users/oatrice/Software-projects/Luma/luma_core/config.py) | MODIFY | เพิ่ม `AKASA_API_URL`, `AKASA_API_KEY`, `AKASA_CHAT_ID` |
| [main.py](file:///Users/oatrice/Software-projects/Luma/main.py) | MODIFY | Wrap 8 actions ด้วย `run_with_notify()` |
| [.env.example](file:///Users/oatrice/Software-projects/Luma/.env.example) | MODIFY | เพิ่ม AKASA env vars |

## TDD Results

✅ 5/5 tests passing:
- `test_notify_sends_correct_payload` — ส่ง payload ถูกต้อง
- `test_notify_skips_when_no_chat_id` — skip เมื่อไม่มี Chat ID
- `test_notify_handles_network_error` — จัดการ network error
- `test_notify_excludes_none_optional_fields` — ไม่ส่ง None fields
- `test_notify_handles_http_error` — จัดการ HTTP 500

## ⚠️ ขั้นตอนที่เหลือ

> [!IMPORTANT]
> ต้องเพิ่ม env vars ใน `/Users/oatrice/Software-projects/Luma/.env`:
> ```
> AKASA_API_URL=http://localhost:8000
> AKASA_API_KEY=default-dev-key
> AKASA_CHAT_ID=<chat_id จาก Telegram>
> ```
> แล้ว **restart Luma CLI** เพื่อให้ config มีผล
