You are a Senior Software Architect.
Your goal is to write a Technical Implementation Plan (`plan.md`) based on the provided Specification.

---
### 📜 CONSTITUTION (RULES)

---

### INSTRUCTIONS
1. Read the **Specification** carefully.
2. Fill out the **Implementation Plan Template**.
3. **Step-by-Step**: Break down the implementation into atomic, testable steps.
4. **Files**: Explicitly mention which files need creation or modification.
5. **Verification**: Define how each step will be verified.
6. Output ONLY the markdown content.


    Please generate the Implementation Plan for this Spec:
    
    ---
    SPECIFICATION:
    # Specification: [Phase 1] ทดสอบการเชื่อมต่อ OpenRouter API

| | |
|---|---|
| **Feature Name** | [Phase 1] สมัคร OpenRouter + ทดสอบ API |
| **Issue URL** | [#1](https://github.com/oatrice/Akasa/issues/1) |
| **Status** | **Draft** |
| **Date** | 2026-03-07 |

## 1. เป้าหมาย (The 'Why')

เพื่อตรวจสอบและยืนยันว่าระบบสามารถเชื่อมต่อกับ **OpenRouter API** ได้อย่างถูกต้อง และสามารถเรียกใช้งาน LLM (โมเดลภาษาขนาดใหญ่) ที่เป็นโมเดลฟรีได้สำเร็จ นี่เป็นขั้นตอนการพิสูจน์แนวคิด (Proof of Concept) ที่สำคัญเพื่อลดความเสี่ยงทางเทคนิคก่อนที่จะเริ่มพัฒนาระบบ Backend หลัก

## 2. ผู้ใช้งาน (User Persona)

| Persona | ลักษณะ |
|---|---|
| **Developer (นักพัฒนา)** | ผู้ที่รับผิดชอบการตั้งค่าเริ่มต้นของโปรเจกต์ และต้องการสร้างเครื่องมือเพื่อยืนยันว่าการเชื่อมต่อกับบริการภายนอก (Third-party) ทำงานได้ตามที่คาดหวัง |

## 3. เส้นทางของผู้ใช้ (User Journey)

**ในฐานะ**นักพัฒนา
**ฉันต้องการ** รันสคริปต์เพื่อทดสอบการเรียก API ของ OpenRouter ด้วย API Key ของฉัน
**เพื่อที่ฉันจะ** สามารถมั่นใจได้ว่าการเชื่อมต่อสำเร็จและพร้อมสำหรับนำไปใช้เป็นส่วนประกอบหลักใน Backend ของแอปพลิเคชัน Akasa

## 4. เกณฑ์การยอมรับ (Acceptance Criteria)

- [ ] ต้องมีสคริปต์สำหรับทดสอบการเชื่อมต่อ API (`scripts/test_openrouter.py`)
- [ ] เมื่อรันสคริปต์ด้วย API Key ที่ถูกต้อง สคริปต์จะต้องได้รับสถานะ `HTTP 200 OK` กลับมา
- [ ] ผลลัพธ์ที่ได้รับจาก API ต้องเป็น JSON object ที่มีโครงสร้างถูกต้องและมีข้อความที่ AI สร้างขึ้นตอบกลับมาในส่วน `choices[0].message.content`
- [ ] เมื่อรันสคริปต์ด้วย API Key ที่**ไม่**ถูกต้อง สคริปต์จะต้องจัดการข้อผิดพลาดและแสดงผลสถานะ `HTTP 401 Unauthorized`
- [ ] API Key จะต้องไม่ถูกเก็บไว้ในโค้ดโดยตรง (No Hardcoding) แต่ต้องถูกเรียกมาจาก Environment Variable

## 5. กรณีตัวอย่าง (Specification by Example - SBE)

### **Scenario 1: การเรียก API สำเร็จด้วย Key ที่ถูกต้อง**

**GIVEN** นักพัฒนามี `OPENROUTER_API_KEY` ที่ถูกต้องและใช้งานได้
**AND** Key ดังกล่าวถูกตั้งค่าไว้ใน Environment Variable ของระบบ
**WHEN** นักพัฒนารันสคริปต์ทดสอบเพื่อส่งคำถามไปยังโมเดลฟรี
**THEN** ระบบควรได้รับ Response `HTTP 200 OK`
**AND** ผลลัพธ์ที่แสดงผลออกมาควรมีข้อความที่สร้างโดย AI

**ตัวอย่าง:**

| Action | `POST /api/v1/chat/completions` |
|---|---|
| **Request Headers** | `Authorization: Bearer <VALID_API_KEY>`<br>`Content-Type: application/json` |
| **Request Body** | ```json<br>{<br>  "model": "mistralai/mistral-7b-instruct:free",<br>  "messages": [<br>    {"role": "user", "content": "What is the capital of Thailand?"}<br>  ]<br>}``` |
| **Response Status** | `200 OK` |
| **Response Body (Example)** | ```json<br>{<br>  "id": "gen-abc123...",<br>  "model": "mistralai/mistral-7b-instruct:free",<br>  "choices": [<br>    {<br>      "message": {<br>        "role": "assistant",<br>        "content": "The capital of Thailand is Bangkok."<br>      }<br>    }<br>  ]<br>}``` |

---

### **Scenario 2: การเรียก API ผิดพลาดด้วย Key ที่ไม่ถูกต้อง**

**GIVEN** นักพัฒนามี `OPENROUTER_API_KEY` ที่**ไม่**ถูกต้อง (อาจจะพิมพ์ผิด, ยกเลิกไปแล้ว, หรือไม่มีอยู่จริง)
**AND** Key ดังกล่าวถูกตั้งค่าไว้ใน Environment Variable
**WHEN** นักพัฒนารันสคริปต์ทดสอบ
**THEN** ระบบควรได้รับ Response `HTTP 401 Unauthorized`
**AND** ควรมีการแสดงข้อความผิดพลาดที่บ่งชี้ว่าการยืนยันตัวตนล้มเหลว

**ตัวอย่าง:**

| Action | `POST /api/v1/chat/completions` |
|---|---|
| **Request Headers** | `Authorization: Bearer <INVALID_API_KEY>` |
| **Request Body** | ```json<br>{<br>  "model": "mistralai/mistral-7b-instruct:free",<br>  "messages": [<br>    {"role": "user", "content": "Test prompt"}<br>  ]<br>}``` |
| **Response Status** | `401 Unauthorized` |
| **Response Body (Example)** | ```json<br>{<br>  "error": {<br>    "message": "Incorrect API key provided...",<br>    "type": "invalid_request_error",<br>    "code": "invalid_api_key"<br>  }<br>}``` |

## 6. สิ่งที่ไม่ได้ทำใน Scope นี้ (Out of Scope)

- การสร้าง Backend Server (FastAPI) ที่สมบูรณ์
- การเชื่อมต่อกับ Messaging Platform (LINE, Telegram)
- การจัดการประวัติการสนทนา (Conversation History)
- การนำสคริปต์ไป Deploy บน Production
- การทดสอบกับโมเดลที่ต้องเสียเงิน
    
    ---
    TEMPLATE:
    # Implementation Plan

[Template not found]
    
