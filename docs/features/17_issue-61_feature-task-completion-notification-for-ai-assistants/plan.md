# Implementation Plan: [Feature] Task Completion Notification for AI Assistants

> **Refers to**: [Spec Link](./spec.md)
> **Status**: Draft

## 1. Architecture & Design
*High-level technical approach.*

### Component View
- **Modified Components**:
    - `app/services/telegram_service.py`: เพิ่มฟังก์ชันสำหรับส่งข้อความแจ้งเตือนที่จัดรูปแบบ (Formatted Notification).
    - `scripts/akasa_mcp_server.py`: เพิ่มเครื่องมือ `notify_task_complete` เพื่อให้ MCP Clients (เช่น Gemini CLI) เรียกใช้งานได้.
    - `app/routers/notifications.py`: เพิ่ม Endpoint `/api/notify` สำหรับรับคำขอแจ้งเตือนจากภายนอก.
- **New Components**:
    - `app/models/notification.py`: (ถ้ายังไม่มี) หรือแก้ไขให้รองรับ `NotificationRequest` สำหรับรับข้อมูล Task, Status, Project, และ Link.
- **Dependencies**:
    - `python-dotenv`: สำหรับจัดการ API Key/Token ของระบบ.
    - `fastapi`: สำหรับ Endpoint ใหม่.

### Data Model Changes
```python
# app/models/notification.py หรือภายใน router
from pydantic import BaseModel
from typing import Optional

class TaskNotificationRequest(BaseModel):
    project: Optional[str] = "General"
    task: str
    status: str  # success, failure, completed
    link: Optional[str] = None
    source: Optional[str] = "External" # e.g., "Gemini CLI", "Luma CLI"
```

---

## 2. Step-by-Step Implementation

### Step 1: Implement Formatted Telegram Notification Service
- **Docs**: อัปเดต docstring ใน `telegram_service.py`.
- **Code**: เพิ่ม Method `send_task_notification` ใน `TelegramService` โดยใช้ MarkdownV2 และ Emoji ตามสถานะ (✅ สำหรับ success, ❌ สำหรับ failure, 🔔 สำหรับ general).
- **Tests**: `tests/services/test_telegram_service_notification.py` - ทดสอบว่าสร้างข้อความถูกต้องตามเงื่อนไข.

### Step 2: Create HTTP Endpoint `/api/notify`
- **Docs**: ระบุ API Spec ใน `spec.md`.
- **Code**: 
    - สร้าง Endpoint `POST /api/notify` ใน `app/routers/notifications.py`.
    - เพิ่มระบบ Authentication พื้นฐานด้วย API Key ใน Header (e.g., `X-Akasa-Key`).
- **Tests**: `tests/routers/test_notifications.py` - ทดสอบการเรียกใช้ด้วย Valid/Invalid API Key และ Payload.

### Step 3: Integrate Notification Tool in MCP Server
- **Docs**: อัปเดตรายการ Tools ใน `scripts/akasa_mcp_server.py`.
- **Code**: เพิ่มฟังก์ชัน `notify_task_complete` ใน `akasa_mcp_server.py` โดยให้เรียกใช้ `TelegramService` ภายใน.
- **Tests**: `tests/scripts/test_akasa_mcp_server_tools.py` - จำลองการเรียก Tool ผ่าน MCP protocol.

### Step 4: Add MarkdownV2 Sanitization
- **Docs**: -
- **Code**: ตรวจสอบและ Escape ตัวอักษรพิเศษใน `app/utils/markdown_utils.py` เพื่อป้องกัน Telegram API Error เมื่อส่ง MarkdownV2.
- **Tests**: `tests/utils/test_markdown_utils.py` - ทดสอบการ escape อักขระเช่น `_`, `*`, `[`, `]`, `(`, `)`, `~`, `` ` ``, `>`, `#`, `+`, `-`, `=`, `|`, `{`, `}`, `.`, `!`.

---

## 3. Verification Plan
*How will we verify success?*

### Automated Tests
- [ ] **Unit Tests**: ทดสอบ Logic การจัดรูปแบบข้อความใน `TelegramService`.
- [ ] **Integration Tests**: 
    - ทดสอบ `POST /api/notify` โดยใช้ `TestClient`.
    - ทดสอบการทำงานร่วมกับ MCP SDK (Mocking Telegram API calls).

### Manual Verification
- [ ] **Scenario 1 (CLI)**: ใช้ `curl` ส่ง Request ไปยัง `/api/notify` พร้อม API Key และตรวจสอบข้อความใน Telegram Bot.
- [ ] **Scenario 2 (MCP)**: ใช้ `gemini-cli` หรือ MCP Inspector เรียกใช้ tool `notify_task_complete` และตรวจสอบผลลัพธ์.
- [ ] **Rate Limiting**: ทดสอบส่งข้อความรัวๆ เพื่อดูว่าระบบยังทำงานได้เสถียร (ถ้ามี implementation).