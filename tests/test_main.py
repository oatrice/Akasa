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
