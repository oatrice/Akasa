# 🏗️ Multi-Project Support Architecture (v0.7.1)

> **Objective**: พัฒนา Akasa จากแชทบอทแบบคุยทีละคน (1-on-1) สู่การเป็น **"Project Orchestrator"** ที่สามารถจัดการหลายโปรเจ็กต์ (Repo) ได้อย่างอิสระและเป็นระเบียบ

---

## 🏛️ Design Philosophy: "1 Bot, Many Contexts"

เราจะใช้ **"Logical Project Context"** เป็นตัวแบ่งงาน โดยที่ User ไม่ต้องสร้าง Bot ใหม่ แต่จะใช้การสลับ Context (Context Switching) ภายใน Bot ตัวเดิม

### 📍 Chat Patterns (รูปแบบการใช้งาน)

1.  **Private Chat (1-on-1)**:
    - **Logic**: 1 User สามารถมีได้หลายโปรเจ็กต์ (N Projects)
    - **UI**: ใช้คำสั่ง `/project select <name>` เพื่อสลับโปรเจ็กต์ที่ต้องการคุยในขณะนั้น
    - **Context Persistence**: บอทจะจำ "โปรเจ็กต์ล่าสุด" ที่ User เลือกไว้ใน Redis

2.  **Group Chat (Collaborative)**:
    - **Logic**: 1 Group Chat = 1 Project (1-on-1 mapping)
    - **UI**: เมื่อดึงบอทเข้ากลุ่ม บอทจะใช้ `chat_id` ของกลุ่มเป็น Project ID โดยอัตโนมัติ
    - **Cross-Reference**: สมาชิกในกลุ่มคุยเรื่องเดียวกัน ข้อมูลเดียวกัน (Shared Context)

---

## 💾 Redis Key Schema (New Structure)

เพื่อให้ระบบ Scalable เราจะเปลี่ยนโครงสร้าง Key จากเดิมที่ผูกแค่ `chat_id` ให้เพิ่มระดับของ `project_name` เข้าไป:

| Feature | Key Pattern | Description |
|---------|-------------|-------------|
| **Current Project** | `user_current_project:{chat_id}` | เก็บชื่อโปรเจ็กต์ที่ Active อยู่ใน Private Chat |
| **Chat History** | `chat_history:{chat_id}:{project_name}` | แยกประวัติแชทตามโปรเจ็กต์ |
| **Project Settings**| `project_config:{chat_id}:{project_name}` | เก็บ Repo URL, Build command, ฯลฯ |
| **Project List** | `user_projects:{chat_id}` | รายชื่อโปรเจ็กต์ทั้งหมดของ User |

---

## 🔄 Cross-Project Interaction (การรวมโปรเจ็กต์)

ในกรณีที่โปรเจ็กต์มีการ Integrate กัน:
- **Project Merging**: รองรับการย้าย (Migration) ของ Redis Keys จาก Project A ไปรวมกับ Project B
- **Global Context Injection**: เมื่อบอทอยู่ใน Project A บอทสามารถ "แอบดู" หรือดึงสรุป (Summary) จาก Project B มาช่วยตอบได้ผ่าน Tool-calling

---

## ✅ Acceptance Criteria (AC) สำหรับ Issue #17

- [ ] **AC 1**: สามารถสร้างโปรเจ็กต์ใหม่ผ่านคำสั่ง `/project new <name>`
- [ ] **AC 2**: ประวัติการคุย (History) ใน Project A ต้องไม่ปนกับ Project B เมื่อสลับ Context
- [ ] **AC 3**: ใน Group Chat บอทต้องจำแนกโปรเจ็กต์ได้ทันทีโดยไม่ต้องสั่ง `/project select`
- [ ] **AC 4**: เมื่อเรียก LLM ระบบต้องส่งข้อมูล "Current Project" ไปใน System Prompt เพื่อให้ AI รู้ตัว

---

## 🚀 Remote Orchestration Bridge (#30 & #29)

เพื่อให้ Akasa คุยกับโลกภายนอกได้ (Laptop-to-Mobile):
1. **Outbound Push**: `TelegramService` ต้องรองรับการส่งข้อความหา User โดยไม่ต้องรอการตอบกลับ (Proactive)
2. **API Endpoint**: `POST /api/v1/notify` ต้องมีระบบความปลอดภัยด้วย API Key และสามารถระบุเป้าหมาย `project_name` เพื่อให้ข้อความไปโผล่ใน Context ที่ถูกต้อง

---

**Status**: Ready for Implementation
**Assignee**: Senior AI Engineer / Architect
