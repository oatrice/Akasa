"""
🟥 TDD RED Phase: Failing Tests สำหรับ FastAPI Health Check

Test cases ตาม SBE (Specification by Example):
- Scenario 1: GET /health → 200 OK + {"status": "ok"}
- Scenario 2: GET /nonexistent → 404 Not Found
- Scenario 3: POST /health → 405 Method Not Allowed
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check_success():
    """
    GIVEN Backend application ทำงานอยู่
    WHEN ส่ง GET request ไปยัง /health
    THEN ตอบกลับ 200 OK พร้อม {"status": "ok"}
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_route_not_found():
    """
    GIVEN Backend application ทำงานอยู่
    WHEN ส่ง GET request ไปยัง endpoint ที่ไม่มีอยู่
    THEN ตอบกลับ 404 Not Found
    """
    response = client.get("/this-route-does-not-exist")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_method_not_allowed():
    """
    GIVEN Backend application ทำงานอยู่
    WHEN ส่ง POST request ไปยัง /health (ซึ่งรองรับแค่ GET)
    THEN ตอบกลับ 405 Method Not Allowed
    """
    response = client.post("/health")
    assert response.status_code == 405
    assert response.json() == {"detail": "Method Not Allowed"}


def test_health_check_dependency_failure():
    """
    GIVEN Backend application มีการใช้งาน Service ภายใน (Dependency)
    WHEN Service ภายในเกิดทำงานล้มเหลว (Raise Exception) ตอนเรียก /health
    THEN ตอบกลับ 503 Service Unavailable แทนที่จะเป็น 200 OK
    """
    # จำลอง (Mock) ว่า dependency `check_database` ล้มเหลว
    from app.routers.health import check_database
    
    def override_check_database():
        # จำลองว่าระบบฐานข้อมูลทำงานผิดปกติและส่งค่า False กลับไป
        return False
        
    app.dependency_overrides[check_database] = override_check_database
    
    try:
        response = client.get("/health")
        assert response.status_code == 503
        assert response.json() == {"detail": "Service Unavailable"}
    finally:
        # ล้าง override ออก เพื่อไม่ให้ส่งผลกับ test ถัดไป (สำคัญมาก เพราะถ้าแอพ exception ขัดมันจะข้ามบรรทัดนี้ในโค้ดเดิม)
        app.dependency_overrides.clear()


def test_health_check_trailing_slash():
    """
    GIVEN Backend application มี Endpoint /health
    WHEN ส่ง request ไปยัง /health/ (มี trailing slash)
    THEN ตอบกลับ 404 Not Found (Strict routing)
    """
    response = client.get("/health/")
    assert response.status_code == 404


def test_openapi_schema_validation():
    """
    GIVEN Backend application ทำงานอยู่
    WHEN ดึงข้อมูล OpenAPI schema จาก /openapi.json
    THEN Endpoint /health ต้องมี tag "Monitoring"
    """
    response = client.get("/openapi.json")
    assert response.status_code == 200
    
    schema = response.json()
    paths = schema.get("paths", {})
    health_path = paths.get("/health", {})
    health_get = health_path.get("get", {})
    tags = health_get.get("tags", [])
    
    assert "Monitoring" in tags

