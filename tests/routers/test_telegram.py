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


# === Code Review #3 — Test Suggestions ===


def test_webhook_fail_malformed_payload():
    """ส่ง JSON ที่โครงสร้างไม่ตรงกับ Update model → ต้องได้ 422"""
    with patch("app.routers.telegram.settings") as mock_settings:
        mock_settings.WEBHOOK_SECRET_TOKEN = TEST_SECRET_TOKEN
        response = client.post(
            WEBHOOK_URL,
            headers={"X-Telegram-Bot-Api-Secret-Token": TEST_SECRET_TOKEN},
            json={"invalid_field": "not an update"},
        )
    assert response.status_code == 422


def test_webhook_fail_empty_secret_token_bypass():
    """ป้องกัน auth bypass: ถ้า WEBHOOK_SECRET_TOKEN เป็น '' และ header ก็เป็น '' → ต้องได้ 403"""
    with patch("app.routers.telegram.settings") as mock_settings:
        mock_settings.WEBHOOK_SECRET_TOKEN = ""  # ค่าว่าง — ไม่ได้ตั้งค่า
        response = client.post(
            WEBHOOK_URL,
            headers={"X-Telegram-Bot-Api-Secret-Token": ""},
            json=VALID_PAYLOAD,
        )
    assert response.status_code == 403
    assert response.json() == {"detail": "Invalid secret token"}


def test_webhook_success_edited_message():
    """ส่ง payload เป็น edited_message แทน message → ต้อง parse ได้ 200 OK"""
    edited_message_payload = {
        "update_id": 99,
        "edited_message": {
            "message_id": 5,
            "chat": {"id": 1, "type": "private"},
            "date": 1678886400,
            "text": "edited text",
        },
    }
    with patch("app.routers.telegram.settings") as mock_settings:
        mock_settings.WEBHOOK_SECRET_TOKEN = TEST_SECRET_TOKEN
        response = client.post(
            WEBHOOK_URL,
            headers={"X-Telegram-Bot-Api-Secret-Token": TEST_SECRET_TOKEN},
            json=edited_message_payload,
        )
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_webhook_success_calls_chat_service():
    """ส่ง request ที่ถูกต้อง → ต้องเรียกใช้ chat_service.handle_chat_message ผ่าน BackgroundTasks"""
    with patch("app.routers.telegram.settings") as mock_settings:
        mock_settings.WEBHOOK_SECRET_TOKEN = TEST_SECRET_TOKEN
        with patch("app.routers.telegram.handle_chat_message") as mock_handle:
            response = client.post(
                WEBHOOK_URL,
                headers={"X-Telegram-Bot-Api-Secret-Token": TEST_SECRET_TOKEN},
                json=VALID_PAYLOAD,
            )
    assert response.status_code == 200
    mock_handle.assert_called_once()
