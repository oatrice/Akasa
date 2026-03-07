# Specification: [Phase 1] Telegram Bot Webhook Integration

| | |
|---|---|
| **Feature Name** | [Phase 1] สร้าง Telegram Bot + webhook |
| **Issue URL** | [#3](https://github.com/oatrice/Akasa/issues/3) |
| **Status** | **Draft** |
| **Date** | 2026-03-07 |

## 1. เป้าหมาย (The 'Why')

เพื่อสร้างช่องทางการสื่อสารหลักระหว่างผู้ใช้งานกับระบบ Akasa Backend ทำให้แอปพลิเคชันสามารถรับข้อความและคำสั่งจากผู้ใช้ผ่าน Telegram ได้แบบ Real-time ซึ่งเป็นหัวใจสำคัญของการสร้าง Chatbot Assistant การเชื่อมต่อนี้จะทำผ่านกลไก Webhook เพื่อให้แน่ใจว่าทุกข้อความที่ถูกส่งมายังบอทจะถูกส่งต่อมายัง Backend ของเราเพื่อการประมวลผลต่อไป

## 2. ผู้ใช้งาน (User Persona)

| Persona | ลักษณะ |
|---|---|
| **End User** | ผู้ที่ใช้งานแอปพลิเคชัน Telegram และต้องการโต้ตอบกับ Akasa Chatbot เพื่อขอความช่วยเหลือด้านการเขียนโค้ด |
| **The System (Akasa Backend)** | ระบบเบื้องหลังที่ต้องรอรับและยืนยันความถูกต้องของข้อความที่ถูกส่งมาจาก Telegram |

## 3. เส้นทางของผู้ใช้ (User Journey)

**ในฐานะ**ผู้ใช้งาน Telegram
**ฉันต้องการ** ส่งข้อความไปยัง Akasa Bot
**เพื่อที่ฉันจะ** สามารถเริ่มต้นการสนทนาและส่งคำสั่งให้ระบบประมวลผลได้

## 4. เกณฑ์การยอมรับ (Acceptance Criteria)

- [ ] Backend ต้องมี API endpoint สำหรับรับ Webhook จาก Telegram ที่ `POST /api/v1/telegram/webhook`
- [ ] Endpoint นี้ต้องถูกป้องกัน และจะยอมรับ request ที่มี `X-Telegram-Bot-Api-Secret-Token` header ที่ถูกต้องเท่านั้น
- [ ] เมื่อได้รับ request ที่มี Secret Token ถูกต้อง ระบบจะต้องตอบกลับด้วย HTTP status `200 OK` (เพื่อยืนยันกับ Telegram ว่าได้รับข้อมูลแล้ว)
- [ ] เมื่อได้รับ request ที่มี Secret Token **ไม่ถูกต้อง** หรือ **ไม่มี** Secret Token, ระบบจะต้องตอบกลับด้วย HTTP status `403 Forbidden`
- [ ] ระบบต้องสามารถรับและแยกแยะข้อมูล (payload) ที่ Telegram ส่งมาในรูปแบบของ `Update` object ได้ (ในขั้นนี้แค่รับได้ ยังไม่ต้องประมวลผล)

## 5. กรณีตัวอย่าง (Specification by Example - SBE)

### **Scenario 1: ได้รับข้อความผ่าน Webhook สำเร็จ (Happy Path)**

**GIVEN** Akasa Backend ทำงานอยู่และตั้งค่า Secret Token ไว้อย่างถูกต้อง
**AND** Webhook ของ Telegram Bot ถูกตั้งค่าให้ชี้มาที่ `https://<your-public-url>/api/v1/telegram/webhook`
**WHEN** ผู้ใช้ส่งข้อความในแอป Telegram และ Telegram server ส่ง `POST` request มายัง Webhook พร้อมกับ Secret Token ที่ถูกต้องใน Header
**THEN** ระบบจะตอบกลับด้วย status `200 OK` และ Body ว่างเปล่า

**ตัวอย่าง:**

| Action | `POST /api/v1/telegram/webhook` |
|---|---|
| **Request Headers** | `Content-Type: application/json`<br>`X-Telegram-Bot-Api-Secret-Token: <VALID_SECRET_TOKEN>` |
| **Request Body (Example)** | ```json<br>{<br>  "update_id": 123,<br>  "message": { "text": "Hello Akasa" }<br>}``` |
| **Response Status** | `200 OK` |
| **Response Body** | (empty) |

---

### **Scenario 2: การเรียก Webhook ไม่สำเร็จเนื่องจาก Secret Token ผิดพลาด**

**GIVEN** Akasa Backend ทำงานอยู่
**WHEN** มี `POST` request ส่งมายัง `/api/v1/telegram/webhook` แต่มี Secret Token ใน Header ที่ **ไม่ถูกต้อง** หรือ **ไม่มี** Header ดังกล่าว
**THEN** ระบบจะปฏิเสธ request นั้นและตอบกลับด้วย status `403 Forbidden`

**ตัวอย่าง:**

| Header: `X-Telegram-Bot-Api-Secret-Token` | Response Status | Response Body (contains) |
|---|---|---|
| `invalid-secret-key` | `403 Forbidden` | `{"detail": "Invalid secret token"}` |
| (Header is missing) | `403 Forbidden` | `{"detail": "Secret token missing"}` |
| ` ` (empty string) | `403 Forbidden` | `{"detail": "Invalid secret token"}` |

## 6. สิ่งที่ไม่ได้ทำใน Scope นี้ (Out of Scope)

- การประมวลผลเนื้อหาของข้อความ (เช่น การส่งต่อไปยัง LLM)
- การส่งข้อความตอบกลับไปยังผู้ใช้ใน Telegram
- การจัดการกับข้อความประเภทอื่นนอกเหนือจาก Text (เช่น รูปภาพ, ไฟล์, สติกเกอร์)
- การตั้งค่าหรือยกเลิก Webhook ผ่าน API (ในขั้นนี้จะตั้งค่าด้วยมือหรือสคริปต์แยก)