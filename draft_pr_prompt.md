# PR Draft Prompt

You are an AI assistant helping to create a Pull Request description.
    
TASK: Add model field to TaskNotificationRequest and display in notifications
ISSUE: {
  "title": "Add model field to TaskNotificationRequest and display in notifications",
  "number": 90,
  "body": "## Feature Request: Add Model Field to TaskNotificationRequest\n\nCurrently, task notifications show the source (e.g., Antigravity, kilo, ...) but do not display which AI model was used to generate the response.\n\n### Proposed Changes\n1. Add a new optional `model` field to `TaskNotificationRequest` in `app/models/notification.py`:\n   - Type: `Optional[str] = None`\n   - Description: The AI model identifier used for the task\n\n2. Update `send_task_notification` in `app/services/telegram_service.py` to display the model:\n   - Add a line like `lines.append(f\"*Model:* {safe_model}\")` if `request.model` is present\n\n3. Modify notification senders to include the model:\n   - In `notify_task_complete` tool in `scripts/akasa_mcp_server.py`, retrieve the user's model preference and include it in the payload\n   - Update any other places where `TaskNotificationRequest` is created (e.g., test commands)\n\n### Benefits\n- Users can see which AI model generated the task result\n- Improved transparency for debugging and model selection\n- Consistent with source field display\n\n### Implementation Notes\n- Model should be retrieved from Redis user preferences (via chat_id)\n- Ensure backward compatibility by making the field optional\n- Use `escape_markdown_v2_content` for safe display in MarkdownV2\n\nPlease implement this to enhance notification clarity.\n\nCloses #90",
  "url": "https://github.com/oatrice/Akasa/issues/90"
}

GIT CONTEXT:
COMMITS:
7e78fd5 feat: Add model field to TaskNotificationRequest and dis...
6961f32 chore(release): bump version to 0.23.0 and update documentation
7b33742 feat(notifications): add support for AI model field in task notifications
e500b58 feat(notifications): include AI model in task notifications
19aea86 docs: add feature documentation and roadmap updates for issue #90

STATS:
.luma_metrics.json                                 |  22 ++
 CHANGELOG.md                                       |   9 +
 README.md                                          |   6 +-
 VERSION                                            |   2 +-
 app/models/notification.py                         |  15 +-
 app/routers/notifications.py                       |  20 +-
 app/services/telegram_service.py                   |  57 ++++--
 docs/ROADMAP.md                                    |   4 +
 .../analysis.md                                    | 223 +++++++++++++++++++++
 .../manual_verify.md                               | 208 +++++++++++++++++++
 .../manual_verify2.md                              |  60 ++++++
 .../plan.md                                        |  73 +++++++
 .../sbe.md                                         |  50 +++++
 .../spec.md                                        |  70 +++++++
 kilo.json                                          |  15 ++
 scripts/akasa_mcp_server.py                        |  16 +-
 tests/routers/test_notifications.py                |  30 +++
 tests/scripts/test_akasa_mcp_server.py             |  66 ++++++
 tests/services/test_telegram_service.py            |  35 +++-
 19 files changed, 950 insertions(+), 31 deletions(-)

KEY FILE DIFFS:
diff --git a/app/models/notification.py b/app/models/notification.py
index 9b59ae4..abd89a1 100644
--- a/app/models/notification.py
+++ b/app/models/notification.py
@@ -27,13 +27,24 @@ class NotificationResponse(BaseModel):
 class TaskNotificationRequest(BaseModel):
     project: Optional[str] = "General"
     task: str
-    status: Literal["starting", "success", "failure", "partial", "retrying", "limit_reached", "timeout"]
+    status: Literal[
+        "starting",
+        "success",
+        "failure",
+        "partial",
+        "retrying",
+        "limit_reached",
+        "timeout",
+    ]
     duration: Optional[str] = None  # e.g., "5m 20s"
     message: Optional[str] = None  # additional details / summary
     link: Optional[str] = None  # PR link, file, etc.
     source: Optional[str] = None  # "Gemini CLI", "Luma CLI", etc.
+    model: Optional[str] = None  # AI model identifier, e.g., "gpt-4o"
     chat_id: Optional[str] = None  # if not provided, backend uses AKASA_CHAT_ID
-    task_id: Optional[str] = None  # unique task ID for tracking (auto-generated if not provided)
+    task_id: Optional[str] = (
+        None  # unique task ID for tracking (auto-generated if not provided)
+    )
     retry_count: Optional[int] = Field(
         default=None, ge=1
     )  # current attempt number, 1-based (e.g., 2)
diff --git a/app/routers/notifications.py b/app/routers/notifications.py
index 8da6cf4..a453e75 100644
--- a/app/routers/notifications.py
+++ b/app/routers/notifications.py
@@ -15,7 +15,7 @@ from app.models.notification import (
     TaskNotificationResponse,
 )
 from app.services.agent_task_service import create_task, update_task
-from app.services.redis_service import redis_pool
+from app.services.redis_service import redis_pool, get_user_model_preference
 from app.services.telegram_service import tg_service
 
 logger = logging.getLogger(__name__)
@@ -121,9 +121,18 @@ async def task_complete_notification(
             detail="Invalid chat_id format. Must be numeric.",
         )
 
+    # Model resolution logic:
+    # - Use case 1 (External AI): If payload includes model (e.g., "SWE-1.6" from Windsurf),
+    #   use it directly to show which external AI performed the task
+    # - Use case 2 (Local AI): If payload has no model, retrieve user's preference
+    #   from Redis (set via /model command in Telegram) to show which model local AI used
+    if not payload.model:
+        model_pref = await get_user_model_preference(chat_id)
+        payload.model = model_pref
+
     logger.info(
         f"Task notification received — project: {payload.project!r}, "
-        f"task: {payload.task!r}, status: {payload.status}, source: {payload.source!r}"
+        f"task: {payload.task!r}, status: {payload.status}, source: {payload.source!r}, model: {payload.model!r}"
     )
 
     # Handle 'starting' status - create task log for timeout tracking
@@ -150,7 +159,12 @@ async def task_complete_notification(
             )
 
     # Update task log for completion statuses
-    if payload.task_id and payload.status in ("success", "failure", "partial", "timeout"):
+    if payload.task_id and payload.status in (
+        "success",
+        "failure",
+        "partial",
+        "timeout",
+    ):
         try:
             await update_task(
                 task_id=payload.task_id,
diff --git a/app/services/telegram_service.py b/app/services/telegram_service.py
index 0ebae10..4f18520 100644
--- a/app/services/telegram_service.py
+++ b/app/services/telegram_service.py
@@ -1,4 +1,5 @@
 import logging
+import os
 from typing import TYPE_CHECKING, Optional
 
 import httpx
@@ -25,7 +26,11 @@ class TelegramService:
         self.client = httpx.AsyncClient()
 
     async def send_message(
-        self, chat_id: int, text: str, reply_markup: Optional[dict] = None, parse_mode: Optional[str] = "MarkdownV2"
+        self,
+        chat_id: int,
+        text: str,
+        reply_markup: Optional[dict] = None,
+        parse_mode: Optional[str] = "MarkdownV2",
     ) -> None:
         """
         Sends a text message to a specific chat using the Telegram Bot API.
@@ -36,7 +41,7 @@ class TelegramService:
         }
         if parse_mode:
             payload["parse_mode"] = parse_mode
-            
+
         if reply_markup:
             payload["reply_markup"] = reply_markup
 
@@ -82,7 +87,7 @@ class TelegramService:
         message_id: int,
         text: str,
         reply_markup: Optional[dict] = None,
-        parse_mode: str = "MarkdownV2"
+        parse_mode: str = "MarkdownV2",
     ):
         """
         แก้ไขข้อความเดิม (ใช้สำหรับอัปเดตสถานะหลังจากกดปุ่ม)
@@ -190,26 +195,32 @@ class TelegramService:
             lines.append(f"*Duration:* {safe_duration}")
 
         if request.source:
-            logger.info(
-                f"[SOURCE DEBUG] raw source from payload: {request.source!r}"
-            )
+            logger.info(f"[SOURCE DEBUG] raw source from payload: {request.source!r}")
             normalized_source = normalize_source_display(request.source)
             logger.info(
                 f"[SOURCE DEBUG] after normalize_source_display: {normalized_source!r}"
             )
-            
+
             # Remove redundant project name from source. E.g., Project: "Akasa", Source: "Luma (Akasa)" -> "Luma"
             if request.project and normalized_source:
                 suffix = f"({request.project})"
-                if normalized_source.endswith(suffix) or normalized_source.endswith(suffix + " "):
+                if normalized_source.endswith(suffix) or normalized_source.endswith(
+                    suffix + " "
+                ):
                     # Might have a space before parentheses
                     prefix_end = normalized_source.rfind("(")
                     if prefix_end > 0:
                         normalized_source = normalized_source[:prefix_end].strip()
 
-            safe_source = escape_markdown_v2_content(normalized_source or request.source)
+            safe_source = escape_markdown_v2_content(
+                normalized_source or request.source
+            )
             lines.append(f"*Source:* {safe_source}")
 
+        if request.model:
+            safe_model = escape_markdown_v2_content(request.model)
+            lines.append(f"*Model:* {safe_model}")
+
         if request.message:
             msg = request.message
             if len(msg) > 300:
@@ -228,6 +239,13 @@ class TelegramService:
 
         text = "\n".join(lines)
 
+        # For testing: skip actual Telegram send if DISABLE_TELEGRAM is set
+        if os.getenv("DISABLE_TELEGRAM") == "1":
+            logger.info(
+                f"TELEGRAM DISABLED: Would send task notification to chat_id: {chat_id}, status: {request.status}, text: {text!r}"
+            )
+            return
+
         # Send pre-formatted MarkdownV2 directly — do NOT route through
         # send_message() as that would call escape_markdown_v2() again
         # and double-escape the already-escaped content.
@@ -236,15 +254,18 @@ class TelegramService:
             "text": text,
             "parse_mode": "MarkdownV2",
         }
-        response = await self.client.post(
-            f"{self.api_url}/sendMessage",
-            json=payload,
-            timeout=10.0,
-        )
-        response.raise_for_status()
-        logger.info(
-            f"Task notification sent to chat_id: {chat_id}, status: {request.status}"
-        )
+        try:
+            response = await self.client.post(
+                f"{self.api_url}/sendMessage",
+                json=payload,
+                timeout=10.0,
+            )
+            response.raise_for_status()
+            logger.info(
+                f"Task notification sent to chat_id: {chat_id}, status: {request.status}"
+            )
+        except Exception as e:
+            logger.error(f"Failed to send task notification: {e}")
 
     async def send_deployment_notification(
         self, chat_id: int, record: "DeploymentRecord"
diff --git a/scripts/akasa_mcp_server.py b/scripts/akasa_mcp_server.py
index fa20830..2e41f4c 100644
--- a/scripts/akasa_mcp_server.py
+++ b/scripts/akasa_mcp_server.py
@@ -39,7 +39,6 @@ MCP_SESSION_ID = str(uuid.uuid4())
 MCP_CLIENT_NAME = "Antigravity"
 
 
-
 async def request_remote_approval(
     command: str,
     cwd: str,
@@ -176,10 +175,15 @@ async def notify_task_complete(
     link: Optional[str] = None,
     retry_count: Optional[int] = None,
     max_retries: Optional[int] = None,
+    model: Optional[str] = None,
 ) -> dict:
     """
     ส่งการแจ้งเตือนสรุปงานไปยัง Akasa Backend เพื่อส่งต่อให้ผู้ใช้ผ่าน Telegram
 
+    Note: If model is provided, it will be used directly in the notification.
+    If not provided, the backend will attempt to retrieve the model from user
+    preferences stored in Redis.
+
     Args:
         project: ชื่อโปรเจกต์ที่กำลังทำงานอยู่
         task: คำอธิบายงานที่เพิ่งเสร็จสิ้น
@@ -189,6 +193,7 @@ async def notify_task_complete(
         link: URL ของ PR, ไฟล์, หรือแหล่งข้อมูลที่เกี่ยวข้อง (optional)
         retry_count: หมายเลข attempt ปัจจุบัน นับจาก 1 เช่น 2 (optional)
         max_retries: จำนวน retry สูงสุดที่อนุญาต เช่น 3 (optional)
+        model: AI model identifier (e.g., "SWE-1.6", "grok") (optional)
 
     Returns:
         dict: {"delivered": bool, "timestamp": str}
@@ -213,6 +218,8 @@ async def notify_task_complete(
         payload["retry_count"] = retry_count
     if max_retries is not None:
         payload["max_retries"] = max_retries
+    if model:
+        payload["model"] = model
 
     headers = {"X-Akasa-API-Key": AKASA_API_KEY}
 
@@ -339,6 +346,10 @@ TOOL_DEFINITIONS = [
                     "type": "integer",
                     "description": "Maximum number of retry attempts allowed, e.g., 3",
                 },
+                "model": {
+                    "type": "string",
+                    "description": "AI model identifier (e.g., 'SWE-1.6', 'grok', 'gpt-4o'). If not provided, backend will use user's model preference from Redis.",
+                },
             },
             "required": ["project", "task", "status"],
         },
@@ -356,7 +367,7 @@ def make_error(req_id, code, message):
     )
 
 
-async def handle_rpc(request: dict) -> str:
+async def handle_rpc(request: dict) -> Optional[str]:
     """Handle a single JSON-RPC request"""
     global MCP_CLIENT_NAME
     req_id = request.get("id")
@@ -460,6 +471,7 @@ async def handle_rpc(request: dict) -> str:
                     link=arguments.get("link"),
                     retry_count=arguments.get("retry_count"),
                     max_retries=arguments.get("max_retries"),
+                    model=arguments.get("model"),
                 )
                 delivered = result.get("delivered", False)
                 if delivered:
diff --git a/tests/routers/test_notifications.py b/tests/routers/test_notifications.py
index f76abce..0807a8a 100644
--- a/tests/routers/test_notifications.py
+++ b/tests/routers/test_notifications.py
@@ -30,6 +30,12 @@ def mock_redis_service():
         yield mock
 
 
+@pytest.fixture
+def mock_get_user_model_preference():
+    with patch("app.routers.notifications.get_user_model_preference") as mock:
+        yield mock
+
+
 def test_send_notification_unauthorized():
     """ต้องคืนค่า 401 ถ้า API Key ไม่ถูกต้องหรือหายไป"""
     response = client.post(
@@ -247,6 +253,30 @@ async def test_task_complete_success_fallback_to_akasa_chat_id(
     assert call_kwargs["chat_id"] == 6346467495
 
 
+@pytest.mark.asyncio
+async def test_task_complete_includes_model_preference(
+    mock_tg_service, mock_get_user_model_preference
+):
+    """Model preference retrieved from Redis and included in notification request."""
+    mock_tg_service.send_task_notification = AsyncMock(return_value=None)
+    mock_get_user_model_preference.return_value = "gpt-4o"
+    app.dependency_overrides[verify_api_key] = lambda: True
+
+    payload = {**VALID_TASK_PAYLOAD, "chat_id": "6346467495"}
+
+    response = client.post(
+        TASK_COMPLETE_URL,
+        json=payload,
+        headers={"X-Akasa-API-Key": "valid-key"},
+    )
+
+    assert response.status_code == 200
+    mock_get_user_model_preference.assert_called_once_with(6346467495)
+    call_kwargs = mock_tg_service.send_task_notification.call_args.kwargs
+    request = call_kwargs["request"]
+    assert request.model == "gpt-4o"
+
+
 def test_task_complete_no_chat_id_and_no_server_default(mock_tg_service, monkeypatch):
     """ต้องคืนค่า 400 ถ้าไม่มี chat_id ใน payload และ AKASA_CHAT_ID ก็ไม่ได้ตั้งค่า"""
     app.dependency_overrides[verify_api_key] = lambda: True
diff --git a/tests/scripts/test_akasa_mcp_server.py b/tests/scripts/test_akasa_mcp_server.py
index c8c8312..7437a65 100644
--- a/tests/scripts/test_akasa_mcp_server.py
+++ b/tests/scripts/test_akasa_mcp_server.py
@@ -430,6 +430,71 @@ class TestNotifyTaskComplete:
         assert payload["message"] == "PR #42 created with 3 commits"
         assert payload["link"] == "https://github.com/oatrice/Akasa/pull/42"
 
+    @pytest.mark.asyncio
+    async def test_notify_task_complete_includes_model_when_provided(self):
+        """Model field ต้องถูกรวมใน payload เมื่อระบุ"""
+        from scripts.akasa_mcp_server import notify_task_complete
+
+        mock_response = MagicMock()
+        mock_response.json.return_value = {
+            "delivered": True,
+            "timestamp": "2026-03-13T10:00:00+00:00",
+        }
+        mock_response.raise_for_status = MagicMock()
+
+        mock_client = AsyncMock()
+        mock_client.post.return_value = mock_response
+        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
+        mock_client.__aexit__ = AsyncMock(return_value=False)
+
+        with (
+            patch(
+                "scripts.akasa_mcp_server.httpx.AsyncClient", return_value=mock_client
+            ),
+            patch("scripts.akasa_mcp_server.AKASA_CHAT_ID", "6346467495"),
+        ):
+            await notify_task_complete(
+                project="Akasa",
+                task="Implement feature",
+                status="success",
+                model="SWE-1.6",
+            )
+
+        payload = mock_client.post.call_args.kwargs["json"]
+        assert payload["model"] == "SWE-1.6"
+
+    @pytest.mark.asyncio
+    async def test_notify_task_complete_excludes_model_when_not_provided(self):
+        """Model field ต้องไม่ปรากฏใน payload เมื่อไม่ระบุ"""
+        from scripts.akasa_mcp_server import notify_task_complete
+
+        mock_response = MagicMock()
+        mock_response.json.return_value = {
+            "delivered": True,
+            "timestamp": "2026-03-13T10:00:00+00:00",
+        }
+        mock_response.raise_for_status = MagicMock()
+
+        mock_client = AsyncMock()
+        mock_client.post.return_value = mock_response
+        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
+        mock_client.__aexit__ = AsyncMock(return_value=False)
+
+        with (
+            patch(
+                "scripts.akasa_mcp_server.httpx.AsyncClient", return_value=mock_client
+            ),
+            patch("scripts.akasa_mcp_server.AKASA_CHAT_ID", "6346467495"),
+        ):
+            await notify_task_complete(
+                project="Akasa",
+                task="Implement feature",
+                status="success",
+            )
+
+        payload = mock_client.post.call_args.kwargs["json"]
+        assert "model" not in payload
+
     @pytest.mark.asyncio
     async def test_handle_rpc_notify_task_complete_delivered(self):
         """tools/call notify_task_complete → delivered=True → ข้อความสำเร็จ"""
@@ -550,6 +615,7 @@ class TestNotifyTaskComplete:
         assert "link" in properties
         assert "retry_count" in properties
         assert "max_retries" in properties
+        assert "model" in properties
 
         # status field ต้องมี enum ครบ 5 ค่า
         status_enum = properties["status"].get("enum", [])
diff --git a/tests/services/test_telegram_service.py b/tests/services/test_telegram_service.py
index f0bb2e4..c3c4779 100644
--- a/tests/services/test_telegram_service.py
+++ b/tests/services/test_telegram_service.py
@@ -100,9 +100,12 @@ async def test_send_proactive_message_success(mock_redis):
         await tg_service.send_proactive_message(user_id, text)
 
         mock_redis.get_chat_id_for_user.assert_called_once_with(user_id)
-        
+
         from app.utils.markdown_utils import escape_markdown_v2
-        mock_send_message.assert_called_once_with(chat_id=chat_id, text=escape_markdown_v2(text))
+
+        mock_send_message.assert_called_once_with(
+            chat_id=chat_id, text=escape_markdown_v2(text)
+        )
 
 
 @pytest.mark.asyncio
@@ -364,6 +367,34 @@ async def test_send_task_notification_optional_fields_omitted(monkeypatch):
         assert "*Source:*" not in text
         assert "*Details:*" not in text
         assert "*Link:*" not in text
+        assert "*Model:*" not in text
+
+
+@pytest.mark.asyncio
+async def test_send_task_notification_with_model(monkeypatch):
+    """Model field appears as *Model:* line when provided."""
+    from app.models.notification import TaskNotificationRequest
+
+    monkeypatch.setattr(
+        tg_service, "api_url", "https://api.telegram.org/bot_test_token"
+    )
+
+    request = TaskNotificationRequest(
+        project="Akasa",
+        task="Test task",
+        status="success",
+        model="gpt-4o",
+    )
+
+    with patch.object(tg_service.client, "post", new_callable=AsyncMock) as mock_post:
+        mock_response = MagicMock()
+        mock_response.raise_for_status = MagicMock()
+        mock_post.return_value = mock_response
+
+        await tg_service.send_task_notification(chat_id=12345, request=request)
+
+        text = mock_post.call_args.kwargs["json"]["text"]
+        assert "*Model:* gpt\\-4o" in text
 
 
 @pytest.mark.asyncio


PR TEMPLATE:


INSTRUCTIONS:
1. Generate a comprehensive PR description in Markdown format.
2. If a template is provided, fill it out intelligently.
3. If no template, use a standard structure: Summary, Changes, Impact.
4. Focus on 'Why' and 'What'.
5. Do not include 'Here is the PR description' preamble. Just the body.
6. IMPORTANT: Always use the exact FULL URL for closing issues. You must write `Closes https://github.com/oatrice/Akasa/issues/90`. Do NOT use short syntax (e.g., #123) and do not invent an owner/repo.
