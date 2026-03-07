# Issue #25: Local Bot Build Info in Responses

## Feature/Fix Implementation Tracking

### Setup & Baseline
- [x] Create implementation plan
- [x] Wait for user approval on implementation plan

### Akasa Code Review Refactoring & Tests
- [x] Create automated test for LLM error handling fallback (Red -> Green -> Refactor)
- [x] Create automated test ensuring system prompt is omitted from Redis history (Red -> Green -> Refactor)
- [x] Implement `chat_service.py` fixes (silent failure & PEP8 top-level imports)
- [x] Implement `llm_service.py` fixes (API key config, hardcoded URL & PEP8 top-level imports)
- [x] Verify all tests pass and test coverage is complete

## TDD Implementation

- [x] 🟥 RED: เขียน failing tests ควบคุมการแนบ Build Info (Version, Build Time, Git Hash) ต่อท้ายข้อความที่ตอบกลับ กรณีรันแบบ Local Dev
- [x] 🟢 GREEN: เพิ่ม `ENVIRONMENT`, หา Version จากโฟลเดอร์รัน, หา Startup Time, และ Git Hash นำไปต่อกับข้อความใน `chat_service.py` เมื่อ `ENVIRONMENT` เป็น "development"
- [x] ✨ REFACTOR: จัดระเบียบโค้ดสำหรับอ่านค่าต่างๆ เช่น สร้างฟังก์ชัน `get_build_info()`
- [x] ✅ Verify: ทดลองรันจริง ว่าบอทตอบกลับแบบมี Footer Information ครบถ้วน
