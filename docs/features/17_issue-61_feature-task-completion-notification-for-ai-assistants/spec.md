# Specification: [Feature] Task Completion Notification for AI Assistants

## 1. ข้อมูลทั่วไป (Overview)
**ชื่อฟีเจอร์:** Task Completion Notification for AI Assistants
**Issue URL:** https://github.com/oatrice/Akasa/issues/61
**สถานะ:** Draft
**ผู้รับผิดชอบ:** Product Manager / Systems Analyst

### 1.1 ความเป็นมา (Context)
ในปัจจุบัน เมื่อ AI Assistant อย่าง Antigravity IDE หรือ Gemini CLI ทำงานตามที่ได้รับมอบหมายเสร็จสิ้น กระบวนการจะจบลงเงียบๆ (Silent completion) ทำให้ผู้ใช้งานไม่ทราบสถานะที่แน่นอนหากไม่ได้เฝ้าหน้าจอตลอดเวลา ฟีเจอร์นี้จึงมุ่งเน้นการสร้างระบบการแจ้งเตือนผ่าน Telegram เพื่อให้ผู้ใช้ทราบทันทีเมื่อภารกิจสำเร็จ

### 1.2 เป้าหมาย (Goal)
- เพื่อให้ผู้ใช้ได้รับแจ้งเตือนผ่าน Telegram ทันทีเมื่อ AI Assistant ทำงานเสร็จสิ้น
- เพื่อลดเวลาที่ผู้ใช้ต้องรอคอยหรือตรวจสอบสถานะด้วยตนเอง
- เพื่อเพิ่มความต่อเนื่องในการทำงาน (Workflow Continuity) โดยผู้ใช้สามารถดำเนินการขั้นถัดไปได้ทันที

---

## 2. เส้นทางของผู้ใช้งาน (User Journey)
1. **Trigger:** ผู้ใช้สั่งงาน AI Assistant (เช่น ให้เขียนโค้ดหรือแก้ไขบั๊ก)
2. **Process:** AI Assistant ดำเนินการตามขั้นตอนจนครบถ้วน
3. **Notification:** 
    - AI Assistant เรียกใช้เครื่องมือแจ้งเตือน (MCP Tool) หรือส่ง Request ไปยัง Akasa Backend
    - ระบบ Akasa ส่งข้อความสรุปผลการทำงานไปยัง Telegram ของผู้ใช้
4. **Outcome:** ผู้ใช้ได้รับข้อความแจ้งเตือนบนมือถือ/คอมพิวเตอร์ และทราบว่างานเสร็จสิ้นแล้ว

---

## 3. พฤติกรรมของระบบ (System Behavior)

### 3.1 การรับข้อมูลการแจ้งเตือน
- ระบบต้องรองรับการส่งข้อมูลผ่าน 2 ช่องทางหลัก:
    1. **MCP Tool:** สำหรับ AI Agents ที่รองรับ Model Context Protocol (เช่น Gemini CLI)
    2. **HTTP Endpoint:** สำหรับ CLI หรือเครื่องมือภายนอก (เช่น Luma CLI) ที่ต้องการส่งสถานะผ่าน Webhook

### 3.2 ข้อมูลที่ต้องแสดงในข้อความ (Message Content)
ข้อความแจ้งเตือนควรประกอบด้วย:
- **Project Name:** ชื่อโปรเจกต์ที่กำลังทำงานอยู่
- **Task Summary:** สรุปสั้นๆ ว่างานที่เสร็จคืออะไร
- **Status:** สถานะการจบงาน (เช่น Success, Completed with warnings)
- **Direct Link (ถ้ามี):** เช่น Link ไปยัง PR ที่ถูกสร้าง หรือไฟล์ที่ถูกแก้ไข

---

## 4. การแสดงพฤติกรรมด้วยตัวอย่าง (Specification by Example - SBE)

### Scenario 1: การแจ้งเตือนเมื่อ Gemini CLI ทำงานสำเร็จผ่าน MCP Tool
**Given:** Gemini CLI กำลังทำงานในโปรเจกต์ "Akasa" และได้รับคำสั่งให้ "Refactor Telegram Service"
**When:** Gemini CLI ดำเนินการเสร็จสิ้นและเรียกใช้เครื่องมือ `notify_task_complete`
**Then:** ผู้ใช้จะได้รับข้อความใน Telegram พร้อมรายละเอียดของงาน

| Project | Task Description | Tool Called | Telegram Output (Example) |
| :--- | :--- | :--- | :--- |
| Akasa | Refactor Telegram Service | `notify_task_complete` | ✅ **Task Completed: Akasa**<br>Refactor Telegram Service is finished. |
| MyWeb | Update README.md | `notify_task_complete` | ✅ **Task Completed: MyWeb**<br>Update README.md is finished. |

### Scenario 2: การแจ้งเตือนจาก Luma CLI เมื่อสร้าง Artifacts สำเร็จผ่าน HTTP API
**Given:** Luma CLI กำลังรัน Workflow การสร้าง Build Artifacts
**When:** ขั้นตอน 'Archive Artifacts' สำเร็จ และ Luma CLI ส่ง POST request ไปที่ `/api/notify`
**Then:** ระบบ Akasa จะส่งข้อความแจ้งเตือนสถานะความสำเร็จไปยัง Telegram

| Endpoint | Method | Payload (Source) | Telegram Output (Example) |
| :--- | :--- | :--- | :--- |
| `/api/notify` | POST | `{"task": "Archive Artifacts", "status": "success"}` | 🔔 **Luma CLI Notification**<br>Task: Archive Artifacts<br>Status: Success |
| `/api/notify` | POST | `{"task": "Create PR", "status": "completed"}` | 🔔 **Luma CLI Notification**<br>Task: Create PR<br>Status: Completed |

---

## 5. กฎทางธุรกิจ (Business Rules / Constraints)
- **Authentication:** การเรียกใช้ Endpoint `/api/notify` ต้องมีการตรวจสอบความปลอดภัย (เช่น API Key หรือ Token) เพื่อป้องกันการส่งข้อความรบกวน (Spam)
- **Rate Limiting:** จำกัดจำนวนการแจ้งเตือนต่อนาทีเพื่อไม่ให้ระบบ Telegram Bot ถูกแบน
- **Formatting:** ข้อความต้องอยู่ในรูปแบบ MarkdownV2 เพื่อให้แสดงผลได้สวยงามและอ่านง่ายบน Telegram

---

## 6. คำถามที่ยังต้องการคำตอบ (Open Questions)
- จำเป็นต้องมีการเก็บประวัติการแจ้งเตือน (Notification History) ในฐานข้อมูลหรือไม่?
- ควรมีการแจ้งเตือนในกรณีที่งาน "ล้มเหลว" (Failure Notification) ด้วยรูปแบบที่ต่างออกไปหรือไม่? (เช่น ใช้ Emoji ❌ แทน ✅)