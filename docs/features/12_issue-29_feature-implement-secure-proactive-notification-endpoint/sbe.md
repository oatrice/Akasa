# SBE: Secure Proactive Notification Endpoint

> 📅 Created: 2026-03-09
> 🔗 Issue: https://github.com/oatrice/Akasa/issues/29

---

## Feature: Secure Proactive Notification Endpoint

สร้าง Endpoint `POST /api/v1/notifications/send` เพื่อรับ Payload ข้อความจากภายนอก (เช่น Gemini CLI) โดย Endpoint นี้จะทำการตรวจสอบ `X-Akasa-API-Key` จาก Header และทำการส่งข้อความผ่าน `TelegramService` ไปยัง `user_id` ที่ระบุ

### Scenario: Happy Path - ส่งการแจ้งเตือนสำเร็จ

**Given** มีการตั้งค่า `X-Akasa-API-Key` ที่ถูกต้องและ `user_id` ที่มี `chat_id` ถูกจัดเก็บไว้ใน Redis
**When** ระบบส่ง `POST` request ไปยัง `/api/v1/notifications/send` พร้อม Header `X-Akasa-API-Key` ที่ถูกต้องและ Payload ที่มีข้อมูลครบถ้วน
**Then** Endpoint จะตรวจสอบ API Key สำเร็จ
**And** Payload จะถูก Parse และ Validate สำเร็จ
**And** `TelegramService.send_proactive_message` จะถูกเรียกใช้ด้วยข้อมูลที่ถูกต้อง
**And** Endpoint จะคืนค่า `200 OK` พร้อมข้อความยืนยัน

#### Examples

| `X-Akasa-API-Key` Header | `user_id` (Payload) | `message` (Payload) | `priority` (Payload) | `metadata` (Payload) | Expected API Response Body |
|---|---|---|---|---|---|
| `valid-akasa-key-xyz789` | `"123456789"` | `"System maintenance scheduled"` | `"high"` | `{"maintenance_window": "2026-03-10T02:00:00Z"}` | `{"status": "success", "message": "Notification queued for delivery."}` |
| `valid-akasa-key-xyz789` | `"987654321"` | `"Your report is ready."` | `"normal"` | `{}` | `{"status": "success", "message": "Notification queued for delivery."}` |
| `valid-akasa-key-xyz789` | `"112233445"` | `"Deployment successful"` | `"normal"` | `{"deployment_id": "deploy-abc-789"}` | `{"status": "success", "message": "Notification queued for delivery."}` |

### Scenario: Authentication Failure - API Key ไม่ถูกต้อง

**Given** `X-Akasa-API-Key` ใน Header ไม่ถูกต้อง, ขาดหายไป, หรือหมดอายุ
**When** ระบบส่ง `POST` request ไปยัง `/api/v1/notifications/send`
**Then** การตรวจสอบ API Key จะล้มเหลว
**And** Request จะถูกปฏิเสธทันที
**And** Endpoint จะคืนค่า `401 Unauthorized`

#### Examples

| `X-Akasa-API-Key` Header | Expected API Response Status Code | Expected API Response Body |
|---|---|---|
| `invalid-akasa-key` | `401` | `{"detail": "Invalid or missing API key"}` |
| `""` (Empty header) | `401` | `{"detail": "Invalid or missing API key"}` |
| (Header missing) | `401` | `{"detail": "Invalid or missing API key"}` |

### Scenario: Bad Request - Payload ไม่ถูกต้อง

**Given** `X-Akasa-API-Key` ถูกต้อง
**When** ระบบส่ง `POST` request ไปยัง `/api/v1/notifications/send` พร้อม Payload ที่ขาดฟิลด์ที่จำเป็น หรือมีชนิดข้อมูลไม่ถูกต้อง
**Then** การตรวจสอบ Payload จะล้มเหลว
**And** Request จะถูกปฏิเสธ
**And** Endpoint จะคืนค่า `400 Bad Request` พร้อมรายละเอียดของข้อผิดพลาด

#### Examples

| `user_id` (Payload) | `message` (Payload) | `priority` (Payload) | `metadata` (Payload) | Expected API Response Status Code | Expected API Response Body |
|---|---|---|---|---|---|
| `null` | `"System update"` | `"normal"` | `{}` | `400` | `{"detail": "user_id is required"}` |
| `"123456789"` | `null` | `"high"` | `{}` | `400` | `{"detail": "message is required"}` |
| `"123456789"` | `"Test"` | `"urgent"` (Invalid enum value) | `{}` | `400` | `{"detail": "priority must be one of 'high' or 'normal'"}` |
| `"123456789"` | `"Test"` | `"normal"` | `["invalid_metadata"]` (Not an object) | `400` | `{"detail": "metadata must be an object"}` |

### Scenario: Internal Error during Notification Dispatch

**Given** `X-Akasa-API-Key` ถูกต้อง
**And** Payload ถูกต้อง
**When** ระบบส่ง `POST` request ไปยัง `/api/v1/notifications/send`
**And** `TelegramService.send_proactive_message` เกิด Exception (เช่น `UserChatIdNotFoundException` หรือ `BotBlockedException`)
**Then** Exception จะถูก Catch โดย Handler ของ Endpoint
**And** Endpoint จะคืนค่า Error Response ที่เหมาะสม (เช่น `400 Bad Request` สำหรับ `UserChatIdNotFoundException` หรือ `500 Internal Server Error` สำหรับ `BotBlockedException` หรือข้อผิดพลาดอื่นๆ ที่ไม่คาดคิด)

#### Examples

| `user_id` (Payload) | `message` (Payload) | `priority` (Payload) | `metadata` (Payload) | `TelegramService` Exception | Expected API Response Status Code | Expected API Response Body |
|---|---|---|---|---|---|---|
| `"unknown-user"` | `"Hello"` | `"normal"` | `{}` | `UserChatIdNotFoundException` | `400` | `{"detail": "User not found for notification"}` |
| `"blocked-user"` | `"Maintenance"` | `"high"` | `{}` | `BotBlockedException` | `500` | `{"detail": "Failed to send notification: Bot blocked by user."}` |
| `"user-with-error"` | `"Test"` | `"normal"` | `{}` | `RuntimeError("Unexpected issue")` | `500` | `{"detail": "An internal error occurred during notification dispatch."}` |