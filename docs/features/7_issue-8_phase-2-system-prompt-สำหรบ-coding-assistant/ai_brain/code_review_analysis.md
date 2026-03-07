# 📊 Code Review Analysis (Cross-Repository)

จากการสำรวจไฟล์ `code_review.md` ในทั้ง 3 โปรเจกต์ (Akasa, JarWise, The Middle Way) นี่คือสรุปประเด็นที่ต้องแก้ไขและคำแนะนำในการเขียนเทสต์ (Test Suggestions) ครับ

---

## 1️⃣ โปรเจกต์: Akasa (Python / FastAPI / Telegram Bot)
**ประเด็นที่ลูม่าคอมเมนต์มา:**
- **Silent Failure (High Priority)**: ใน `chat_service.py` เมื่อเกิด Exception ทั่วไป (เช่น API พังแบบไม่คาดคิด) บอทจะเงียบไปเลย ควรเพิ่มให้ส่งกลับไปบอกผู้ใช้ว่า "ขออภัย เกิดข้อผิดพลาดที่ไม่คาดคิด"
- **Inconsistent Config**: `llm_service.py` มีการฮาร์ดโค้ด URL ของ OpenRouter และใช้ `OPENROUTER_API_KEY` โดยตรง แทนที่จะใช้ `LLM_BASE_URL` และ `LLM_API_KEY` ชี้เป้าตามที่ออกแบบมา
- **PEP8 Style**: เคลื่อนย้ายการ import (`import logging`, `from app.config import settings`) ที่ซ่อนอยู่ในฟังก์ชั่นขึ้นมาไว้บนสุดของไฟล์

**Test Suggestions ที่ให้ทำตาม:**
เป็นคำแนะนำเกี่ยวกับ **Manual Verification** การเทสต์การทำงานของ System Prompt ว่าทำงานถูกต้องหรือไม่ และเช็คข้อมูลใน Redis History `LRANGE` เพื่อยืนยันว่าไม่มี System Prompt หลุดลงไปใน History. (ส่วนนี้คุณเพิ่งเทสต์ไปแล้ว)

---

## 2️⃣ โปรเจกต์: JarWise (Requirements / Specs)
**ประเด็นที่ลูม่าคอมเมนต์มา:**
- **Logic Error / Conflicting Specs (High Priority)**: เอกสาร Requirement ของ Feature #59 (Financial Reports) ดันมีบอกขอบเขตหลุดไปถึงเรื่อง Data Export ทั้งที่ Data Export ถูกแยกไปเป็น Issue #89, #90, #91 แล้ว
- **แก้ไขด่วน**: ต้องไปปรับแก้ `analysis.md` ของ #59 ให้ตัดส่วน Export Data ออกจากการออกแบบหน้าจอ / Flowchart ทิ้งทั้งหมด 
- **แก้ไข Prompt**: อัปเดตไฟล์ `prompt_*.txt` ให้ชี้เป้าไปที่เอกสารใหม่ที่ถูกต้อง

**Test Suggestions ที่ให้ทำตาม:**
- **Data Integrity**: เขียนเทสต์กรณีลบ Wallet แม่ทิ้ง (ที่มี Jars ลูกอยู่และมี Transaction) ต้องมีระบบป้องกัน หรือจับย้าย Jars ไปไว้ Wallet อื่นอัตโนมัติ ไม่ให้เงินหาย
- **Legacy Migration**: ม็อกไฟล์ Data เก่าที่พังหรือข้อมูลไม่ครบถ้วน โยนให้ตัวทำ Migration (#65) เช็คว่าแอพต้องไม่แครช และจัดเก็บ/ข้าม ข้อมูลที่พังอย่างปลอดภัย
- **Cross-Device Sync Conflict**: สร้างสถานการณ์โอนเงิน (#71) ในเครื่อง A แล้วรีบไปลบกระเป๋าเงินในเครื่อง B ก่อนที่ Sync จะทำงานเสร็จ เพื่อดูว่าระบบคลาวน์จะจัดการ Conflict นี้อย่างไร

---

## 3️⃣ โปรเจกต์: The Middle Way (Go Backend)
**ประเด็นที่ลูม่าคอมเมนต์มา:**
- **Mock Race Condition**: ขาดการใส่ `sync.Mutex` ในการจำลองข้อมูล (`mock repo`) บนเทสต์ `admin_category_handler_test.go` ซึ่งเสี่ยงให้เกิดพาณิชย์ข้อมูลแข่งกัน (Data Races) ในตอนรันเทสต์แบบ `t.Parallel()`
- **Inefficient Query**: `DeleteCategory` ไม่ยอมหา by ID ทำดึง Category ทั้งหมดมาก่อนแล้ววนลูปหา ซึ่งทำงานช้า แก้ด้วยการใช้ `repo.FindByID(id)`
- **Query Fallback ซ่อนบั๊ก**: โค้ด `FindAll` มี Fallback ตอน Join Query พัง ซึ่งจะปกปิด Error โดยการเซ็ตให้ UsageCount เป็น 0 เสมอ เสี่ยงทำให้เกิดบั๊กลบ Category ผิดตัว
- **โค้ดเก่าค้าง**: มี Admin Logic ซ้ำซ้อนของเก่า (`AdminHandler`) ให้ลบทิ้งเพราะไปใช้ไฟล์ใหม่กันหมดแล้ว

**Test Suggestions ที่ให้ทำตาม:**
- **Test DeleteCategory (Success Case)**: เขียนเทสต์ให้ครอบคลุมกรณีที่ Category `UsageCount == 0` สามารถสร้าง Request โยนไป `DELETE` แล้วลบสำเร็จ ได้ HTTP `200 OK`
- **Test Reorder Atomicity**: ทดสอบส่ง IDs เรียงมาไม่ครบ หรือ ส่ง ID ขยะมา ระบบจะต้องตอบ `400 Bad Request` หรือ `500` กลับไป และ Order_index เก่าต้องไม่ถูกแก้ไข
- **Test FindAll Query Error**: ทอดสอบการดึงข้อมูลตอนที่ Join Table โดนทำให้พัง (ข้าม Fallback check) ว่า `UsageCount` ถูกจัดการอย่างไร
