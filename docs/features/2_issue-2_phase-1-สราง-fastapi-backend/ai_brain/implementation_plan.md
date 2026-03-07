# Phase 1: FastAPI Backend Foundation

สร้างโครงสร้าง FastAPI Backend พร้อม `/health` endpoint ตาม Issue #2 โดยใช้ TDD strict mode และเตรียมโครงสร้าง directory ที่รองรับ scaling ในอนาคต

## User Review Required

> [!IMPORTANT]
> **Virtual Environment (venv):** แนะนำให้ใช้ venv เพื่อแยก dependencies ออกจาก system Python จะได้ไม่มีปัญหา version ชนกัน ผมจะสร้าง venv ให้ก่อนเริ่ม (ถ้ายังไม่มี)

## Proposed Changes

### Project Structure

#### [NEW] `app/` directory tree

```
app/
├── __init__.py
├── main.py              ← FastAPI app entry point
├── routers/
│   ├── __init__.py
│   └── health.py        ← /health endpoint (after refactor)
├── services/
│   └── __init__.py      ← เตรียมไว้สำหรับ business logic
└── models/
    └── __init__.py      ← เตรียมไว้สำหรับ data models
```

---

### Dependencies

#### [MODIFY] [requirements.txt](file:///Users/oatrice/Software-projects/Akasa/requirements.txt)

เพิ่ม 3 packages:

```diff
 requests
 python-dotenv
 pytest
 responses
+fastapi
+uvicorn[standard]
+httpx
```

---

### TDD Phase 1 — 🟥 RED (Failing Tests)

#### [NEW] [test_main.py](file:///Users/oatrice/Software-projects/Akasa/tests/test_main.py)

สร้าง test file ก่อนที่จะมี production code → pytest ต้อง FAIL

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check_success():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_route_not_found():
    response = client.get("/this-route-does-not-exist")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}

def test_method_not_allowed():
    response = client.post("/health")
    assert response.status_code == 405
    assert response.json() == {"detail": "Method Not Allowed"}
```

---

### TDD Phase 2 — 🟢 GREEN (Minimal Code)

#### [NEW] [main.py](file:///Users/oatrice/Software-projects/Akasa/app/main.py)

เขียนโค้ดน้อยที่สุดเท่าที่จะทำให้ test ผ่าน:

```python
from fastapi import FastAPI

app = FastAPI(title="Akasa API", version="0.1.0")

@app.get("/health", tags=["Monitoring"])
def health_check() -> dict:
    return {"status": "ok"}
```

---

### TDD Phase 3 — ✨ REFACTOR

#### [NEW] [health.py](file:///Users/oatrice/Software-projects/Akasa/app/routers/health.py)

ย้าย health endpoint เข้า router เพื่อรองรับ scaling:

```python
from fastapi import APIRouter

router = APIRouter(tags=["Monitoring"])

@router.get("/health")
def health_check() -> dict:
    return {"status": "ok"}
```

#### [MODIFY] [main.py](file:///Users/oatrice/Software-projects/Akasa/app/main.py)

Refactor ให้ใช้ router:

```python
from fastapi import FastAPI
from app.routers import health

app = FastAPI(title="Akasa API", version="0.1.0")
app.include_router(health.router)
```

---

## Verification Plan

### Automated Tests

```bash
# รันจาก project root
pytest tests/test_main.py -v
```

คาดหวัง: 3 tests ผ่านทั้งหมด:
- `test_health_check_success` — `GET /health` → 200 + `{"status": "ok"}`
- `test_route_not_found` — `GET /nonexistent` → 404
- `test_method_not_allowed` — `POST /health` → 405

### Manual Verification

1. **Start server:** `uvicorn app.main:app --port 8000`
2. **Health check:** `curl http://127.0.0.1:8000/health` → `{"status":"ok"}`
3. **404 check:** `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/nonexistent` → `404`
4. **Swagger UI:** เปิด `http://127.0.0.1:8000/docs` ใน browser → ต้องเห็น API docs

---

## Code Review Feedback Implementation

เพื่อการปรับปรุงตาม Code Review (Issue #2) จะมีการเพิ่มการเขียนข้อตลกลงในไฟล์ `tests/test_main.py` เพิ่มเติม และการทำงานตามกลไก TDD:

1. **Dependency Failure Test:**
   - **RED:** ขียน Test จำลอง dependency inject ใน Endpoint `GET /health` ตัวหนึ่งที่ raise Exception เสมอ
   - **GREEN:** สร้างฟังก์ชัน dependencies หลอกที่คืนค่าปรกติใน `app/routers/health.py` และทำ Endpoint ให้ return 503 HTTP Exception เมื่อระบบล่ม
   - **REFACTOR:** ย้าย dependency เป็น Function ปกติที่สามารถ override ได้ช่วงรันเทส

2. **URL with Trailing Slash:**
   - **RED:** เขียน Test ยิง `GET /health/` ต้องคืนค่า 404 (การันตีได้ด้วย FastAPI default router behavior)
   - **GREEN:** รันให้ผ่าน

3. **API Schema Validation:**
   - **RED:** เขียน Test รันแอพพลิเคชันดึงข้อมูลไปที่ช่องทาง `/openapi.json` เพื่อหา endpoint `/health` ว่ามี tag ติดมาว่า `Monitoring` จริงหรือไม่
   - **GREEN:** รันให้ผ่าน
