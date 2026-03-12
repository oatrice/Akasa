# Walkthrough: Remote Action Confirmation

> 📅 Date: 2026-03-12
> 🔗 Feature: [Issue #49](https://github.com/oatrice/Akasa/issues/49)

เอกสารนี้อธิบายวิธีการตั้งค่าและตรวจสอบการทำงานของระบบยืนยันการกระทำระยะไกล (Remote Action Confirmation) ผ่าน Akasa Bot (Telegram)

## 1. การตั้งค่า (Configuration)

### ฝั่ง Backend (Akasa API)
อัปเดตไฟล์ `.env` ของคุณด้วยค่าต่อไปนี้:
```env
# API Key สำหรับการสื่อสารระหว่าง CLI และ Backend
AKASA_API_KEY=your-secure-key-here

# รายชื่อ Chat ID ของ Telegram ที่อนุญาตให้รับแจ้งเตือน (คั่นด้วยเครื่องหมายจุลภาค)
ALLOWED_TELEGRAM_CHAT_IDS=6346467495,123456789
```

### ฝั่ง Client (Gemini CLI)
*หมายเหตุ: ส่วนนี้จะอยู่ในขั้นตอนการพัฒนาฝั่ง CLI ต่อไป*
- CLI จะต้องส่ง `X-Akasa-API-Key` ใน Header
- CLI จะต้องส่ง `chat_id` ที่ถูกต้องใน Request Body

## 2. วิธีการทดสอบแบบ Manual (Manual Verification)

### ขั้นตอนที่ 1: ส่งคำขอยืนยัน (Initiate Request)
ใช้ `curl` เพื่อจำลอง Gemini CLI ส่งคำขอ:

```bash
curl -X POST http://localhost:8000/api/v1/actions/request \
     -H "Content-Type: application/json" \
     -H "X-Akasa-API-Key: your-secure-key-here" \
     -d '{
       "chat_id": "YOUR_CHAT_ID",
       "message": "⚠️ *Akasa Required Confirmation*\n\nCommand: `rm -rf /tmp/test`",
       "metadata": {
         "request_id": "test-001",
         "command": "rm -rf /tmp/test",
         "cwd": "/project/root",
         "session_id": "session-unique-id"
       }
     }'
```

### ขั้นตอนที่ 2: ตรวจสอบสถานะ (Polling)
จำลอง CLI ที่กำลังรอคำตอบ (Long-polling):

```bash
curl -X GET http://localhost:8000/api/v1/actions/requests/test-001 \
     -H "X-Akasa-API-Key: your-secure-key-here"
```

### ขั้นตอนที่ 3: ตอบโต้ผ่าน Telegram
1. บอทจะส่งข้อความเข้า Telegram ของคุณพร้อมปุ่ม: `✅ Allow Once`, `🛡️ Allow Session`, `❌ Deny`
2. เมื่อกดปุ่ม ข้อความจะเปลี่ยนสถานะ และ `curl` ในขั้นตอนที่ 2 จะได้รับ JSON ตอบกลับทันที

## 3. ความสามารถพิเศษ (Key Features)

- **Real-time Updates**: เมื่อกดปุ่มใน Telegram ข้อความเดิมจะถูกแก้ไขเพื่อแสดงว่าใครเป็นคนตัดสินใจและตัดสินใจอย่างไร
- **Session Support**: หากกด `🛡️ Allow Session` คำสั่งถัดๆ ไปที่มี `session_id` เดียวกันจะได้รับการอนุมัติอัตโนมัติ (แต่ยังคงมีการแจ้งเตือนเป็น Log ใน Telegram เสมอ)
- **Security**: มีระบบ Whitelist สำหรับ `chat_id` ป้องกันบอทส่งข้อความหาคนอื่นโดยไม่ได้รับอนุญาต
- **Markdown Support**: รองรับการใช้ `*ตัวหนา*` และ `_ตัวเอียง_` ในข้อความแจ้งเตือน
