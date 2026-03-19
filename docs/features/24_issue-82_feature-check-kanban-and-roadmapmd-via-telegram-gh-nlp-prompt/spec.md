# Specification: ตรวจสอบ Kanban และ Roadmap ผ่าน Telegram (/gh + NLP)

เอกสารข้อกำหนดฉบับนี้ระบุถึงพฤติกรรมและผลลัพธ์ที่คาดหวังสำหรับการเพิ่มความสามารถในการเรียกดูสถานะ **GitHub Project (Kanban)** และสรุปไฟล์ **Roadmap (ROADMAP.md)** ผ่านทาง Akasa Bot บน Telegram ทั้งในรูปแบบของ Slash Command และการคุยแบบภาษาธรรมชาติ (NLP)

---

## 🎯 เป้าหมาย (Goal)
เพื่อให้ผู้ใช้งานสามารถติดตามภาพรวมและความคืบหน้าของโปรเจกต์ได้ทันทีผ่าน Telegram โดยไม่ต้องสลับหน้าจอไปที่ GitHub Web Interface ช่วยให้การบริหารจัดการโครงการมีความคล่องตัวสูงขึ้น

---

## 👤 กลุ่มผู้ใช้งาน (User Persona)
- **Developer:** ต้องการเช็คว่ามีงานอะไรอยู่ในคอลัมน์ "Doing" หรือ "Next" บ้าง
- **Project Manager:** ต้องการสรุปภาพรวมของแผนงาน (Roadmap) เพื่อตอบคำถามทีมหรือลูกค้าขณะอยู่นอกสถานที่

---

## 🚶 เส้นทางผู้ใช้งาน (User Journey)
1. **ผ่านคำสั่งตรง (Slash Command):** ผู้ใช้พิมพ์ `/gh kanban` หรือ `/gh roadmap` ใน Telegram
2. **ผ่านการสนทนา (NLP):** ผู้ใช้พิมพ์ข้อความถามทั่วไป เช่น "ตอนนี้งานถึงไหนแล้ว ขอดู kanban หน่อย" หรือ "แผนงานปีนี้มีอะไรบ้าง สรุป roadmap ให้ที"
3. **การประมวลผล:** ระบบจะตรวจสอบว่าเป็นการระบุ Repository โดยตรง หรือต้องอ้างอิงจาก Project Context ปัจจุบันที่ Bind ไว้
4. **การแสดงผล:** ระบบตอบกลับด้วยข้อความ Markdown ที่สรุปเนื้อหาสำคัญ กระชับ และมีลิงก์ไปยัง GitHub เพื่อดูรายละเอียดเพิ่มเติม

---

## ✅ ข้อกำหนดเชิงฟังก์ชัน (Functional Requirements)

### 1. การเรียกใช้ผ่าน Slash Command (`/gh`)
- รองรับ Sub-command ใหม่: `kanban` และ `roadmap`
- รูปแบบการใช้งาน:
    - `/gh kanban [owner/repo]`
    - `/gh roadmap [owner/repo]`
- หากไม่ระบุ `owner/repo` ระบบจะใช้ลำดับการค้นหาดังนี้:
    1. โปรเจกต์ปัจจุบันที่กำลังคุยอยู่ (Current Project Context)
    2. พาธที่ Bind ไว้ในเครื่อง (Bound Project Path)

### 2. การเรียกใช้ผ่านภาษาธรรมชาติ (NLP/LLM Tools)
- เพิ่มความสามารถให้ AI Agent เข้าถึงเครื่องมือ (Tools) ในการดึงข้อมูล Kanban และ Roadmap
- AI ต้องสามารถตีความเจตนาของผู้ใช้ (Intent Recognition) เพื่อเรียกใช้ฟังก์ชันที่ถูกต้อง

### 3. การแสดงผล Kanban (Kanban Summary)
- สรุปคอลัมน์ (Buckets/Statuses) ของ GitHub Project ที่เกี่ยวข้องกับ Repo นั้นๆ
- แสดงจำนวนรายการในแต่ละคอลัมน์ (เช่น Todo: 5, In Progress: 2)
- รายงานรายการงานสำคัญหรือรายการล่าสุดในคอลัมน์หลักๆ
- ให้ลิงก์กลับไปยังหน้า GitHub Project Board

### 4. การแสดงผล Roadmap (Roadmap Summary)
- ค้นหาไฟล์ `docs/ROADMAP.md` (หรือชื่อใกล้เคียงในโฟลเดอร์ docs)
- กรณีที่มีการ Bind Project Path ในเครื่อง ให้เลือกอ่านจากไฟล์ในเครื่องก่อน (Local-first)
- หากไม่มีไฟล์ในเครื่อง ให้พยายามดึงข้อมูลจาก Repository บน GitHub (Remote fallback)
- สรุปเนื้อหาจากไฟล์ให้สั้น กระชับ เหมาะสำหรับการอ่านบนมือถือ

### 5. การจัดการกรณีผิดพลาด (Error Handling)
- หากไม่พบ Project Board หรือไฟล์ Roadmap ต้องแจ้งผู้ใช้ด้วยข้อความที่ชัดเจนและสุภาพ
- หากระบุ Repository ผิดพลาด ต้องมีการแนะนำวิธีระบุที่ถูกต้อง

---

## 🛠 ข้อกำหนดที่ไม่ใช่เชิงฟังก์ชัน (Non-Functional Requirements)
- **Response Time:** การดึงข้อมูลและสรุปควรใช้เวลาไม่เกิน 5-10 วินาที
- **Formatting:** ใช้ MarkdownV2 ของ Telegram อย่างถูกต้อง (รองรับการ Escape อักขระพิเศษ)

---

## 📋 Specification by Example (SBE)

### Scenario 1: การตรวจสอบ Kanban ผ่าน Slash Command
**สถานะ:** ผู้ใช้กำลังพัฒนาโปรเจกต์ Akasa และต้องการดูงานที่ค้างอยู่

| ผู้ใช้พิมพ์ (Input) | บริบท (Context) | ผลลัพธ์ที่คาดหวัง (Expected Output Summary) |
|:---|:---|:---|
| `/gh kanban` | Bind อยู่กับ `oatrice/Akasa` | รายการคอลัมน์: Todo (10), Doing (2), Done (45). งานที่กำลังทำ: #82, #83 [Link] |
| `/gh kanban google/jax` | ไม่มี | สรุปสถานะ Kanban ของ Repo `google/jax` พร้อมลิงก์ไปยัง Project Board |
| `/gh kanban` | ไม่ได้ Bind โปรเจกต์ใดๆ | "กรุณาระบุ repository หรือเลือกโปรเจกต์ก่อน (เช่น /gh kanban owner/repo)" |

### Scenario 2: การขอสรุป Roadmap ผ่าน NLP
**สถานะ:** ผู้ใช้ต้องการทราบทิศทางของโปรเจกต์โดยการพิมพ์ถามทั่วไป

| ผู้ใช้พิมพ์ (Input) | การทำงานภายใน (Action) | ผลลัพธ์ที่คาดหวัง (Expected Response) |
|:---|:---|:---|
| "ขอดู roadmap ของ Akasa หน่อย" | เรียก Tool `get_roadmap_summary` สำหรับ `oatrice/Akasa` | "📍 **Roadmap: Akasa**\n- Phase 1: Core Bot (Done)\n- Phase 2: GitHub Integration (In Progress)\n- Phase 3: GUI Support (Q3 2024)\n[ดูไฟล์เต็มที่นี่]" |
| "โปรเจกต์นี้มีแผนจะทำอะไรต่อบ้าง?" | ระบุ Repo จาก Context แล้วเรียกสรุป Roadmap | "สรุปแผนงานถัดไปของโปรเจกต์นี้จาก ROADMAP.md คือ...\n1. เพิ่มระบบแจ้งเตือน...\n2. ปรับปรุง UI..." |

---

## 🚧 ข้อจำกัดและสิ่งที่ต้องระวัง (Constraints & Considerations)
- **GitHub API Limits:** การดึงข้อมูล GitHub Project อาจต้องใช้ GraphQL API (สำหรับ ProjectV2) ซึ่งต้องตรวจสอบสิทธิ์การเข้าถึงให้ถูกต้อง
- **Message Length:** ไฟล์ `ROADMAP.md` อาจยาวมาก AI ต้องสรุปให้ไม่เกินโควตาข้อความของ Telegram (4096 ตัวอักษร)
- **Privacy:** ตรวจสอบให้แน่ใจว่าการอ่านไฟล์ Local Roadmap ไม่ได้นำข้อมูลที่เป็นความลับออกไปเผยแพร่ในช่องทางสาธารณะ (หากเป็นกลุ่มเปิด)