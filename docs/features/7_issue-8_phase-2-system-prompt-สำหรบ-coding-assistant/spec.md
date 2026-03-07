# Specification: [Phase 2] System Prompt for Coding Assistant

| | |
|---|---|
| **Feature Name** | [Phase 2] System prompt สำหรับ coding assistant |
| **Issue URL** | [#8](https://github.com/oatrice/Akasa/issues/8) |
| **Status** | **Draft** |
| **Date** | 2026-03-08 |

## 1. เป้าหมาย (The 'Why')

เพื่อกำหนดบุคลิก (Persona) และแนวทางการตอบของ Akasa Chatbot ให้มีความสม่ำเสมอและตรงกับวัตถุประสงค์ของการเป็น "ผู้ช่วยเขียนโค้ด" การใช้ System Prompt เพื่อสั่งให้ LLM ตอบอย่างกระชับ, เน้นทางเทคนิค, และใช้ Code Block อย่างถูกต้อง จะช่วยเพิ่มคุณภาพและความน่าเชื่อถือของคำตอบ ทำให้ผู้ใช้ได้รับประสบการณ์ที่ดีขึ้น

## 2. ผู้ใช้งาน (User Persona)

| Persona | ลักษณะ |
|---|---|
| **End User** | ผู้ใช้งานที่ต้องการคำตอบที่แม่นยำ, ตรงประเด็น, และมีรูปแบบที่เหมาะกับการเขียนโค้ด มากกว่าคำตอบแบบ AI ทั่วไป |
| **System Owner** | ผู้ที่ต้องการควบคุมและปรับแต่งบุคลิกของบอทให้มีคุณภาพสม่ำเสมอในทุกการสนทนา |

## 3. เส้นทางของผู้ใช้ (User Journey)

**ในฐานะ**ผู้ใช้งาน
**ฉันต้องการ** ให้บอทตอบคำถามเหมือนผู้เชี่ยวชาญด้านการเขียนโค้ด
**เพื่อที่ฉันจะ** ได้รับคำตอบที่กระชับ, นำไปใช้ได้จริง, และไม่ต้องเสียเวลาอ่านคำอธิบายที่ไม่จำเป็น

## 4. เกณฑ์การยอมรับ (Acceptance Criteria)

- [ ] ก่อนการเรียก LLM ทุกครั้ง, จะต้องมี "System Prompt" ถูกเพิ่มเข้าไปเป็นข้อความแรกสุดในชุดข้อความที่จะส่งไปประมวลผล
- [ ] System Prompt ที่เพิ่มเข้าไปจะต้องมี `role` เป็น `system`
- [ ] ประวัติการสนทนา (จาก Redis) และข้อความใหม่ของผู้ใช้ จะต้องถูกวางต่อจาก System Prompt ตามลำดับ
- [ ] System Prompt จะต้อง **ไม่ถูก** บันทึกซ้ำลงในประวัติการสนทนาใน Redis เพื่อป้องกันข้อมูลซ้ำซ้อนและสิ้นเปลืองหน่วยความจำ

## 5. กรณีตัวอย่าง (Specification by Example - SBE)

### **Scenario 1: การสนทนาครั้งแรกได้รับอิทธิพลจาก System Prompt**

**GIVEN** ระบบมีการตั้งค่า System Prompt ว่า "You are a helpful coding assistant. Be concise."
**WHEN** ผู้ใช้ส่งข้อความแรก "What is FastAPI?"
**THEN** ระบบจะส่งข้อความที่มีทั้ง System Prompt และข้อความของผู้ใช้ไปยัง LLM
**AND** คำตอบที่ได้จาก LLM จะสั้นกระชับและตรงประเด็นตามคำสั่ง

**ตัวอย่าง:**

| Input from User | `messages` array sent to LLM | Expected Bot Reply (Concise) |
|---|---|---|
| "What is FastAPI?" | `[<br>  {"role": "system", "content": "You are a helpful coding assistant. Be concise."},<br>  {"role": "user", "content": "What is FastAPI?"}<br>]` | "A modern, fast web framework for building APIs with Python." |

---

### **Scenario 2: System Prompt ถูกใช้ร่วมกับประวัติการสนทนา**

**GIVEN** ระบบมี System Prompt และมีประวัติการสนทนาใน Redis แล้ว
**WHEN** ผู้ใช้ส่งคำถามต่อเนื่อง
**THEN** ระบบจะสร้างชุดข้อความโดยเรียงลำดับดังนี้: 1. System Prompt, 2. ประวัติการสนทนาจาก Redis, 3. ข้อความใหม่ของผู้ใช้

**ตัวอย่าง:**

| History in Redis | New User Message | `messages` array sent to LLM |
|---|---|---|
| `[<br> {"role": "user", "content": "Tell me about Python."},<br> {"role": "assistant", "content": "A versatile programming language."}<br>]` | "What about its typing?" | `[<br>  {"role": "system", "content": "You are a helpful coding assistant..."},<br>  {"role": "user", "content": "Tell me about Python."},<br>  {"role": "assistant", "content": "A versatile programming language."},<br>  {"role": "user", "content": "What about its typing?"}<br>]` |

## 6. สิ่งที่ไม่ได้ทำใน Scope นี้ (Out of Scope)

- การให้ผู้ใช้สามารถกำหนด System Prompt ของตนเองได้
- การเปลี่ยน System Prompt แบบไดนามิกระหว่างการสนทนา
- การสรุปประวัติการสนทนาเพื่อลดจำนวน token (ยังคงส่งประวัติไปทั้งหมดตามที่กำหนด)