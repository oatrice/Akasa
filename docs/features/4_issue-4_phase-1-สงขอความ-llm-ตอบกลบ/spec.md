# Specification: [Phase 1] Core Chat Loop (Message → LLM → Reply)

| | |
|---|---|
| **Feature Name** | [Phase 1] ส่งข้อความ ➡️ LLM ➡️ ตอบกลับ |
| **Issue URL** | [#4](https://github.com/oatrice/Akasa/issues/4) |
| **Status** | **Draft** |
| **Date** | 2026-03-07 |

## 1. เป้าหมาย (The 'Why')

เพื่อทำให้ Akasa Chatbot สามารถโต้ตอบกับผู้ใช้ได้จริงโดยการสร้างวงจรการสนทนาที่สมบูรณ์ (Chat Loop) ซึ่งเป็นฟังก์ชันการทำงานหลักของ MVP (Minimum Viable Product) โดยจะเชื่อมต่อส่วนที่รับข้อความจาก Telegram เข้ากับบริการ AI (LLM) และส่งคำตอบที่สร้างขึ้นกลับไปให้ผู้ใช้

## 2. ผู้ใช้งาน (User Persona)

| Persona | ลักษณะ |
|---|---|
| **End User** | ผู้ใช้งาน Telegram ที่ส่งข้อความเข้ามาเพื่อสนทนาและคาดหวังว่าจะได้รับคำตอบที่ชาญฉลาดกลับไป |
| **The System (Akasa Backend)** | ระบบเบื้องหลังที่ทำหน้าที่เป็นตัวกลางรับ-ส่งข้อมูลระหว่าง Telegram และ OpenRouter API |

## 3. เส้นทางของผู้ใช้ (User Journey)

**ในฐานะ**ผู้ใช้งาน Telegram
**ฉันต้องการ** ส่งคำถามหรือข้อความไปหา Akasa Bot
**เพื่อที่ฉันจะ** ได้รับคำตอบที่ถูกสร้างโดย AI กลับมาในห้องแชทของฉัน

## 4. เกณฑ์การยอมรับ (Acceptance Criteria)

- [ ] เมื่อ Webhook ได้รับข้อความประเภท Text จากผู้ใช้, ระบบจะต้องดึงเนื้อหาข้อความ (`text`) และ `chat.id` ออกมาได้
- [ ] เนื้อหาข้อความนั้นจะต้องถูกส่งเป็น prompt ไปยัง OpenRouter API เพื่อประมวลผล
- [ ] ระบบต้องสามารถดึงคำตอบที่ AI สร้างขึ้นจาก Response ของ OpenRouter API ได้
- [ ] คำตอบจาก AI จะต้องถูกส่งกลับไปหาผู้ใช้ใน `chat.id` เดิม ผ่าน Telegram Bot API
- [ ] Webhook endpoint จะต้องตอบกลับ `200 OK` ให้กับ Telegram ทันทีที่ได้รับ request โดยการประมวลผลที่อาจใช้เวลานาน (เช่น การเรียก LLM) ต้องทำงานอยู่เบื้องหลัง (Background Task)
- [ ] หากเกิดข้อผิดพลาดระหว่างการเรียก API ภายนอก (OpenRouter หรือ Telegram) ระบบจะต้องไม่หยุดทำงาน (crash) และควรมีการบันทึก Log ข้อผิดพลาดไว้

## 5. กรณีตัวอย่าง (Specification by Example - SBE)

### **Scenario 1: การโต้ตอบสำเร็จ (Happy Path)**

**GIVEN** ผู้ใช้ส่งข้อความ "What is Python?" ไปยังบอท
**WHEN** Webhook ได้รับข้อความ, ส่ง "What is Python?" ไปยัง LLM, และ LLM ตอบกลับมาว่า "Python is a programming language."
**THEN** ระบบจะส่งข้อความ "Python is a programming language." กลับไปในห้องแชทของผู้ใช้
**AND** การเรียก Webhook ครั้งแรกจะได้รับ `200 OK` ทันที โดยไม่ต้องรอให้ LLM ประมวลผลเสร็จ

**ตัวอย่าง:**

| Input from Telegram | Action: Call OpenRouter | Action: Call Telegram `sendMessage` |
|---|---|---|
| `{"message": {"text": "What is Python?", "chat": {"id": 123}}}` | **Prompt:** "What is Python?" | **chat_id:** `123`<br>**text:** "Python is a programming language." |

---

### **Scenario 2: ระบบ LLM ภายนอกขัดข้อง**

**GIVEN** ผู้ใช้ส่งข้อความไปยังบอท
**WHEN** ระบบพยายามส่งข้อความนั้นไปยัง OpenRouter API แต่ API ตอบกลับมาเป็น Error (เช่น `500 Internal Server Error`)
**THEN** ระบบจะต้องจัดการ Error นั้น (เช่น บันทึก Log) โดยไม่หยุดทำงาน
**AND** จะไม่มีข้อความใดๆ ถูกส่งกลับไปหาผู้ใช้
**AND** การเรียก Webhook ครั้งแรกจะยังคงได้รับ `200 OK` ตามปกติ

**ตัวอย่าง:**

| Input from Telegram | Action: Call OpenRouter | System Behavior | Action: Call Telegram `sendMessage` |
|---|---|---|---|
| `{"message": {"text": "Why is the sky blue?", "chat": {"id": 456}}}` | **Status:** `503 Service Unavailable` | - Log the error from OpenRouter API<br>- Do not crash | (No call is made) |

## 6. สิ่งที่ไม่ได้ทำใน Scope นี้ (Out of Scope)

- การจดจำบริบทการสนทนา (Conversation Memory) แต่ละข้อความจะถูกจัดการแยกกัน
- การส่งข้อความตอบกลับในรูปแบบอื่นนอกเหนือจากข้อความธรรมดา (เช่น Markdown, รูปภาพ)
- การจัดการคำสั่งพิเศษ เช่น `/start`, `/help`
- การส่ง "Typing..." indicator ขณะที่บอทกำลังประมวลผล
- การส่งข้อความแจ้งผู้ใช้เมื่อเกิดข้อผิดพลาดภายในระบบ