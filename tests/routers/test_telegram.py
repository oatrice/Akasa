"""
Tests สำหรับ Telegram Webhook Router

ครอบคลุม:
- Happy path: token ถูกต้อง → 200
- Invalid token → 403
- Missing token → 403
- Unsupported HTTP method → 405
"""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
WEBHOOK_URL = "/api/v1/telegram/webhook"
TEST_SECRET_TOKEN = "a_very_secret_string_123"

VALID_PAYLOAD = {
    "update_id": 1,
    "message": {
        "message_id": 1,
        "chat": {"id": 1, "type": "private"},
        "date": 1678886400,
        "text": "hello",
    },
}


def test_webhook_success_valid_token():
    """ส่ง request พร้อม Secret Token ที่ถูกต้อง → ต้องได้ 200 OK"""
    with patch("app.routers.telegram.settings") as mock_settings:
        mock_settings.WEBHOOK_SECRET_TOKEN = TEST_SECRET_TOKEN
        response = client.post(
            WEBHOOK_URL,
            headers={"X-Telegram-Bot-Api-Secret-Token": TEST_SECRET_TOKEN},
            json=VALID_PAYLOAD,
        )
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_webhook_fail_invalid_token():
    """ส่ง request พร้อม Secret Token ที่ผิด → ต้องได้ 403"""
    with patch("app.routers.telegram.settings") as mock_settings:
        mock_settings.WEBHOOK_SECRET_TOKEN = TEST_SECRET_TOKEN
        response = client.post(
            WEBHOOK_URL,
            headers={"X-Telegram-Bot-Api-Secret-Token": "this_is_a_wrong_token"},
            json=VALID_PAYLOAD,
        )
    assert response.status_code == 403
    assert response.json() == {"detail": "Invalid secret token"}


def test_webhook_fail_missing_token():
    """ส่ง request โดยไม่มี Secret Token Header → ต้องได้ 403"""
    response = client.post(WEBHOOK_URL, json=VALID_PAYLOAD)
    assert response.status_code == 403
    assert response.json() == {"detail": "Secret token missing"}


def test_webhook_fail_unsupported_method():
    """ใช้ GET method แทน POST → ต้องได้ 405"""
    response = client.get(WEBHOOK_URL)
    assert response.status_code == 405
