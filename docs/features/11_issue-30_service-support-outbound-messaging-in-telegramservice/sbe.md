# SBE: Proactive Messaging in TelegramService

> 📅 Created: 2026-03-09
> 🔗 Issue: https://github.com/oatrice/Akasa/issues/30

---

## Feature: Proactive Messaging via TelegramService

เพิ่มความสามารถให้ `TelegramService` สามารถส่งข้อความหาผู้ใช้ได้โดยตรง (proactively) โดยใช้ `user_id` ของผู้ใช้เป็นตัวระบุ ระบบจะค้นหา `chat_id` ที่ผูกกับ `user_id` นั้นจาก Redis แล้วจึงส่งข้อความผ่าน Telegram API ซึ่งจำเป็นสำหรับการส่งการแจ้งเตือนหรือผลลัพธ์ของงานที่ใช้เวลานาน

### Scenario: Happy Path - ส่งข้อความหาผู้ใช้ที่เคยติดต่อสำเร็จ

**Given** `chat_id` ของผู้ใช้ถูกจัดเก็บไว้ใน Redis อย่างถูกต้อง
**When** `TelegramService.send_proactive_message` ถูกเรียกใช้ด้วย `user_id` และข้อความที่ต้องการส่ง
**Then** ระบบจะเรียกใช้ Telegram API เพื่อส่งข้อความไปยัง `chat_id` ที่ถูกต้อง และคืนค่า `True`

#### Examples

| user_id | text | expected_chat_id_lookup | expected_telegram_api_call | return_value |
|---------|------|---------------------------|------------------------------|--------------|
| "12345" | "Your report is ready." | "98765" | `sendMessage(chat_id="98765", text="Your report is ready.")` | `True` |
| "67890" | "Reminder: Your subscription is expiring." | "54321" | `sendMessage(chat_id="54321", text="Reminder: Your subscription is expiring.")` | `True` |
| "11122" | "Hello from Akasa!" | "33445" | `sendMessage(chat_id="33445", text="Hello from Akasa!")` | `True` |
| "99001" | "ผลการวิเคราะห์โปรเจกต์ของคุณเสร็จสิ้นแล้ว" | "77889" | `sendMessage(chat_id="77889", text="ผลการวิเคราะห์โปรเจกต์ของคุณเสร็จสิ้นแล้ว")` | `True` |

### Scenario: Error Handling - ไม่พบข้อมูลผู้ใช้ในระบบ (User Not Found)

**Given** `user_id` ที่ระบุไม่มีข้อมูล `chat_id` ถูกจัดเก็บไว้ใน Redis
**When** `TelegramService.send_proactive_message` ถูกเรียกใช้ด้วย `user_id` ที่ไม่มีในระบบ
**Then** ระบบ **ต้องไม่** เรียกใช้ Telegram API, บันทึก Log ว่า "User not found", และคืนค่า `False`

#### Examples

| user_id | text | expected_log_message | return_value |
|---------|------|------------------------|--------------|
| "user_never_chatted" | "This will fail." | "Chat ID not found for user_id: user_never_chatted" | `False` |
| "99999" | "Welcome!" | "Chat ID not found for user_id: 99999" | `False` |
| "ABC-DEF" | "Test message" | "Chat ID not found for user_id: ABC-DEF" | `False` |

### Scenario: Error Handling - ผู้ใช้บล็อกบอท (Bot Was Blocked)

**Given** `chat_id` ของผู้ใช้ถูกเก็บใน Redis แต่ผู้ใช้ได้ทำการบล็อกบอทใน Telegram แล้ว
**When** `TelegramService.send_proactive_message` ถูกเรียกใช้
**Then** ระบบจะเรียก Telegram API แต่จะได้รับ Error `Forbidden: bot was blocked by the user`, จากนั้นระบบจะบันทึก Log ที่เฉพาะเจาง และคืนค่า `False`

#### Examples

| user_id | text | expected_telegram_api_call | api_response | expected_log_message | return_value |
|---------|------|------------------------------|--------------|------------------------|--------------|
| "user_who_blocked" | "Please unblock me." | `sendMessage(chat_id="chat_of_blocker", ...)` | `HTTP 403 Forbidden` | "Failed to send to user_id user_who_blocked: Bot was blocked." | `False` |
| "56789" | "A notification" | `sendMessage(chat_id="555444", ...)` | `HTTP 403 Forbidden` | "Failed to send to user_id 56789: Bot was blocked." | `False` |