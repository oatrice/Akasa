# Specification: [Phase 1] FastAPI Backend Foundation

| | |
|---|---|
| **Feature Name** | [Phase 1] สร้าง FastAPI backend |
| **Issue URL** | [#2](https://github.com/oatrice/Akasa/issues/2) |
| **Status** | **Draft** |
| **Date** | 2026-03-07 |

## 1. เป้าหมาย (The 'Why')

เพื่อสร้างโครงสร้างพื้นฐานที่มั่นคงสำหรับ Backend ของโปรเจกต์ Akasa โดยใช้ FastAPI ซึ่งเป็นรากฐานที่จำเป็นก่อนที่จะเริ่มพัฒนาฟีเจอร์หลัก เช่น การรับ Webhook จากแอปแชท หรือการเชื่อมต่อกับ LLM API การมีโครงสร้างที่ชัดเจนและ endpoint สำหรับตรวจสอบสถานะ (`/health`) จะช่วยให้การพัฒนาและการดูแลรักษาระบบในอนาคตเป็นไปอย่างราบรื่น

## 2. ผู้ใช้งาน (User Persona)

| Persona | ลักษณะ |
|---|---|
| **Developer (นักพัฒนา)** | ผู้ที่จะต้องพัฒนาและต่อยอดฟีเจอร์ต่างๆ บน Backend และต้องการโครงสร้างโปรเจกต์ที่เป็นมาตรฐานเพื่อให้ทำงานได้ง่าย |
| **System Operator (ผู้ดูแลระบบ)** | ผู้ที่รับผิดชอบการ deploy และ monitoring แอปพลิเคชัน และต้องการ endpoint พื้นฐานเพื่อตรวจสอบว่าแอปพลิเคชันทำงานอยู่หรือไม่ |

## 3. เส้นทางของผู้ใช้ (User Journey)

**ในฐานะ**ผู้ดูแลระบบ (System Operator)
**ฉันต้องการ** เรียกใช้งาน `/health` endpoint
**เพื่อที่ฉันจะ** สามารถตรวจสอบได้ว่า Backend service ทำงานเป็นปกติและพร้อมใช้งาน

## 4. เกณฑ์การยอมรับ (Acceptance Criteria)

- [ ] ต้องมีโครงสร้าง directory `app/` สำหรับเก็บซอร์สโค้ดของ Backend
- [ ] แอปพลิเคชัน FastAPI ต้องสามารถรันได้สำเร็จ
- [ ] ต้องมี API endpoint `GET /health`
- [ ] เมื่อเรียก `GET /health` จะต้องได้รับ HTTP status code `200 OK`
- [ ] Response body ที่ได้จากการเรียก `GET /health` จะต้องเป็น JSON object `{"status": "ok"}`
- [ ] เมื่อเรียก endpoint ที่ไม่มีอยู่จริง (เช่น `/foobar`) จะต้องได้รับ HTTP status code `404 Not Found`

## 5. กรณีตัวอย่าง (Specification by Example - SBE)

### **Scenario 1: การตรวจสอบสถานะของระบบสำเร็จ (Happy Path)**

**GIVEN** Backend application ทำงาน (running) อยู่
**WHEN** ผู้ดูแลระบบส่ง `GET` request ไปยัง `/health`
**THEN** ระบบจะตอบกลับด้วย status `200 OK`
**AND** response body จะต้องเป็น `{"status": "ok"}`

**ตัวอย่าง:**

| Action | `GET /health` |
|---|---|
| **Request Headers** | (any) |
| **Request Body** | (none) |
| **Response Status** | `200 OK` |
| **Response Body** | `{"status": "ok"}` |

---

### **Scenario 2: การเรียกใช้เส้นทาง (Route) ที่ไม่มีอยู่จริง**

**GIVEN** Backend application ทำงาน (running) อยู่
**WHEN** Client ส่ง request ไปยัง endpoint ที่ไม่มีอยู่จริง
**THEN** ระบบจะตอบกลับด้วย status `404 Not Found`

**ตัวอย่าง:**

| Action | Endpoint | Response Status | Response Body (contains) |
|---|---|---|---|
| `GET` | `/` | `404 Not Found` | `{"detail":"Not Found"}` |
| `GET` | `/api/v1/messages` | `404 Not Found` | `{"detail":"Not Found"}` |
| `POST`| `/health` | `405 Method Not Allowed` | `{"detail":"Method Not Allowed"}`|

## 6. สิ่งที่ไม่ได้ทำใน Scope นี้ (Out of Scope)

- การสร้าง API endpoint อื่นๆ นอกเหนือจาก `/health`
- การเชื่อมต่อกับฐานข้อมูล (Database) หรือหน่วยความจำ (Memory store)
- การตั้งค่า CI/CD pipeline สำหรับการ deploy
- การสร้าง Dockerfile สำหรับแอปพลิเคชัน
- การ implement business logic ใดๆ