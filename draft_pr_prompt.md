# PR Draft Prompt

You are an AI assistant helping to create a Pull Request description.
    
TASK: [Phase 1] สร้าง Telegram Bot + webhook
ISSUE: {
  "title": "[Phase 1] \u0e2a\u0e23\u0e49\u0e32\u0e07 Telegram Bot + webhook",
  "number": 3,
  "body": "\u0e2a\u0e23\u0e49\u0e32\u0e07 Telegram Bot \u0e1c\u0e48\u0e32\u0e19 BotFather \u0e41\u0e25\u0e30\u0e40\u0e0a\u0e37\u0e48\u0e2d\u0e21 webhook \u0e40\u0e1e\u0e37\u0e48\u0e2d\u0e23\u0e31\u0e1a\u0e02\u0e49\u0e2d\u0e04\u0e27\u0e32\u0e21\n\n## \ud83e\udde0 AI Brain Context\n- [walkthrough.md.metadata.json](https://raw.githubusercontent.com/oatrice/Akasa/feat/3-create-telegram-bot/docs/features/3_issue-3_phase-1-\u0e2a\u0e23\u0e32\u0e07-telegram-bot-webhook/ai_brain/walkthrough.md.metadata.json)\n- [walkthrough.md.resolved](https://raw.githubusercontent.com/oatrice/Akasa/feat/3-create-telegram-bot/docs/features/3_issue-3_phase-1-\u0e2a\u0e23\u0e32\u0e07-telegram-bot-webhook/ai_brain/walkthrough.md.resolved)\n- [task.md.resolved.5](https://raw.githubusercontent.com/oatrice/Akasa/feat/3-create-telegram-bot/docs/features/3_issue-3_phase-1-\u0e2a\u0e23\u0e32\u0e07-telegram-bot-webhook/ai_brain/task.md.resolved.5)\n- [task.md.resolved.2](https://raw.githubusercontent.com/oatrice/Akasa/feat/3-create-telegram-bot/docs/features/3_issue-3_phase-1-\u0e2a\u0e23\u0e32\u0e07-telegram-bot-webhook/ai_brain/task.md.resolved.2)\n- [task.md.metadata.json](https://raw.githubusercontent.com/oatrice/Akasa/feat/3-create-telegram-bot/docs/features/3_issue-3_phase-1-\u0e2a\u0e23\u0e32\u0e07-telegram-bot-webhook/ai_brain/task.md.metadata.json)\n- [task.md.resolved.3](https://raw.githubusercontent.com/oatrice/Akasa/feat/3-create-telegram-bot/docs/features/3_issue-3_phase-1-\u0e2a\u0e23\u0e32\u0e07-telegram-bot-webhook/ai_brain/task.md.resolved.3)\n- [task.md.resolved.4](https://raw.githubusercontent.com/oatrice/Akasa/feat/3-create-telegram-bot/docs/features/3_issue-3_phase-1-\u0e2a\u0e23\u0e32\u0e07-telegram-bot-webhook/ai_brain/task.md.resolved.4)\n- [implementation_plan.md.resolved.0](https://raw.githubusercontent.com/oatrice/Akasa/feat/3-create-telegram-bot/docs/features/3_issue-3_phase-1-\u0e2a\u0e23\u0e32\u0e07-telegram-bot-webhook/ai_brain/implementation_plan.md.resolved.0)\n- [task.md.resolved](https://raw.githubusercontent.com/oatrice/Akasa/feat/3-create-telegram-bot/docs/features/3_issue-3_phase-1-\u0e2a\u0e23\u0e32\u0e07-telegram-bot-webhook/ai_brain/task.md.resolved)\n- [implementation_plan.md.metadata.json](https://raw.githubusercontent.com/oatrice/Akasa/feat/3-create-telegram-bot/docs/features/3_issue-3_phase-1-\u0e2a\u0e23\u0e32\u0e07-telegram-bot-webhook/ai_brain/implementation_plan.md.metadata.json)\n- [implementation_plan.md.resolved](https://raw.githubusercontent.com/oatrice/Akasa/feat/3-create-telegram-bot/docs/features/3_issue-3_phase-1-\u0e2a\u0e23\u0e32\u0e07-telegram-bot-webhook/ai_brain/implementation_plan.md.resolved)\n- [task.md.resolved.1](https://raw.githubusercontent.com/oatrice/Akasa/feat/3-create-telegram-bot/docs/features/3_issue-3_phase-1-\u0e2a\u0e23\u0e32\u0e07-telegram-bot-webhook/ai_brain/task.md.resolved.1)\n- [task.md](https://raw.githubusercontent.com/oatrice/Akasa/feat/3-create-telegram-bot/docs/features/3_issue-3_phase-1-\u0e2a\u0e23\u0e32\u0e07-telegram-bot-webhook/ai_brain/task.md)\n- [task.md.resolved.0](https://raw.githubusercontent.com/oatrice/Akasa/feat/3-create-telegram-bot/docs/features/3_issue-3_phase-1-\u0e2a\u0e23\u0e32\u0e07-telegram-bot-webhook/ai_brain/task.md.resolved.0)\n- [walkthrough.md](https://raw.githubusercontent.com/oatrice/Akasa/feat/3-create-telegram-bot/docs/features/3_issue-3_phase-1-\u0e2a\u0e23\u0e32\u0e07-telegram-bot-webhook/ai_brain/walkthrough.md)\n- [implementation_plan.md](https://raw.githubusercontent.com/oatrice/Akasa/feat/3-create-telegram-bot/docs/features/3_issue-3_phase-1-\u0e2a\u0e23\u0e32\u0e07-telegram-bot-webhook/ai_brain/implementation_plan.md)\n- [walkthrough.md.resolved.0](https://raw.githubusercontent.com/oatrice/Akasa/feat/3-create-telegram-bot/docs/features/3_issue-3_phase-1-\u0e2a\u0e23\u0e32\u0e07-telegram-bot-webhook/ai_brain/walkthrough.md.resolved.0)\n",
  "url": "https://github.com/oatrice/Akasa/issues/3"
}

GIT CONTEXT:
COMMITS:
4f4b604 docs: sync AI brain artifacts
0d0151f fix(telegram): prevent auth bypass with empty webhook secret token
35d24e9 feat: add Telegram bot webhook integration with configuration management

STATS:
.env.example                                       |   4 +
 CHANGELOG.md                                       |  14 ++
 README.md                                          |  21 +-
 VERSION                                            |   2 +-
 app/config.py                                      |  18 ++
 app/main.py                                        |   3 +-
 app/models/telegram.py                             |  37 +++
 app/routers/telegram.py                            |  46 ++++
 conftest.py                                        |   5 +
 docs/ROADMAP.md                                    |   2 +-
 .../ai_brain/implementation_plan.md"               |  58 +++++
 .../ai_brain/implementation_plan.md.metadata.json" |   5 +
 .../ai_brain/implementation_plan.md.resolved"      |  58 +++++
 .../ai_brain/implementation_plan.md.resolved.0"    |  58 +++++
 .../ai_brain/task.md"                              |  18 ++
 .../ai_brain/task.md.metadata.json"                |   5 +
 .../ai_brain/task.md.resolved"                     |  18 ++
 .../ai_brain/task.md.resolved.0"                   |   8 +
 .../ai_brain/task.md.resolved.1"                   |   8 +
 .../ai_brain/task.md.resolved.2"                   |   8 +
 .../ai_brain/task.md.resolved.3"                   |   8 +
 .../ai_brain/task.md.resolved.4"                   |  18 ++
 .../ai_brain/task.md.resolved.5"                   |  18 ++
 .../ai_brain/walkthrough.md"                       |  41 ++++
 .../ai_brain/walkthrough.md.metadata.json"         |   5 +
 .../ai_brain/walkthrough.md.resolved"              |  41 ++++
 .../ai_brain/walkthrough.md.resolved.0"            |  41 ++++
 .../analysis.md"                                   | 266 +++++++++++++++++++++
 .../code_review.md"                                |  15 ++
 .../implementation_plan.md"                        |  58 +++++
 .../plan.md"                                       | 190 +++++++++++++++
 .../sbe.md"                                        |  55 +++++
 .../spec.md"                                       |  74 ++++++
 .../task.md"                                       |  18 ++
 .../walkthrough.md"                                |  41 ++++
 requirements.txt                                   |   1 +
 tests/__init__.py                                  |   0
 tests/routers/__init__.py                          |   0
 tests/routers/test_telegram.py                     | 118 +++++++++
 39 files changed, 1387 insertions(+), 17 deletions(-)

KEY FILE DIFFS:
diff --git a/app/config.py b/app/config.py
new file mode 100644
index 0000000..e6df185
--- /dev/null
+++ b/app/config.py
@@ -0,0 +1,18 @@
+"""
+Akasa Configuration — จัดการค่า settings จาก environment variables
+
+ใช้ pydantic-settings เพื่อโหลดค่าจากไฟล์ .env อัตโนมัติ
+"""
+
+from pydantic_settings import BaseSettings, SettingsConfigDict
+
+
+class Settings(BaseSettings):
+    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
+
+    TELEGRAM_BOT_TOKEN: str = ""
+    WEBHOOK_SECRET_TOKEN: str = ""
+    OPENROUTER_API_KEY: str = ""
+
+
+settings = Settings()
diff --git a/app/main.py b/app/main.py
index 967b93b..6395600 100644
--- a/app/main.py
+++ b/app/main.py
@@ -5,7 +5,7 @@ Akasa API — FastAPI Backend Entry Point
 """
 
 from fastapi import FastAPI
-from app.routers import health
+from app.routers import health, telegram
 
 app = FastAPI(
     title="Akasa API",
@@ -16,3 +16,4 @@ app = FastAPI(
 app.router.redirect_slashes = False
 
 app.include_router(health.router)
+app.include_router(telegram.router)
diff --git a/app/models/telegram.py b/app/models/telegram.py
new file mode 100644
index 0000000..9ef3e59
--- /dev/null
+++ b/app/models/telegram.py
@@ -0,0 +1,37 @@
+"""
+Telegram Pydantic Models — รองรับ Telegram Bot API Update object
+
+ใช้สำหรับ deserialize ข้อมูลที่ Telegram ส่งมาผ่าน Webhook
+"""
+
+from pydantic import BaseModel, Field
+from typing import Optional
+
+
+class TelegramUser(BaseModel):
+    """ผู้ใช้ Telegram"""
+    id: int
+    is_bot: bool = False
+    first_name: str = ""
+
+
+class Chat(BaseModel):
+    """Chat ที่ข้อความถูกส่งมา"""
+    id: int
+    type: str
+
+
+class Message(BaseModel):
+    """ข้อความจาก Telegram"""
+    message_id: int
+    chat: Chat
+    from_user: Optional[TelegramUser] = Field(None, alias="from")
+    date: int = 0
+    text: Optional[str] = None
+
+
+class Update(BaseModel):
+    """Telegram Update object — payload หลักที่ส่งมาทาง Webhook"""
+    update_id: int
+    message: Optional[Message] = None
+    edited_message: Optional[Message] = None
diff --git a/app/routers/telegram.py b/app/routers/telegram.py
new file mode 100644
index 0000000..7b45cbf
--- /dev/null
+++ b/app/routers/telegram.py
@@ -0,0 +1,46 @@
+"""
+Telegram Webhook Router — รับ Webhook จาก Telegram Bot API
+
+Endpoint: POST /api/v1/telegram/webhook
+- ตรวจสอบ Secret Token จาก Header
+- รับ Update object จาก Telegram
+- ในเฟสนี้แค่ log ยังไม่ประมวลผล
+"""
+
+import logging
+from fastapi import APIRouter, Depends, Header, HTTPException, status
+
+from app.config import settings
+from app.models.telegram import Update
+
+logger = logging.getLogger(__name__)
+
+router = APIRouter(prefix="/api/v1/telegram", tags=["Telegram"])
+
+
+async def verify_secret_token(
+    x_telegram_bot_api_secret_token: str = Header(None),
+):
+    """Dependency สำหรับตรวจสอบ Secret Token ที่ Telegram ส่งมาใน Header"""
+    if x_telegram_bot_api_secret_token is None:
+        raise HTTPException(
+            status_code=status.HTTP_403_FORBIDDEN,
+            detail="Secret token missing",
+        )
+    if not settings.WEBHOOK_SECRET_TOKEN or x_telegram_bot_api_secret_token != settings.WEBHOOK_SECRET_TOKEN:
+        raise HTTPException(
+            status_code=status.HTTP_403_FORBIDDEN,
+            detail="Invalid secret token",
+        )
+
+
+@router.post("/webhook", dependencies=[Depends(verify_secret_token)])
+async def telegram_webhook(update: Update):
+    """
+    รับ updates จาก Telegram Bot API
+
+    ในเฟสนี้แค่ log ข้อมูลที่ได้รับ
+    ยังไม่ประมวลผลหรือตอบกลับผู้ใช้
+    """
+    logger.info("Received Telegram update: %s", update.model_dump_json(indent=2))
+    return {"status": "ok"}
diff --git a/conftest.py b/conftest.py
new file mode 100644
index 0000000..40f64b0
--- /dev/null
+++ b/conftest.py
@@ -0,0 +1,5 @@
+import sys
+import os
+
+# เพิ่ม project root เข้า sys.path เพื่อให้ pytest หา module 'app' ได้
+sys.path.insert(0, os.path.dirname(__file__))
diff --git a/tests/__init__.py b/tests/__init__.py
new file mode 100644
index 0000000..e69de29
diff --git a/tests/routers/__init__.py b/tests/routers/__init__.py
new file mode 100644
index 0000000..e69de29
diff --git a/tests/routers/test_telegram.py b/tests/routers/test_telegram.py
new file mode 100644
index 0000000..6287716
--- /dev/null
+++ b/tests/routers/test_telegram.py
@@ -0,0 +1,118 @@
+"""
+Tests สำหรับ Telegram Webhook Router
+
+ครอบคลุม:
+- Happy path: token ถูกต้อง → 200
+- Invalid token → 403
+- Missing token → 403
+- Unsupported HTTP method → 405
+"""
+
+from unittest.mock import patch
+
+from fastapi.testclient import TestClient
+
+from app.main import app
+
+client = TestClient(app)
+WEBHOOK_URL = "/api/v1/telegram/webhook"
+TEST_SECRET_TOKEN = "a_very_secret_string_123"
+
+VALID_PAYLOAD = {
+    "update_id": 1,
+    "message": {
+        "message_id": 1,
+        "chat": {"id": 1, "type": "private"},
+        "date": 1678886400,
+        "text": "hello",
+    },
+}
+
+
+def test_webhook_success_valid_token():
+    """ส่ง request พร้อม Secret Token ที่ถูกต้อง → ต้องได้ 200 OK"""
+    with patch("app.routers.telegram.settings") as mock_settings:
+        mock_settings.WEBHOOK_SECRET_TOKEN = TEST_SECRET_TOKEN
+        response = client.post(
+            WEBHOOK_URL,
+            headers={"X-Telegram-Bot-Api-Secret-Token": TEST_SECRET_TOKEN},
+            json=VALID_PAYLOAD,
+        )
+    assert response.status_code == 200
+    assert response.json() == {"status": "ok"}
+
+
+def test_webhook_fail_invalid_token():
+    """ส่ง request พร้อม Secret Token ที่ผิด → ต้องได้ 403"""
+    with patch("app.routers.telegram.settings") as mock_settings:
+        mock_settings.WEBHOOK_SECRET_TOKEN = TEST_SECRET_TOKEN
+        response = client.post(
+            WEBHOOK_URL,
+            headers={"X-Telegram-Bot-Api-Secret-Token": "this_is_a_wrong_token"},
+            json=VALID_PAYLOAD,
+        )
+    assert response.status_code == 403
+    assert response.json() == {"detail": "Invalid secret token"}
+
+
+def test_webhook_fail_missing_token():
+    """ส่ง request โดยไม่มี Secret Token Header → ต้องได้ 403"""
+    response = client.post(WEBHOOK_URL, json=VALID_PAYLOAD)
+    assert response.status_code == 403
+    assert response.json() == {"detail": "Secret token missing"}
+
+
+def test_webhook_fail_unsupported_method():
+    """ใช้ GET method แทน POST → ต้องได้ 405"""
+    response = client.get(WEBHOOK_URL)
+    assert response.status_code == 405
+
+
+# === Code Review #3 — Test Suggestions ===
+
+
+def test_webhook_fail_malformed_payload():
+    """ส่ง JSON ที่โครงสร้างไม่ตรงกับ Update model → ต้องได้ 422"""
+    with patch("app.routers.telegram.settings") as mock_settings:
+        mock_settings.WEBHOOK_SECRET_TOKEN = TEST_SECRET_TOKEN
+        response = client.post(
+            WEBHOOK_URL,
+            headers={"X-Telegram-Bot-Api-Secret-Token": TEST_SECRET_TOKEN},
+            json={"invalid_field": "not an update"},
+        )
+    assert response.status_code == 422
+
+
+def test_webhook_fail_empty_secret_token_bypass():
+    """ป้องกัน auth bypass: ถ้า WEBHOOK_SECRET_TOKEN เป็น '' และ header ก็เป็น '' → ต้องได้ 403"""
+    with patch("app.routers.telegram.settings") as mock_settings:
+        mock_settings.WEBHOOK_SECRET_TOKEN = ""  # ค่าว่าง — ไม่ได้ตั้งค่า
+        response = client.post(
+            WEBHOOK_URL,
+            headers={"X-Telegram-Bot-Api-Secret-Token": ""},
+            json=VALID_PAYLOAD,
+        )
+    assert response.status_code == 403
+    assert response.json() == {"detail": "Invalid secret token"}
+
+
+def test_webhook_success_edited_message():
+    """ส่ง payload เป็น edited_message แทน message → ต้อง parse ได้ 200 OK"""
+    edited_message_payload = {
+        "update_id": 99,
+        "edited_message": {
+            "message_id": 5,
+            "chat": {"id": 1, "type": "private"},
+            "date": 1678886400,
+            "text": "edited text",
+        },
+    }
+    with patch("app.routers.telegram.settings") as mock_settings:
+        mock_settings.WEBHOOK_SECRET_TOKEN = TEST_SECRET_TOKEN
+        response = client.post(
+            WEBHOOK_URL,
+            headers={"X-Telegram-Bot-Api-Secret-Token": TEST_SECRET_TOKEN},
+            json=edited_message_payload,
+        )
+    assert response.status_code == 200
+    assert response.json() == {"status": "ok"}


PR TEMPLATE:


INSTRUCTIONS:
1. Generate a comprehensive PR description in Markdown format.
2. If a template is provided, fill it out intelligently.
3. If no template, use a standard structure: Summary, Changes, Impact.
4. Focus on 'Why' and 'What'.
5. Do not include 'Here is the PR description' preamble. Just the body.
6. IMPORTANT: Always use the exact FULL URL for closing issues. You must write `Closes https://github.com/oatrice/Akasa/issues/3`. Do NOT use short syntax (e.g., #123) and do not invent an owner/repo.
