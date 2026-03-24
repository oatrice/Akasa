# Implementation Plan: ตรวจสอบ Kanban และ Roadmap ผ่าน Telegram (/gh + NLP)

> **Refers to**: [Specification: ตรวจสอบ Kanban และ Roadmap ผ่าน Telegram (/gh + NLP)](./spec.md)
> **Status**: Draft

## 1. Architecture & Design
การเพิ่มฟีเจอร์นี้จะเน้นไปที่การขยายความสามารถของ `GitHubService` ในการดึงข้อมูลจาก GitHub Project (ProjectV2) ผ่าน GraphQL และการอ่านไฟล์ Roadmap ทั้งจาก Local และ Remote จากนั้นจึงนำมาเชื่อมต่อกับ `ChatService` (LLM Tools) และ `Command Router`

### Component View
- **GitHubService**: 
    - เพิ่มฟังก์ชัน `get_project_kanban(owner, repo)`: ใช้ GitHub GraphQL API เพื่อดึงข้อมูล ProjectV2 (เนื่องจาก REST API ของ Projects เดิมล้าสมัยและไม่รองรับ ProjectV2 อย่างสมบูรณ์)
    - เพิ่มฟังก์ชัน `get_roadmap_content(owner, repo)`: ค้นหาไฟล์ `docs/ROADMAP.md` หรือ `ROADMAP.md` ใน Repository
- **ChatService (LLM Tools)**: 
    - เพิ่มเครื่องมือ `get_kanban_summary` และ `get_roadmap_summary` เพื่อให้ AI สามารถเรียกใช้งานได้เมื่อผู้ใช้ถามผ่าน NLP
- **Commands Router**: 
    - อัปเดต `/gh` handler ให้รองรับ sub-commands `kanban` และ `roadmap`
- **Markdown Utils**: 
    - ตรวจสอบและปรับปรุงการ Escape ตัวอักษรพิเศษสำหรับ Telegram MarkdownV2

### Data Model Changes
ไม่มีการเปลี่ยนแปลง Database Schema แต่จะมีการนิยาม Data Structure สำหรับสรุปข้อมูล:
```python
class KanbanStatus(BaseModel):
    project_name: str
    columns: List[Dict[str, Any]]  # Name, Count, Recent Items
    url: str

class RoadmapSummary(BaseModel):
    repository: str
    content: str  # สรุปเนื้อหาที่ผ่านการประมวลผลโดย LLM หรือตัดตอนมา
    url: str
```

---

## 2. Step-by-Step Implementation

### Step 1: Research & GitHub GraphQL Client
เนื่องจาก ProjectV2 ของ GitHub ต้องใช้ GraphQL API เป็นหลัก
- **Task**: ตรวจสอบการส่ง GraphQL request ใน `GitHubService` และเตรียม Query สำหรับดึงข้อมูล Columns และ Items ใน ProjectV2
- **Code**: `app/services/github_service.py`
- **Verification**: สร้าง Unit Test เพื่อ Mock GraphQL Response และตรวจสอบการ Parse ข้อมูล

### Step 2: Implement Kanban Fetching Logic
- **Task**: พัฒนา `get_project_kanban` ใน `GitHubService` โดยรองรับการระบุ `owner/repo` และดึง Project ที่ Linked อยู่กับ Repository นั้น
- **Code**: `app/services/github_service.py`
- **Tests**: `tests/services/test_github_service.py` (TDD: เขียนเทสต์จำลองกรณีพบและไม่พบ Project)

### Step 3: Implement Roadmap Fetching (Local-first Strategy)
- **Task**: พัฒนา `get_roadmap_content` โดยมีลำดับคือ 1. ตรวจสอบ Local Path (ถ้ามีการ Bind) 2. ถ้าไม่พบให้ดึงจาก GitHub API
- **Code**: `app/services/github_service.py`, `app/services/redis_service.py` (เพื่อดู Context การ Bind)
- **Tests**: `tests/services/test_github_service.py`

### Step 4: Define LLM Tools in ChatService
- **Task**: เพิ่มฟังก์ชันใน `ChatService` เพื่อเป็น Interface ให้ AI เรียกใช้ (Function Calling)
- **Code**: `app/services/chat_service.py`
- **Verification**: ทดสอบผ่าน `scripts/test_openrouter.py` หรือ Unit Test ของ ChatService

### Step 5: Update Telegram Slash Commands
- **Task**: เพิ่มตรรกะใน `app/routers/commands.py` เพื่อแยกแยะ `/gh kanban` และ `/gh roadmap`
- **Code**: `app/routers/commands.py`
- **Tests**: `tests/routers/test_commands.py`

### Step 6: Markdown Formatting & Escaping
- **Task**: ปรับแต่งการแสดงผลให้สวยงามบน Telegram (ใช้ Emoji และ List) และตรวจสอบการ Escape อักขระพิเศษ
- **Code**: `app/utils/markdown_utils.py`
- **Verification**: รัน `test_escape.py` เพื่อยืนยันว่าข้อความไม่ Error เมื่อส่งไป Telegram

---

## 3. Verification Plan

### Automated Tests
- **Unit Tests**:
    - `tests/services/test_github_service.py`: ทดสอบการดึงข้อมูล Kanban (Mock GraphQL) และ Roadmap (Mock File/API)
    - `tests/services/test_chat_service_tools.py`: ทดสอบว่า AI เลือกใช้ Tool ถูกต้องตาม Intent ของผู้ใช้
- **Integration Tests**:
    - `tests/routers/test_commands.py`: ทดสอบการเรียกคำสั่งผ่าน Router และการคืนค่า Response ที่ถูกต้อง

### Manual Verification
- [ ] พิมพ์ `/gh kanban` ใน Telegram Bot (กรณี Bind โปรเจกต์ Akasa ไว้)
- [ ] พิมพ์ `/gh roadmap google/jax` เพื่อดู Roadmap ของโปรเจกต์อื่น
- [ ] พิมพ์ถาม AI: "งานใน Akasa ตอนนี้ถึงไหนแล้ว?" (เช็คการเรียก Kanban Tool)
- [ ] พิมพ์ถาม AI: "สรุปแผนงานของโปรเจกต์นี้ให้หน่อย" (เช็คการเรียก Roadmap Tool)
- [ ] ตรวจสอบว่าลิงก์ที่ส่งมาสามารถคลิกไปที่ GitHub ได้จริง

---

## 🚧 Constraints & Considerations
- **GraphQL API Token**: ตรวจสอบว่า `GITHUB_TOKEN` ใน `.env` มี Scope `read:project`
- **Token Usage**: สำหรับการสรุป Roadmap ที่ยาวมาก ต้องระวังการใช้ Token ของ LLM (ควรตัดส่วนสำคัญหรือใช้ System Prompt จำกัดความยาว)