# การวิเคราะห์ทางเทคนิค (Auto-generated)

| Feature Information | |
| --- | --- |
| **Feature Name** | [Phase 1] สมัคร OpenRouter + ทดสอบ API |
| **Date** | 2026-03-07 |
| **Author** | Gemini-CLI |
| **Issue URL** | [#1](https://github.com/oatrice/Akasa/issues/1) |

---

## 📄 สรุป (Summary)

งานนี้เป็นขั้นตอนแรกในการวางรากฐานของโปรเจกต์ Akasa โดยมีเป้าหมายเพื่อ **สมัครใช้งาน OpenRouter, ขอรับ API Key, และสร้างสคริปต์เพื่อทดสอบการเรียกใช้งาน LLM (Large Language Model) ผ่าน API** เพื่อยืนยันว่าสามารถเชื่อมต่อและรับ-ส่งข้อมูลกับโมเดลฟรีที่มีให้บริการได้สำเร็จ

---

## 🛠️ แนวทางการพัฒนา (Proposed Solution)

1.  **สมัครและรับ API Key:**
    *   ดำเนินการสมัครบัญชีผู้ใช้บนเว็บไซต์ `openrouter.ai` ด้วยตนเอง
    *   สร้าง API Key และจัดเก็บในที่ปลอดภัย

2.  **การจัดเก็บ Key อย่างปลอดภัย:**
    *   **ห้าม Hardcode** API Key ลงในซอร์สโค้ดเด็ดขาด
    *   **ข้อเสนอ:** ให้จัดเก็บ Key เป็น Environment Variable ในไฟล์ `.env` โดยตั้งชื่อว่า `OPENROUTER_API_KEY` และเพิ่ม `.env` เข้าไปในไฟล์ `.gitignore` เพื่อป้องกันการ commit Key ขึ้น Git Repository

3.  **สร้างสคริปต์ทดสอบ:**
    *   สร้างไฟล์ Python ใหม่ที่ path: `scripts/test_openrouter.py`
    *   ใช้ library `requests` และ `os` ใน Python เพื่ออ่าน API Key จาก Environment Variable และยิง HTTP Request
    *   สคริปต์จะส่ง `POST` request ไปยัง Endpoint ของ OpenRouter: `https://openrouter.ai/api/v1/chat/completions`
    *   **Request Headers** ที่ต้องใส่:
        *   `Authorization: Bearer $OPENROUTER_API_KEY`
        *   `Content-Type: application/json`
    *   **Request Body** จะระบุโมเดลฟรี (เช่น `mistralai/mistral-7b-instruct:free`) พร้อมกับ prompt ง่ายๆ เช่น `"Hello, world!"`
    *   สคริปต์จะพิมพ์ผลลัพธ์ (JSON response) ที่ได้รับจาก API ออกทาง console เพื่อเป็นการยืนยันความสำเร็จ

---

## 💥 การวิเคราะห์ผลกระทบ (Impact Analysis)

| Component | Description |
| --- | --- |
| **New Files** | <ul><li>`scripts/test_openrouter.py`</li><li>`.env.example` (ไฟล์ตัวอย่างสำหรับบอกว่าต้องใช้ key อะไรบ้าง)</li></ul> |
| **Backend** | <ul><li>**ไม่มีผลกระทบโดยตรง** กับแอปพลิเคชันหลักในเฟสนี้</li><li>สคริปต์นี้เป็น Proof-of-concept ซึ่งโลจิกจะถูกนำไปพัฒนาต่อเป็นโมดูล `llm_client` ใน Backend service (FastAPI) ในอนาคต</li></ul> |
| **Frontend (Web/Mobile)** | <ul><li>ไม่มีผลกระทบ</li></ul> |
| **Database** | <ul><li>ไม่มีผลกระทบ</li></ul> |
| **Infrastructure / DevOps** | <ul><li>จะต้องมีการจัดการ Secret (`OPENROUTER_API_KEY`) ในระบบ CI/CD และบน Production Server ในอนาคต</li></ul> |

---

## ✅ แผนการทดสอบ (Testing Plan)

*   **Integration Test:** การรันสคริปต์ `scripts/test_openrouter.py` ถือเป็นการทดสอบแบบ Integration Test ในตัวมันเอง
    *   **เกณฑ์การทดสอบผ่าน (Success Criteria):**
        1.  สคริปต์ทำงานสำเร็จโดยไม่มี Error
        2.  Console แสดงผลลัพธ์เป็น JSON response ที่ถูกต้องจาก LLM ซึ่งมีข้อความที่ถูก generate ขึ้นมา
    *   **เกณฑ์การทดสอบไม่ผ่าน (Failure Criteria):**
        1.  สคริปต์เกิดข้อผิดพลาด เช่น Network Error, `401 Unauthorized` (Keyผิด), หรือ `400 Bad Request` (Bodyผิด)
        2.  ไม่ได้รับ JSON response กลับมา หรือ response ที่ได้ไม่มีโครงสร้างตามที่คาดหวัง

---

## 📝 ข้อสันนิษฐานและความเสี่ยง (Assumptions & Risks)

*   **ข้อสันนิษฐาน:**
    *   มีโมเดลฟรี (Free-tier model) ที่เหมาะสมบน OpenRouter ให้สามารถใช้ทดสอบได้โดยไม่มีค่าใช้จ่าย
    *   Project Owner หรือผู้ที่ได้รับมอบหมาย จะเป็นผู้รับผิดชอบในการสมัครและนำ API Key มาใส่ใน Environment ของโปรเจกต์

*   **ความเสี่ยง:**
    *   **API Key รั่วไหล (Secret Leakage):** เป็นความเสี่ยงสูงสุดหากจัดการไม่ดี การใช้ Environment Variable และ `.gitignore` เป็นมาตรการที่จำเป็นอย่างยิ่ง
    *   **ข้อจำกัดของ API:** API ของ OpenRouter อาจมี Rate Limit หรือนโยบายการใช้งานสำหรับโมเดลฟรี ซึ่งอาจส่งผลกระทบต่อการทดสอบหากมีการเรียกใช้งานถี่เกินไป