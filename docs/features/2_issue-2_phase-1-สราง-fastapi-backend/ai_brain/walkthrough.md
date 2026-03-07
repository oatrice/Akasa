# Walkthrough: Phase 1 FastAPI Backend Foundation

> Issue: [#2](https://github.com/oatrice/Akasa/issues/2)
> Status: Completed ✅

เป้าหมายของ Phase นี้คือการสร้างโครงสร้างพื้นฐานสำหรับ FastAPI Backend พร้อม endpoint เริ่มต้น (`/health`) เพื่อการทำงานในอนาคต โดยทุกขั้นตอนเขียนขึ้นภายใต้รูปแบบ **Test-Driven Development (TDD)** อย่างเคร่งครัดตามข้อกำหนดของผู้ใช้

## 1. การสร้างสภาพแวดล้อมและโครงสร้าง

- **Virtual Environment (venv):** ถูกสร้างขึ้นใหม่เพื่อจัดการ dependencies แยกออกจาก System Python
- **Dependencies:** ติดตั้ง core packages ตาม plan รวมถึง `fastapi`, `uvicorn[standard]` (server), และ `httpx` (สำหรับ test client)
- **Directory Structure:** วางโครงสร้างแอปพลิเคชันแบบพร้อม scale โดยแยกหมวดหมู่ชัดเจน:

```
app/
├── __init__.py
├── main.py              ← Entry point ของแอปพลิเคชัน
├── routers/
│   ├── __init__.py
│   └── health.py        ← Router สำหรับ health check
├── services/
│   └── __init__.py      ← โฟลเดอร์เตรียมพร้อมสำหรับ Business logic
└── models/
    └── __init__.py      ← โฟลเดอร์เตรียมพร้อมสำหรับ Data models
```

## 2. กระบวนการ TDD (Red -> Green -> Refactor)

ทำงานตามหลักการ TDD อย่างเคร่งครัด

### 🟥 RED (Failing Tests)
เริ่มจากการสร้างไฟล์ `tests/test_main.py` โดยเขียน Test scenarios ตามที่ออกแบบไว้ใน SBE (Specification by Example) ซึ่งในขณะนั้นแอปพลิเคชันยังไม่มีอยู่จริง เมื่อรัน pytest จะเกิด `ModuleNotFoundError: No module named 'app.main'` ถือว่าผ่านกฎ RED

- `test_health_check_success` (ตรวจสอบสถานะ `200 OK`)
- `test_route_not_found` (ตรวจสอบเส้นทางที่ไม่มีอยู่ `404 Not Found`)
- `test_method_not_allowed` (ตรวจสอบการเรียกใช้เมธอดผิดประเภทลงบน health check `405 Method Not Allowed`)

### 🟢 GREEN (Passing Implementation)
สร้าง [app/main.py](file:///Users/oatrice/Software-projects/Akasa/app/main.py) ขึ้นมาแบบ Minimal เพื่อให้ตอบสนอง 3 สถานการณ์ด้านบน โดยสร้าง API Endpoint ชนิด GET ไปที่ `/health` การรัน pytest ในตอนท้ายผ่านลุล่วง (100% Passed)

### ✨ REFACTOR (Architecture Scaling)
เพื่อรองรับสถาปัตยกรรมแบบ scalable ตามที่ผู้ใช้ระบุ โค้ดสำหรับ monitoring ตัวนี้ถูกแยกย้าย (Refactor) ให้มาอยู่ในรูปของ FastAPI Router
- จัดแยกเป็นไฟล์ [app/routers/health.py](file:///Users/oatrice/Software-projects/Akasa/app/routers/health.py)
- ปรับปรุง [app/main.py](file:///Users/oatrice/Software-projects/Akasa/app/main.py) เพื่อดึง `router` เหล่านี้เข้ามารวมกันผ่านคำสั่ง `app.include_router()`
- รัน `pytest` กลับไปอีกครั้ง พบว่าโค้ดยังคงเสถียรและผ่าน 100% ครบทุกข้อ

---

## 3. Results and Validation

### Automated Validation (Unit Tests)

จากการรันคำสั่ง  `pytest tests/ -v` ชุดทดสอบทั้งหมด 8 รายการทำงานผ่านครบถ้วน

```log
============================= test session starts ==============================
tests/test_main.py::test_health_check_success PASSED                     [ 12%]
tests/test_main.py::test_route_not_found PASSED                          [ 25%]
tests/test_main.py::test_method_not_allowed PASSED                       [ 37%]
tests/test_openrouter.py::test_call_openrouter_api_success PASSED        [ 50%]
tests/test_openrouter.py::test_call_openrouter_api_unauthorized PASSED   [ 62%]
tests/test_openrouter.py::test_call_openrouter_api_missing_key PASSED    [ 75%]
tests/test_openrouter.py::test_call_openrouter_api_server_error PASSED   [ 87%]
tests/test_openrouter.py::test_call_openrouter_api_malformed_response PASSED [100%]
========================= 8 passed, 1 warning in 2.10s =========================
```

### Manual Validation

1. สั่งเปิด Uvicorn server ที่ `http://127.0.0.1:8000`
2. ทดสอบยิง Request ผ่าน Terminal (`curl`) ไปที่เซิร์ฟเวอร์ด้วยตนเอง:
    - **Happy Path:** `/health` ได้ผลตอบกลับ `{"status":"ok"}`
    - **404:** `/nonexistent` ได้ HTTP responses code `404`
    - **405:** ส่ง `POST` ไปที่ `/health` ได้ responses code `405`

### 4. Code Highlight

โครงสร้างที่มีการ Refactor ให้ใช้ Router เพื่อเป็นแบบอย่างในการพัฒนา Endpoint ถัดไปในอนาคต:

**[app/routers/health.py](file:///Users/oatrice/Software-projects/Akasa/app/routers/health.py)**
```python
from fastapi import APIRouter

router = APIRouter(tags=["Monitoring"])

@router.get("/health")
def health_check() -> dict:
    """
    Endpoint สำหรับตรวจสอบสถานะของระบบ (Health Check)
    """
    return {"status": "ok"}
```

### Code Review Feedback Edition (2026-03-07)
เพิ่มเติมเพื่อปรับปรุงระบบตาม Code Review Feedback 3 จุดที่ได้รับมอบหมาย:

1. **Dependency Failure (`503 Service Unavailable`)**: สร้างจำลองการจัดการ Dependency (`db_ok`) เพื่อรองรับการล่มของฐานข้อมูล และสามารถดักจับ Exception ปล่อยเป็นโค้ด `503` ได้ผ่าน `tests/test_main.py`
2. **Strict Routing (`GET /health/` → `404`)**: ทำการปรับปิด `app.router.redirect_slashes = False` ใน `app/main.py` ไม่ให้มีการรีไดเร็ค 307 เพื่อความเด็ดขาดของเส้นทาง API
3. **OpenAPI Schema Validated**: ยืนยันได้ว่าส่วนแสดงผลมี Tag เป็น `"Monitoring"` ตามที่ต้องการ

ทำให้ยอด Test Cases ทั้งหมดมีจำนวน `6` ตัวจาก Route เริ่มต้นตัวเดียว.
```log
============================= test session starts ==============================
tests/test_main.py::test_health_check_success PASSED                     [ 16%]
tests/test_main.py::test_route_not_found PASSED                          [ 33%]
tests/test_main.py::test_method_not_allowed PASSED                       [ 50%]
tests/test_main.py::test_health_check_dependency_failure PASSED          [ 66%]
tests/test_main.py::test_health_check_trailing_slash PASSED              [ 83%]
tests/test_main.py::test_openapi_schema_validation PASSED                [100%]
============================== 6 passed in 0.18s ===============================
```
