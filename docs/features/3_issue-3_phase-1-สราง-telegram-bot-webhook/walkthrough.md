# Walkthrough: Telegram Bot Webhook [Phase 1]

## สิ่งที่ทำ

ใช้ **TDD (Red → Green → Refactor)** สร้าง Webhook endpoint สำหรับรับข้อมูลจาก Telegram Bot API

### ไฟล์ที่สร้างใหม่

| ไฟล์ | หน้าที่ |
|---|---|
| [config.py](file:///Users/oatrice/Software-projects/Akasa/app/config.py) | โหลด settings จาก `.env` ด้วย `pydantic-settings` |
| [telegram.py (models)](file:///Users/oatrice/Software-projects/Akasa/app/models/telegram.py) | Pydantic models สำหรับ Telegram Update/Message/Chat/User |
| [telegram.py (router)](file:///Users/oatrice/Software-projects/Akasa/app/routers/telegram.py) | Webhook endpoint `POST /api/v1/telegram/webhook` + Secret Token verification |
| [test_telegram.py](file:///Users/oatrice/Software-projects/Akasa/tests/routers/test_telegram.py) | 4 test cases ครอบคลุม Happy path, Invalid/Missing token, 405 |
| [conftest.py](file:///Users/oatrice/Software-projects/Akasa/conftest.py) | เพิ่ม project root เข้า `sys.path` ให้ pytest |

### ไฟล์ที่แก้ไข

| ไฟล์ | การเปลี่ยนแปลง |
|---|---|
| [main.py](file:///Users/oatrice/Software-projects/Akasa/app/main.py) | เพิ่ม `telegram.router` |
| [requirements.txt](file:///Users/oatrice/Software-projects/Akasa/requirements.txt) | เพิ่ม `pydantic-settings` |
| [.env.example](file:///Users/oatrice/Software-projects/Akasa/.env.example) | เพิ่ม `TELEGRAM_BOT_TOKEN`, `WEBHOOK_SECRET_TOKEN` |
| [analysis.md](file:///Users/oatrice/Software-projects/Akasa/docs/features/3_issue-3_phase-1-สราง-telegram-bot-webhook/analysis.md) | แก้ Mermaid parse error |

## ผลการทดสอบ

```
15 passed in 0.31s
```

- ✅ `test_webhook_success_valid_token` — Token ถูกต้อง → 200 OK
- ✅ `test_webhook_fail_invalid_token` — Token ผิด → 403
- ✅ `test_webhook_fail_missing_token` — ไม่มี Token → 403
- ✅ `test_webhook_fail_unsupported_method` — GET ไม่ใช่ POST → 405
- ✅ Tests เดิมทั้ง 11 ตัว ยังผ่านหมด

## สิ่งที่ต้องทำต่อ (Manual)

1. สร้าง Telegram Bot ผ่าน **BotFather** แล้วเอา Token มาใส่ `.env`
2. รัน `ngrok http 8000` แล้วนำ HTTPS URL ไปตั้ง Webhook กับ Telegram API
