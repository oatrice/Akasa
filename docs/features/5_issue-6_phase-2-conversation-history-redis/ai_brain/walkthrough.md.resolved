# Walkthrough: Issue #6 — Conversation History with Redis & Error Handling

## สรุปสิ่งที่ทำ

ยกระดับ Akasa Chatbot จาก **stateless** → **stateful** ด้วย Redis เก็บประวัติสนทนาแยก `chat_id` พร้อมเพิ่มความทนทานต่อ **Edge Cases** และ **Error Handling** เชิงลึกตามที่ระบุใน Test Suggestions (Issue #4 และ #6)

### ความสามารถที่เพิ่มขึ้น:
1. **Chat History (Redis):** จำบริบทการสนทนาได้ 10 ข้อความล่าสุดต่อ user, จำเป็นเวลา 24 ชั่วโมง
2. **Graceful Degradation:** ถ้า Redis ล่ม หรือไม่มี Service ให้ต่อ บอทก็จะยังทำงานได้แค่เป็น Stateless ธรรมดา 
3. **API Error Handling (Issue #4 Fixes):**
   - ดักจับ Timeout จาก LLM API
   - ดักจับข้อมูลที่ไม่ใช่ตามฟอร์มจาก LLM (เช่น Parse JSON ผิด หรือส่งของเปล่ากลับมา)
   - หากเจอ Error เหล่านี้ บอทจะ**ไม่แครช** แต่จะส่งข้อความแจ้งเตือนกลับหา User ว่า *"ขออภัย ระบบขัดข้องชั่วคราวในการตอบสนอง 🙇‍♂️"* แทน
4. **Redis Edge Cases (Issue #6 Fixes):**
   - ดักจับ JSON JSONDecodeError เวลาเจอข้อมูลพังใน Redis (จะโดน skip เสมือนไม่มีข้อมูล)
   - ป้องกันบั๊กกรณีระบุค่า `REDIS_HISTORY_LIMIT = 0` (ถ้าระบุศูนย์คือจะไม่บันทึกใดๆ และ Get กลับมาได้ค่าว่างเสมอ ไม่ดึงข้อมูลโง่ๆ กลับมาทั้งหมด)

## ไฟล์ที่เปลี่ยนแปลงหลักๆ

| ไฟล์ | หน้าที่ / การอัปเดต |
|---|---|
| [redis_service.py](file:///Users/oatrice/Software-projects/Akasa/app/services/redis_service.py) | **(สร้างขึั้นมาใหม่)** ใช้เก็บประวัติด้วยคำสั่ง Redis `LPUSH/LTRIM/EXPIRE`. เพิ่มการ Catch Exception เผื่อข้อมูลใน Redis พังและตรวจสอบ `limit <= 0` |
| [chat_service.py](file:///Users/oatrice/Software-projects/Akasa/app/services/chat_service.py) | **(อัปเดต)** เพิ่มส่วนเชื่อมต่อ Redis และเพิ่มส่วนการ Try-Catch ดัก Exception เวลายิง Telegram และ LLM ล้มเหลว พร้อมส่งข้อความสำรอง (Fallback message) |
| [llm_service.py](file:///Users/oatrice/Software-projects/Akasa/app/services/llm_service.py) | **(อัปเดต)** เปลี่ยนเป็นรับข้อมูลแบบ `messages: list[dict]` แทน string อันเดียว ทำให้รองรับ Chat Context |
| [test_chat_service.py](file:///Users/oatrice/Software-projects/Akasa/tests/services/test_chat_service.py) | **(ทดสอบเพิ่ม)** จำลองตอน LLM Timeout, ตอนค่าตอบกลับพัง, รอเช็คว่ามีแจ้งเตือนผู้ใช้ |
| [test_redis_service.py](file:///Users/oatrice/Software-projects/Akasa/tests/services/test_redis_service.py) | **(ทดสอบเพิ่ม)** จำลองข้อมูลพัง (Bad JSON) ลงใน Redis แล้วเช็คว่าระบบข้ามไปถูกตัว, และทดสอบ Limit 0 |
| [test_redis_integration.py](file:///Users/oatrice/Software-projects/Akasa/tests/integration/test_redis_integration.py) | **(ทดสอบเพิ่ม)** เขียนทดสอบการลบ Key เองของ Redis ด้วยการใช้ `asyncio.sleep` คู่กับ `REDIS_TTL_SECONDS = 1` |

## Test Results
ผลรวม Test ผ่านหมด ไม่มี Warning หรือ Error กวนใจแม้แต่ตัวเดียว (ลบไฟล์ `error.log` ที่เกิดจาก HTTP Status Error เวลาทำเทสต์ทิ้งเรียบร้อย)
```
============================= test session starts ==============================
collected 46 items

tests/integration/test_redis_integration.py ..............   [ 10%]
...
tests/services/test_chat_service.py ......................   [ 35%]
...
tests/services/test_redis_service.py .....................   [ 52%]

======================== 46 passed, 1 warning in 4.98s =========================
```
