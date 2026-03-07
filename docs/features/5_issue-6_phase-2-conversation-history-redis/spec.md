# Specification: [Phase 2] Conversation History with Redis

| | |
|---|---|
| **Feature Name** | [Phase 2] Conversation history (Redis) |
| **Issue URL** | [#6](https://github.com/oatrice/Akasa/issues/6) |
| **Status** | **Draft** |
| **Date** | 2026-03-07 |

## 1. เป้าหมาย (The 'Why')

เพื่อยกระดับ Akasa Chatbot จากระบบถาม-ตอบแบบครั้งเดียว (stateless) ให้เป็นผู้ช่วยสนทนาที่สามารถจดจำบริบทได้ (stateful) การเพิ่ม "ความจำ" นี้จะช่วยให้บอทเข้าใจคำถามต่อเนื่อง (follow-up questions) และให้คำตอบที่สอดคล้องกับเรื่องที่คุยกันอยู่ ซึ่งเป็นหัวใจสำคัญในการสร้างประสบการณ์การใช้งานที่เป็นธรรมชาติและมีประสิทธิภาพมากขึ้น

## 2. ผู้ใช้งาน (User Persona)

| Persona | ลักษณะ |
|---|---|
| **End User** | ผู้ใช้งานที่ต้องการสนทนากับบอทอย่างต่อเนื่อง และคาดหวังว่าบอทจะเข้าใจบริบทจากการสนทนาก่อนหน้า |
| **The System (Akasa Backend)** | ระบบเบื้องหลังที่ต้องรับผิดชอบในการจัดเก็บและดึงประวัติการสนทนาสำหรับผู้ใช้แต่ละคน |

## 3. เส้นทางของผู้ใช้ (User Journey)

**ในฐานะ**ผู้ใช้งาน
**ฉันต้องการ** ให้บอทจดจำสิ่งที่ฉันเพิ่งพูดไป
**เพื่อที่ฉันจะ** สามารถถามคำถามต่อเนื่องได้โดยไม่ต้องอธิบายซ้ำทั้งหมด

## 4. เกณฑ์การยอมรับ (Acceptance Criteria)

- [ ] ก่อนส่งข้อความไปให้ LLM, ระบบจะต้องดึงประวัติการสนทนาล่าสุด (เช่น 10 ข้อความหลังสุด) สำหรับ `chat_id` นั้นๆ มาด้วย
- [ ] ประวัติการสนทนาที่ดึงมาจะต้องถูกรวมเข้ากับข้อความใหม่ของผู้ใช้เพื่อสร้างเป็นบริบทที่สมบูรณ์สำหรับ LLM
- [ ] หลังจาก LLM ตอบกลับ, ทั้งข้อความของผู้ใช้และคำตอบของบอทจะต้องถูกบันทึกกลับเข้าไปในประวัติการสนทนาของ `chat_id` นั้นๆ
- [ ] ประวัติการสนทนาจะต้องถูกจำกัดขนาด เพื่อป้องกันไม่ให้บริบทยาวเกินความจำเป็น (e.g., เก็บไว้ไม่เกิน 5 คู่การสนทนา)
- [ ] หากผู้ใช้เริ่มการสนทนาใหม่ (ไม่มีประวัติเดิม), ระบบจะต้องทำงานได้ตามปกติ
- [ ] หากระบบจัดเก็บประวัติขัดข้อง, ระบบควรจะยังสามารถตอบคำถามของผู้ใช้ได้ (แบบไม่มีบริบท) โดยไม่หยุดทำงาน

## 5. กรณีตัวอย่าง (Specification by Example - SBE)

### **Scenario 1: การถามคำถามต่อเนื่องสำเร็จ (Happy Path)**

**GIVEN** ผู้ใช้ได้สนทนากับบอท และประวัติการสนทนาล่าสุดถูกบันทึกไว้
**WHEN** ผู้ใช้ถามคำถามต่อเนื่องที่อ้างอิงถึงบริบทเดิม (เช่น ถามว่า "แล้วมันใช้ทำอะไรได้บ้าง?")
**THEN** ระบบจะดึงประวัติการสนทนามาประกอบกับคำถามใหม่ และส่งให้ LLM
**AND** LLM จะให้คำตอบที่ถูกต้องตามบริบท และบอทจะส่งคำตอบนั้นกลับไปให้ผู้ใช้

**ตัวอย่าง:**

| Step | User Action | System's Context sent to LLM | Bot's Reply |
|---|---|---|---|
| 1 | "Tell me about FastAPI." | `messages: [{"role": "user", "content": "Tell me about FastAPI."}]` | "FastAPI is a modern, fast web framework for building APIs with Python..." |
| 2 | "What are its key features?" | `messages: [{"role": "user", ...}, {"role": "assistant", ...}, {"role": "user", "content": "What are its key features?"}]` | "Its key features include automatic docs, type hints, and high performance." |

---

### **Scenario 2: การสนทนาถูกแยกตามผู้ใช้แต่ละคน (Isolation)**

**GIVEN** User-A กำลังคุยเรื่อง "Python" กับบอทใน Chat-123
**WHEN** User-B ส่งข้อความ "Tell me about it" ไปยังบอทใน Chat-456
**THEN** ระบบจะต้องไม่นำบริบทของ User-A มาใช้ในการตอบ User-B
**AND** คำตอบของบอทที่ส่งให้ User-B ควรจะเป็นการขอข้อมูลเพิ่มเติมเนื่องจากไม่มีบริบท

**ตัวอย่าง:**

| User & Chat | User Action | System's Context sent to LLM | Bot's Reply |
|---|---|---|---|
| **User-A** (Chat-123) | "What is Django?" | `messages: [{"role": "user", "content": "What is Django?"}]` | "Django is a high-level Python web framework..." |
| **User-B** (Chat-456) | "What is it good for?" | `messages: [{"role": "user", "content": "What is it good for?"}]` | "What is 'it' you are referring to? I don't have previous context for our conversation." |

## 6. สิ่งที่ไม่ได้ทำใน Scope นี้ (Out of Scope)

- การสรุปประวัติการสนทนาเพื่อลดจำนวน token
- การจัดเก็บประวัติการสนทนาแบบถาวรในฐานข้อมูล (Persistent Database)
- การให้ผู้ใช้สามารถล้างประวัติการสนทนาของตนเองได้ (e.g., via `/clear` command)
- การใช้ vector search เพื่อค้นหาบริบทที่เกี่ยวข้องจากประวัติที่ยาวมากๆ