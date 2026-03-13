# SBE: Task Completion Notification for AI Assistants

> 📅 Created: 2026-03-13
> 🔗 Issue: https://github.com/oatrice/Akasa/issues/61

---

## Feature: Task Completion Notification for AI Assistants

ระบบแจ้งเตือนผู้ใช้งานผ่าน Telegram เมื่อ AI Assistants (เช่น Antigravity IDE, Gemini CLI หรือ Luma CLI) ทำงานตามที่ได้รับมอบหมายเสร็จสิ้น เพื่อให้ผู้ใช้งานทราบสถานะของงานได้ทันทีโดยไม่ต้องตรวจสอบด้วยตนเองตลอดเวลา ผ่านการเรียกใช้ MCP Tool หรือ HTTP Endpoint

### Scenario: Happy Path - แจ้งเตือนสำเร็จผ่าน MCP Tool

**Given** ระบบ Akasa Backend และ Telegram Bot ทำงานปกติ และ AI Assistant เชื่อมต่อกับ Akasa MCP Server เรียบร้อยแล้ว
**When** AI Assistant เรียกใช้ Tool `notify_task_complete` พร้อมระบุชื่อโปรเจกต์ รายละเอียดงาน และระยะเวลาที่ใช้
**Then** ผู้ใช้งานได้รับข้อความแจ้งเตือนผ่าน Telegram โดยมีรูปแบบข้อความที่ถูกต้องและครบถ้วน

#### Examples

| project | task_description | duration | expected_telegram_message |
|-------|----------|----------|----------|
| Akasa | Refactor Redis Service and add unit tests | 5m 20s | ✅ **Task Completed!**\n\n**Project:** Akasa\n**Task:** Refactor Redis Service and add unit tests\n**Duration:** 5m 20s |
| Luma CLI | Create Pull Request #42 for feature-auth | 1m 15s | ✅ **Task Completed!**\n\n**Project:** Luma CLI\n**Task:** Create Pull Request #42 for feature-auth\n**Duration:** 1m 15s |
| Antigravity | Analyze codebase for security vulnerabilities | 12m 45s | ✅ **Task Completed!**\n\n**Project:** Antigravity\n**Task:** Analyze codebase for security vulnerabilities\n**Duration:** 12m 45s |
| Gemini CLI | Update documentation for API v2 | 3m 10s | ✅ **Task Completed!**\n\n**Project:** Gemini CLI\n**Task:** Update documentation for API v2\n**Duration:** 3m 10s |

### Scenario: Edge Cases - ข้อมูลไม่ครบถ้วนหรือยาวเกินกำหนด

**Given** AI Assistant ทำงานเสร็จสิ้นแต่ระบุข้อมูลบางส่วนไม่ครบถ้วน หรือข้อมูลมีความยาวมากกว่าปกติ
**When** AI Assistant เรียกใช้ Tool `notify_task_complete` หรือส่ง Request ไปยัง `/api/notify`
**Then** ระบบต้องจัดการข้อมูล (เช่น ใส่ค่า Default หรือตัดข้อความ) และส่งแจ้งเตือนไปยัง Telegram ได้โดยไม่ Error

#### Examples

| project | task_description | duration | expected_outcome |
|-------|----------|----------|----------|
| Akasa | Task with very long description... (มากกว่า 500 ตัวอักษร) | 10s | แจ้งเตือนสำเร็จโดยตัดข้อความ (Truncated) |
| Unknown | Deploying application | [NULL] | แจ้งเตือนสำเร็จโดยใช้ค่า Duration เป็น "N/A" |
| A | B | 0s | แจ้งเตือนสำเร็จด้วยข้อมูลขั้นต่ำ |
| Project-X | Special characters: !@#$%^&*() | 1m | แจ้งเตือนสำเร็จและแสดงผลอักขระพิเศษถูกต้อง |

### Scenario: Error Handling - การส่งข้อมูลไม่ถูกต้องหรือระบบปลายทางขัดข้อง

**Given** AI Assistant พยายามส่งการแจ้งเตือนแต่ไม่ได้ระบุข้อมูลสำคัญ หรือ Telegram API ไม่สามารถใช้งานได้
**When** AI Assistant เรียกใช้ Tool หรือ Endpoint ด้วยข้อมูลที่ผิดพลาด
**Then** ระบบต้องตอบกลับด้วย Error Message ที่เหมาะสม เพื่อให้ AI Assistant รับทราบความล้มเหลว

#### Examples

| input_data | missing_field | system_state | error_msg |
|-------|-------|-------|-------|
| {"duration": "5m"} | project, task_description | Normal | "Missing required fields: project, task_description" |
| {"project": "Akasa", "task": "Done"} | None | Telegram Token Invalid | "Failed to send Telegram message: Unauthorized" |
| {} | all | Normal | "Request body cannot be empty" |
| {"project": "Akasa", "task": "Done", "duration": 123} | None (Wrong type) | Normal | "Invalid data type for duration: expected string" |