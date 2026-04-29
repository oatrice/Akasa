# Manual Verification: Add model field to TaskNotificationRequest and display in notifications

> **Issue:** [#90](https://github.com/oatrice/Akasa/issues/90)
> **Feature:** เพิ่มฟิลด์ model ใน TaskNotificationRequest และแสดงใน Telegram notifications
> **Date:** 2026-04-29

## ภาพรวม

เอกสารนี้กำหนดขั้นตอนการ verify ด้วยตนเองหลังจาก implement ฟีเจอร์เสร็จสิ้น เพื่อตรวจสอบว่า:
- Implementation ทำงานถูกต้องตาม acceptance criteria
- Backward compatibility ยังคงอยู่
- ตอบโจทย์ issue #90 ในการเพิ่ม transparency สำหรับโมเดล AI

## Use Cases

ฟีเจอร์นี้รองรับ 2 usecases:

1. **Local AI (User Preference)**: User ตั้งค่า model ผ่าน `/model` command ใน Telegram → เก็บใน Redis → Local AI ใช้ model นี้ → Notification แสดง model ที่ user เลือก

2. **External AI (Direct Model)**: User ทำงานใน Windsurf/Kilo → External AI ส่ง notification พร้อม model ของตัวเอง (เช่น "SWE-1.6") → Notification แสดง model จาก payload (ไม่ override ด้วย Redis)

## Prerequisites

ก่อนเริ่ม verification:

1. **Environment Setup:**
   - Akasa backend ทำงานอยู่ (localhost:8000 หรือ ngrok)
   - Telegram bot token ถูกตั้งค่า
   - Redis ทำงานและสามารถเข้าถึงได้

2. **Configuration:**
   - ตั้งค่า `AKASA_CHAT_ID` ใน environment หรือ settings
   - มี API key ที่ถูกต้องสำหรับ authentication
   - MCP server พร้อมใช้งานถ้าต้องการ test ผ่าน MCP

3. **Test Data:**
   - Telegram chat ID ที่ใช้งานได้
   - Model identifiers สำหรับ test (เช่น "gpt-4o", "claude-3-sonnet")

## Verification Scenarios

### Scenario 1: Local AI - Model from User Preference

**Objective:** ตรวจสอบว่าเมื่อมี model preference ตั้งค่าไว้ใน Redis, notification จะแสดง model จาก Redis เมื่อ payload ไม่มี model

**Steps:**
1. ตั้งค่า model preference สำหรับ user:
   ```
   /model gpt-4o
   ```
2. ส่ง task notification ผ่าน API โดยไม่ระบุ model:
   ```bash
   curl -X POST http://localhost:8000/api/v1/notifications/task-complete \
     -H "X-Akasa-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{
       "project": "Akasa",
       "task": "Test local AI model display",
       "status": "success",
       "chat_id": "YOUR_CHAT_ID"
     }'
   ```
3. ตรวจสอบ Telegram notification ที่ได้รับ

**Expected Result:**
- Notification แสดง "*Model:* gpt-4o" (จาก Redis)
- ไม่มี error ใน logs

**Issue Coverage:** AC3 (retrieve from Redis when payload has no model)

### Scenario 2: External AI - Model from Payload

**Objective:** ตรวจสอบว่าเมื่อ external AI ส่ง model ใน payload, notification จะแสดง model จาก payload (ไม่ใช้ Redis)

**Steps:**
1. ตั้งค่า model preference ใน Redis (เพื่อทดสอบว่า payload มี priority สูงกว่า):
   ```
   /model gpt-4o
   ```
2. ส่ง task notification ผ่าน API พร้อม model ใน payload:
   ```bash
   curl -X POST http://localhost:8000/api/v1/notifications/task-complete \
     -H "X-Akasa-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{
       "project": "Akasa",
       "task": "Test external AI model display",
       "status": "success",
       "source": "Windsurf",
       "model": "SWE-1.6",
       "chat_id": "YOUR_CHAT_ID"
     }'
   ```
3. ตรวจสอบ Telegram notification ที่ได้รับ

**Expected Result:**
- Notification แสดง "*Source:* Windsurf"
- Notification แสดง "*Model:* SWE-1.6" (จาก payload, ไม่ใช่ gpt-4o จาก Redis)
- ไม่มี error ใน logs

**Issue Coverage:** AC2 (display model from payload), AC7 (MCP server accepts model parameter)

### Scenario 3: No Model Available

**Objective:** ตรวจสอบ backward compatibility เมื่อไม่มี model preference และไม่มี model ใน payload

**Steps:**
1. ลบหรือไม่ตั้งค่า model preference (Redis ไม่มีข้อมูลสำหรับ chat_id นั้น)
2. ส่ง task notification โดยไม่ระบุ model:
   ```bash
   curl -X POST http://localhost:8000/api/v1/notifications/task-complete \
     -H "X-Akasa-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{
       "project": "Akasa",
       "task": "Test no model",
       "status": "success",
       "chat_id": "YOUR_CHAT_ID"
     }'
   ```
3. ตรวจสอบ Telegram notification

**Expected Result:**
- Notification ไม่มี model line
- Notification แสดงปกติ (project, task, status)
- ไม่มี error

**Issue Coverage:** AC4 (backward compatibility), AC4 (no model when both absent)

### Scenario 4: Error Handling - Invalid model format

**Objective:** ตรวจสอบการ handle special characters ใน model name

**Steps:**
1. ตั้งค่า model preference ที่มี special chars:
   ```
   /model invalid@model!
   ```
2. ส่ง task notification โดยไม่ระบุ model (เพื่อให้ดึงจาก Redis)
3. ตรวจสอบ Telegram notification

**Expected Result:**
- Notification แสดง "*Model:* invalid\@model\!" (ถูก escape)
- MarkdownV2 rendering ไม่เสียหาย
- ไม่มี syntax error ใน notification

**Issue Coverage:** AC5 (safe display with escaping)

### Scenario 5: Integration Test with MCP Server

**Objective:** ตรวจสอบ end-to-end flow ผ่าน MCP server พร้อม model parameter

**Steps:**
1. เรียก notify_task_complete ผ่าน MCP client พร้อม model parameter:
   ```python
   notify_task_complete(
       project="Akasa",
       task="Test MCP model",
       status="success",
       model="grok"
   )
   ```
2. ตรวจสอบ backend logs ว่า model จาก payload ถูกใช้
3. ตรวจสอบ Telegram notification

**Expected Result:**
- Model "grok" ถูกส่งและแสดงอย่างถูกต้อง
- MCP response กลับมาปกติ

**Issue Coverage:** AC1, AC2, AC7

## Expected Results Summary

| Scenario | Expected Behavior | Pass Criteria |
|----------|-------------------|---------------|
| 1. Local AI (Redis) | "*Model:* {model_from_redis}" ปรากฏใน notification | ✅ |
| 2. External AI (Payload) | "*Model:* {model_from_payload}" ปรากฏ และ override Redis | ✅ |
| 3. No model | ไม่มี model line, notification ปกติ | ✅ |
| 4. Special chars | Model ถูก escape และแสดงได้ | ✅ |
| 5. MCP integration | End-to-end ทำงาน พร้อม model parameter | ✅ |

## Issue Mapping

- **AC1:** TaskNotificationRequest includes optional model field → Verified ผ่าน API payload
- **AC2:** Notifications display model from payload when provided → Verified ผ่าน scenario 2
- **AC3:** Notifications display model from Redis when payload has no model → Verified ผ่าน scenario 1
- **AC4:** No model displayed when None/absent in both → Verified ผ่าน scenario 3
- **AC5:** Model safely escaped in Markdown → Verified ผ่าน scenario 4
- **AC7:** MCP server accepts optional model parameter → Verified ผ่าน scenario 5
- **AC6:** Backward compatibility maintained → Verified ผ่าน scenario 3

## Troubleshooting

- **Notification ไม่แสดง:** ตรวจสอบ chat_id, bot token, และ Redis connection
- **Model ไม่ปรากฏ:** ตรวจสอบ model preference ตั้งค่าไว้หรือไม่ (ใช้ `/model` command)
- **Escape ไม่ทำงาน:** ตรวจสอบ `escape_markdown_v2_content` function
- **Redis error:** ตรวจสอบ Redis service และ chat_id mapping

## Sign-off

| Role | Name | Date | Status |
|------|------|------|--------|
| Tester | [Your Name] | [Date] | ⬜ |
| Developer | Kilo AI | 2026-04-29 | ✅ |

---

**Note:** หลังจาก verification เสร็จสิ้น, อัปเดต status ใน issue #90 และ merge code ถ้าทุกอย่าง pass