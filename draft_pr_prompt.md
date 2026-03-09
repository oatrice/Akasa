# PR Draft Prompt

You are an AI assistant helping to create a Pull Request description.
    
TASK: [Service] Support Outbound Messaging in TelegramService
ISSUE: {
  "title": "[Service] Support Outbound Messaging in TelegramService",
  "number": 30,
  "body": "## Objective\n\u0e40\u0e1e\u0e34\u0e48\u0e21\u0e04\u0e27\u0e32\u0e21\u0e2a\u0e32\u0e21\u0e32\u0e23\u0e16\u0e43\u0e2b\u0e49 `TelegramService` \u0e2a\u0e32\u0e21\u0e32\u0e23\u0e16\u0e2a\u0e48\u0e07\u0e02\u0e49\u0e2d\u0e04\u0e27\u0e32\u0e21\u0e2b\u0e32 User \u0e44\u0e14\u0e49\u0e17\u0e31\u0e19\u0e17\u0e35\u0e42\u0e14\u0e22\u0e44\u0e21\u0e48\u0e15\u0e49\u0e2d\u0e07\u0e23\u0e2d\u0e43\u0e2b\u0e49 User \u0e17\u0e31\u0e01\u0e21\u0e32\u0e01\u0e48\u0e2d\u0e19 (Proactive Messaging)\n\n## Technical Details\n- \u0e40\u0e1e\u0e34\u0e48\u0e21 Method `send_proactive_message(user_id: str, text: str)`\n- \u0e14\u0e36\u0e07 `chat_id` \u0e02\u0e2d\u0e07 User \u0e08\u0e32\u0e01 Redis (\u0e17\u0e35\u0e48\u0e40\u0e01\u0e47\u0e1a\u0e44\u0e27\u0e49\u0e15\u0e2d\u0e19 User \u0e17\u0e31\u0e01\u0e21\u0e32\u0e04\u0e23\u0e31\u0e49\u0e07\u0e41\u0e23\u0e01)\n- \u0e08\u0e31\u0e14\u0e01\u0e32\u0e23 Error handling \u0e01\u0e23\u0e13\u0e35\u0e1a\u0e2d\u0e17\u0e16\u0e39\u0e01 Block \u0e2b\u0e23\u0e37\u0e2d `chat_id` \u0e2b\u0e21\u0e14\u0e2d\u0e32\u0e22\u0e38\n\n## \ud83e\udde0 AI Brain Context\n- [error_state_offline_verified_1772922951712.png](https://raw.githubusercontent.com/oatrice/Akasa/feat/30-telegram-outbound-messaging/docs/features/11_issue-30_service-support-outbound-messaging-in-telegramservice/ai_brain/error_state_offline_verified_1772922951712.png)\n- [task.md](https://raw.githubusercontent.com/oatrice/Akasa/feat/30-telegram-outbound-messaging/docs/features/11_issue-30_service-support-outbound-messaging-in-telegramservice/ai_brain/task.md)\n- [walkthrough.md](https://raw.githubusercontent.com/oatrice/Akasa/feat/30-telegram-outbound-messaging/docs/features/11_issue-30_service-support-outbound-messaging-in-telegramservice/ai_brain/walkthrough.md)\n- [code_review_summary.md](https://raw.githubusercontent.com/oatrice/Akasa/feat/30-telegram-outbound-messaging/docs/features/11_issue-30_service-support-outbound-messaging-in-telegramservice/ai_brain/code_review_summary.md)\n- [error_state_initial_1772922095185.png](https://raw.githubusercontent.com/oatrice/Akasa/feat/30-telegram-outbound-messaging/docs/features/11_issue-30_service-support-outbound-messaging-in-telegramservice/ai_brain/error_state_initial_1772922095185.png)\n- [web_offline_test_1772921949174.webp](https://raw.githubusercontent.com/oatrice/Akasa/feat/30-telegram-outbound-messaging/docs/features/11_issue-30_service-support-outbound-messaging-in-telegramservice/ai_brain/web_offline_test_1772921949174.webp)\n- [implementation_plan.md](https://raw.githubusercontent.com/oatrice/Akasa/feat/30-telegram-outbound-messaging/docs/features/11_issue-30_service-support-outbound-messaging-in-telegramservice/ai_brain/implementation_plan.md)\n- [analysis_issue50.md](https://raw.githubusercontent.com/oatrice/Akasa/feat/30-telegram-outbound-messaging/docs/features/11_issue-30_service-support-outbound-messaging-in-telegramservice/ai_brain/analysis_issue50.md)\n\n\nCloses #30",
  "url": "https://github.com/oatrice/Akasa/issues/30"
}

GIT CONTEXT:
COMMITS:
c4d1cb1 docs: sync AI brain artifacts
5ba7e14 chore(release): version 0.10.0 with outbound messaging support
915ee71 docs: add Luma code review report with type fixes and test guidance
1ac940c test(chat): fix Update object creation to handle 'from' alias
100c5e0 test(chat): fix mock decorator order in handle_chat_message test
e0da367 test: refactor chat service test to use @patch decorators
56b7f19 refactor: rename telegram_service singleton to tg_service
bd1636a test(chat_service): use patch.object to avoid mock naming collisions
4cdcef1 feat: add user-chat ID mapping for proactive messaging support
f35e07c docs: add analysis for TelegramService proactive messaging (issue-30)
06cbcf0 docs: document /note command and project-specific memory feature
df82a64 feat: [Feature] Project-Specific Memory & Context Restor...
e3391e1 docs: sync AI brain artifacts
a8ad906 docs: add Luma code review report identifying test assertion bug
ab80547 feat: Add agent state persistence and context restoration

STATS:
CHANGELOG.md                                       |  22 ++
 README.md                                          |  16 ++
 VERSION                                            |   2 +-
 app/exceptions.py                                  |  11 +
 app/services/chat_service.py                       |  43 ++--
 app/services/redis_service.py                      |  19 ++
 app/services/telegram_service.py                   |  60 +++--
 docs/ROADMAP.md                                    |   3 +-
 .../ai_brain/analysis_issue50.md                   |  40 ++++
 .../ai_brain/code_review_summary.md                |  76 +++++++
 .../ai_brain/error_state_initial_1772922095185.png | Bin 0 -> 111704 bytes
 .../error_state_offline_verified_1772922951712.png | Bin 0 -> 117217 bytes
 .../ai_brain/implementation_plan.md                | 106 +++++++++
 .../ai_brain/task.md                               |  34 +++
 .../ai_brain/walkthrough.md                        |  35 +++
 .../ai_brain/web_offline_test_1772921949174.webp   | Bin 0 -> 16877970 bytes
 .../analysis.md                                    | 252 +++++++++++++++++++++
 .../code_review.md                                 | 144 ++++++++++++
 .../plan.md                                        |  93 ++++++++
 .../sbe.md                                         |  52 +++++
 .../spec.md                                        | 106 +++++++++
 docs/technical_notes/python_mocking_pitfalls.md    |  72 ++++++
 tests/services/test_chat_service.py                | 102 +++++++--
 tests/services/test_redis_service.py               |  26 +++
 tests/services/test_telegram_service.py            | 141 +++++++++---
 25 files changed, 1372 insertions(+), 83 deletions(-)

KEY FILE DIFFS:
diff --git a/app/exceptions.py b/app/exceptions.py
new file mode 100644
index 0000000..e87ea5f
--- /dev/null
+++ b/app/exceptions.py
@@ -0,0 +1,11 @@
+"""
+Custom, application-specific exceptions.
+"""
+
+class UserChatIdNotFoundException(Exception):
+    """Raised when the chat_id for a given user_id cannot be found."""
+    pass
+
+class BotBlockedException(Exception):
+    """Raised when a message fails because the user has blocked the bot."""
+    pass
diff --git a/app/services/chat_service.py b/app/services/chat_service.py
index 3cdb585..6cf8d5c 100644
--- a/app/services/chat_service.py
+++ b/app/services/chat_service.py
@@ -5,9 +5,10 @@ Flow: Telegram → ดึง history จาก Redis → สร้าง message
 Graceful degradation: ถ้า Redis ล่ม ยังทำงานได้เป็น stateless
 """
 
-from app.models.telegram import Update
+from app.models.telegram import Update, Message
 from app.models.agent_state import AgentState
-from app.services import llm_service, telegram_service, redis_service
+from app.services import llm_service, redis_service
+from app.services.telegram_service import tg_service # Import the renamed instance
 import httpx
 import logging
 import os
@@ -59,7 +60,7 @@ async def _send_response(chat_id: int, text: str) -> None:
         final_text = f"{text}\n\n---\n*Local Dev Info*\n{build_info}"
     
     try:
-        await telegram_service.send_message(chat_id, final_text)
+        await tg_service.send_message(chat_id, final_text)
     except httpx.HTTPStatusError as e:
         logger.error(f"Failed to send message to Telegram for {chat_id}. HTTP Status Error: {e}")
     except Exception as e:
@@ -74,27 +75,36 @@ async def handle_chat_message(update: Update) -> None:
     if not update.message or not update.message.text:
         return
 
-    chat_id = update.message.chat.id
-    text = update.message.text.strip()
-    print(f"--- [DEBUG] Processing message from {chat_id}: {text} ---")
+    # --- Issue #30: Proactive Messaging Support ---
+    if update.message and update.message.from_user:
+        try:
+            await redis_service.set_user_chat_id_mapping(
+                user_id=update.message.from_user.id,
+                chat_id=update.message.chat.id
+            )
+        except Exception as e:
+            logger.warning(f"Failed to set user_chat_id mapping for user {update.message.from_user.id}: {e}")
+    # ---------------------------------------------
 
-    if text.startswith("/"):
-        await _handle_command(chat_id, text)
+    if update.message.text.startswith("/"):
+        await _handle_command(update.message)
     else:
-        await _handle_standard_message(chat_id, text)
+        await _handle_standard_message(update.message)
 
 
-async def _handle_command(chat_id: int, command_text: str) -> None:
+async def _handle_command(message: "Message") -> None:
     """จัดการคำสั่งต่างๆ (เช่น /model, /project)"""
-    parts = command_text.split()
+    chat_id = message.chat.id
+    parts = message.text.split()
     cmd = parts[0].lower()
+    args = parts[1:] if len(parts) > 1 else []
     
     if cmd == "/model":
-        await _handle_model_command(chat_id, parts[1:] if len(parts) > 1 else [])
+        await _handle_model_command(chat_id, args)
     elif cmd == "/project":
-        await _handle_project_command(chat_id, parts[1:] if len(parts) > 1 else [])
+        await _handle_project_command(chat_id, args)
     elif cmd == "/note" and len(parts) > 1:
-        await _handle_note_command(chat_id, parts[1:])
+        await _handle_note_command(chat_id, args)
     else:
         await _send_response(chat_id, f"❌ Unknown command: {cmd}")
 
@@ -239,8 +249,11 @@ async def _handle_project_command(chat_id: int, args: list[str]) -> None:
         await _send_response(chat_id, "❌ Invalid usage. Try `/project` for help.")
 
 
-async def _handle_standard_message(chat_id: int, prompt: str) -> None:
+async def _handle_standard_message(message: "Message") -> None:
     """จัดการข้อความปกติ (ดึง history, เรียก LLM, บันทึก history)"""
+    chat_id = message.chat.id
+    prompt = message.text.strip()
+    print(f"--- [DEBUG] Processing message from {chat_id}: {prompt} ---")
     
     # 1. ดึงโปรเจ็กต์ปัจจุบัน
     current_project = await redis_service.get_current_project(chat_id)
diff --git a/app/services/redis_service.py b/app/services/redis_service.py
index 0198fde..ba4b4c5 100644
--- a/app/services/redis_service.py
+++ b/app/services/redis_service.py
@@ -180,3 +180,22 @@ async def set_agent_state(chat_id: int, project_name: str, state: AgentState):
     state_key = _get_agent_state_key(chat_id, project_name)
     json_str = state.to_json()
     await redis_pool.set(state_key, json_str, ex=settings.REDIS_TTL_SECONDS)
+
+
+# --- User ID to Chat ID Mapping (for Proactive Messaging) ---
+
+async def set_user_chat_id_mapping(user_id: int, chat_id: int):
+    """
+    เก็บ mapping ระหว่าง user_id ของ Telegram กับ chat_id ล่าสุด.
+    """
+    key = f"user_chat_id:{user_id}"
+    # Chat ID ควรจะเป็น str เสมอตาม convention ของ Redis
+    await redis_pool.set(key, str(chat_id), ex=settings.REDIS_TTL_SECONDS)
+
+
+async def get_chat_id_for_user(user_id: int) -> Optional[str]:
+    """
+    ดึง chat_id ล่าสุดที่ผูกกับ user_id.
+    """
+    key = f"user_chat_id:{user_id}"
+    return await redis_pool.get(key)
diff --git a/app/services/telegram_service.py b/app/services/telegram_service.py
index 1cfc61c..79c5658 100644
--- a/app/services/telegram_service.py
+++ b/app/services/telegram_service.py
@@ -1,23 +1,55 @@
 import httpx
 from app.config import settings
 from app.utils.markdown_utils import escape_markdown_v2
+from app.services import redis_service
+from app.exceptions import UserChatIdNotFoundException, BotBlockedException
+import logging
 
-async def send_message(chat_id: int, text: str) -> None:
-    """
-    Sends a text message to a specific chat using the Telegram Bot API.
-    """
-    api_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
-    
-    payload = {
-        "chat_id": chat_id,
-        "text": escape_markdown_v2(text),
-        "parse_mode": "MarkdownV2"
-    }
+logger = logging.getLogger(__name__)
 
-    async with httpx.AsyncClient() as client:
-        response = await client.post(
-            api_url,
+class TelegramService:
+    def __init__(self, bot_token: str):
+        self.api_url = f"https://api.telegram.org/bot{bot_token}"
+        self.client = httpx.AsyncClient()
+
+    async def send_message(self, chat_id: int, text: str) -> None:
+        """
+        Sends a text message to a specific chat using the Telegram Bot API.
+        """
+        payload = {
+            "chat_id": chat_id,
+            "text": escape_markdown_v2(text),
+            "parse_mode": "MarkdownV2"
+        }
+
+        response = await self.client.post(
+            f"{self.api_url}/sendMessage",
             json=payload,
             timeout=10.0
         )
         response.raise_for_status()
+
+    async def send_proactive_message(self, user_id: int, text: str):
+        """
+        Sends a proactive message to a user by their user_id.
+        """
+        chat_id_str = await redis_service.get_chat_id_for_user(user_id)
+        
+        if not chat_id_str:
+            logger.error(f"Chat ID not found for user_id: {user_id}")
+            raise UserChatIdNotFoundException(f"Chat ID not found for user_id: {user_id}")
+
+        chat_id = int(chat_id_str)
+        try:
+            await self.send_message(chat_id=chat_id, text=text)
+            logger.info(f"Proactive message sent to user_id: {user_id}")
+        except httpx.HTTPStatusError as e:
+            if e.response.status_code == 403:
+                logger.warning(f"Failed to send to user_id {user_id}: Bot was blocked.")
+                raise BotBlockedException(f"Bot was blocked by user_id: {user_id}")
+            else:
+                logger.error(f"HTTP error sending proactive message to user_id {user_id}: {e}")
+                raise  # Re-raise other HTTP errors
+
+# Create a singleton instance for the application to use
+tg_service = TelegramService(settings.TELEGRAM_BOT_TOKEN)
diff --git a/tests/services/test_chat_service.py b/tests/services/test_chat_service.py
index 74a04b1..d0c387d 100644
--- a/tests/services/test_chat_service.py
+++ b/tests/services/test_chat_service.py
@@ -53,7 +53,7 @@ def setup_mock_redis(mock_redis):
 
 @pytest.mark.asyncio
 @patch("app.services.chat_service.redis_service")
-@patch("app.services.chat_service.telegram_service")
+@patch("app.services.chat_service.tg_service")
 @patch("app.services.chat_service.llm_service")
 async def test_handle_chat_message_success_with_history(mock_llm, mock_telegram, mock_redis, mock_update):
     """ส่ง prompt พร้อม history ที่ดึงจาก Redis ไปให้ LLM โดยแยกตามโปรเจ็กต์"""
@@ -85,10 +85,9 @@ async def test_handle_chat_message_success_with_history(mock_llm, mock_telegram,
     mock_redis.add_message_to_history.assert_any_call(12345, "user", "Hello Bot", project_name="default")
     mock_redis.add_message_to_history.assert_any_call(12345, "assistant", "Reply from AI", project_name="default")
 
-
 @pytest.mark.asyncio
 @patch("app.services.chat_service.redis_service")
-@patch("app.services.chat_service.telegram_service")
+@patch("app.services.chat_service.tg_service")
 @patch("app.services.chat_service.llm_service")
 async def test_handle_chat_message_no_history(mock_llm, mock_telegram, mock_redis, mock_update):
     """ถ้าไม่มี history ต้องส่งแค่ message เดียว"""
@@ -111,7 +110,7 @@ async def test_handle_chat_message_no_history(mock_llm, mock_telegram, mock_redi
 
 @pytest.mark.asyncio
 @patch("app.services.chat_service.redis_service")
-@patch("app.services.chat_service.telegram_service")
+@patch("app.services.chat_service.tg_service")
 @patch("app.services.chat_service.llm_service")
 async def test_handle_chat_message_redis_get_failure(mock_llm, mock_telegram, mock_redis, mock_update):
     """ถ้า Redis ล่ม ตอนดึง history → ยังทำงานได้ (ส่งแค่ prompt เดียว)"""
@@ -133,7 +132,7 @@ async def test_handle_chat_message_redis_get_failure(mock_llm, mock_telegram, mo
 
 @pytest.mark.asyncio
 @patch("app.services.chat_service.redis_service")
-@patch("app.services.chat_service.telegram_service")
+@patch("app.services.chat_service.tg_service")
 @patch("app.services.chat_service.llm_service")
 async def test_handle_chat_message_redis_save_failure(mock_llm, mock_telegram, mock_redis, mock_update):
     """ถ้า Redis ล่ม ตอนบันทึก history → ยังส่ง response ไป Telegram ได้ปกติ"""
@@ -154,7 +153,7 @@ async def test_handle_chat_message_redis_save_failure(mock_llm, mock_telegram, m
 
 @pytest.mark.asyncio
 @patch("app.services.chat_service.redis_service")
-@patch("app.services.chat_service.telegram_service")
+@patch("app.services.chat_service.tg_service")
 @patch("app.services.chat_service.llm_service")
 async def test_handle_chat_message_no_text(mock_llm, mock_telegram, mock_redis, mock_update_no_text):
     """Ignore updates ที่ไม่มี text"""
@@ -165,7 +164,7 @@ async def test_handle_chat_message_no_text(mock_llm, mock_telegram, mock_redis,
 
 @pytest.mark.asyncio
 @patch("app.services.chat_service.redis_service")
-@patch("app.services.chat_service.telegram_service")
+@patch("app.services.chat_service.tg_service")
 @patch("app.services.chat_service.llm_service")
 async def test_handle_chat_message_llm_error(mock_llm, mock_telegram, mock_redis, mock_update):
     """ถ้า LLM error → จะส่งข้อความแจ้งเตือนกลับไปให้ user แทนการตอบปกติ"""
@@ -185,7 +184,7 @@ async def test_handle_chat_message_llm_error(mock_llm, mock_telegram, mock_redis
 
 @pytest.mark.asyncio
 @patch("app.services.chat_service.redis_service")
-@patch("app.services.chat_service.telegram_service")
+@patch("app.services.chat_service.tg_service")
 @patch("app.services.chat_service.llm_service")
 async def test_handle_chat_message_telegram_error(mock_llm, mock_telegram, mock_redis, mock_update):
     """ถ้า Telegram error → ไม่ crash"""
@@ -202,7 +201,7 @@ async def test_handle_chat_message_telegram_error(mock_llm, mock_telegram, mock_
 
 @pytest.mark.asyncio
 @patch("app.services.chat_service.redis_service")
-@patch("app.services.chat_service.telegram_service")
+@patch("app.services.chat_service.tg_service")
 @patch("app.services.chat_service.llm_service")
 async def test_handle_chat_message_timeout(mock_llm, mock_telegram, mock_redis, mock_update):
     """ถ้า LLM timeout → จะส่งข้อความแจ้งเตือนกลับไป"""
@@ -219,7 +218,7 @@ async def test_handle_chat_message_timeout(mock_llm, mock_telegram, mock_redis,
 
 @pytest.mark.asyncio
 @patch("app.services.chat_service.redis_service")
-@patch("app.services.chat_service.telegram_service")
+@patch("app.services.chat_service.tg_service")
 @patch("app.services.chat_service.llm_service")
 async def test_handle_chat_message_llm_malformed_data(mock_llm, mock_telegram, mock_redis, mock_update):
     """ถ้า LLM ตอบกลับมาผิดฟอร์ม (ValueError/KeyError) → จะส่งข้อความแจ้งเตือน"""
@@ -237,7 +236,7 @@ async def test_handle_chat_message_llm_malformed_data(mock_llm, mock_telegram, m
 
 @pytest.mark.asyncio
 @patch("app.services.chat_service.redis_service")
-@patch("app.services.chat_service.telegram_service")
+@patch("app.services.chat_service.tg_service")
 @patch("app.services.chat_service.llm_service")
 async def test_handle_chat_message_llm_unexpected_error(mock_llm, mock_telegram, mock_redis, mock_update):
     """ถ้าเกิด Error ที่ไม่คาดคิดตอนเรียก LLM → จะส่งข้อความแจ้งเตือน generic กลับไป"""
@@ -257,7 +256,7 @@ async def test_handle_chat_message_llm_unexpected_error(mock_llm, mock_telegram,
 
 @pytest.mark.asyncio
 @patch("app.services.chat_service.redis_service")
-@patch("app.services.chat_service.telegram_service")
+@patch("app.services.chat_service.tg_service")
 @patch("app.services.chat_service.llm_service")
 async def test_system_prompt_prepended_with_history(mock_llm, mock_telegram, mock_redis, mock_update):
     """System prompt ต้องถูกวางเป็นข้อความแรกใน messages ที่ส่งให้ LLM (มี history)"""
@@ -286,7 +285,7 @@ async def test_system_prompt_prepended_with_history(mock_llm, mock_telegram, moc
 
 @pytest.mark.asyncio
 @patch("app.services.chat_service.redis_service")
-@patch("app.services.chat_service.telegram_service")
+@patch("app.services.chat_service.tg_service")
 @patch("app.services.chat_service.llm_service")
 async def test_system_prompt_prepended_no_history(mock_llm, mock_telegram, mock_redis, mock_update):
     """System prompt ต้องถูกวางเป็นข้อความแรกแม้ไม่มี history"""
@@ -308,7 +307,7 @@ async def test_system_prompt_prepended_no_history(mock_llm, mock_telegram, mock_
 
 @pytest.mark.asyncio
 @patch("app.services.chat_service.redis_service")
-@patch("app.services.chat_service.telegram_service")
+@patch("app.services.chat_service.tg_service")
 @patch("app.services.chat_service.llm_service")
 async def test_system_prompt_not_saved_to_redis(mock_llm, mock_telegram, mock_redis, mock_update):
     """System prompt ต้องไม่ถูกบันทึกลง Redis"""
@@ -334,7 +333,7 @@ async def test_system_prompt_not_saved_to_redis(mock_llm, mock_telegram, mock_re
 @pytest.mark.asyncio
 @patch("app.services.chat_service.get_build_info")
 @patch("app.services.chat_service.redis_service")
-@patch("app.services.chat_service.telegram_service")
+@patch("app.services.chat_service.tg_service")
 @patch("app.services.chat_service.llm_service")
 async def test_build_info_appended_in_local_dev(
     mock_llm, mock_telegram, mock_redis, mock_get_build_info, mock_update
@@ -364,7 +363,7 @@ async def test_build_info_appended_in_local_dev(
 @pytest.mark.asyncio
 @patch("app.services.chat_service.get_build_info")
 @patch("app.services.chat_service.redis_service")
-@patch("app.services.chat_service.telegram_service")
+@patch("app.services.chat_service.tg_service")
 @patch("app.services.chat_service.llm_service")
 async def test_build_info_not_appended_in_prod(
     mock_llm, mock_telegram, mock_redis, mock_get_build_info, mock_update
@@ -393,7 +392,7 @@ async def test_build_info_not_appended_in_prod(
 
 @pytest.mark.asyncio
 @patch("app.services.chat_service.redis_service")
-@patch("app.services.chat_service.telegram_service")
+@patch("app.services.chat_service.tg_service")
 async def test_handle_model_command_show_current(mock_telegram, mock_redis):
     """ส่ง /model (ไม่มี argument) เพื่อดูโมเดลปัจจุบัน"""
     mock_redis.get_user_model_preference = AsyncMock(return_value="anthropic/claude-3.5-sonnet")
@@ -420,7 +419,7 @@ async def test_handle_model_command_show_current(mock_telegram, mock_redis):
 
 @pytest.mark.asyncio
 @patch("app.services.chat_service.redis_service")
-@patch("app.services.chat_service.telegram_service")
+@patch("app.services.chat_service.tg_service")
 async def test_handle_model_command_show_default_from_settings(mock_telegram, mock_redis, monkeypatch):
     """ส่ง /model (ไม่มี pref) เพื่อดูโมเดลปัจจุบัน โดยต้องดึงค่า default จาก settings จริงๆ"""
     # Setup: ไม่มีการตั้งค่าส่วนตัว
@@ -452,7 +451,7 @@ async def test_handle_model_command_show_default_from_settings(mock_telegram, mo
 
 @pytest.mark.asyncio
 @patch("app.services.chat_service.redis_service")
-@patch("app.services.chat_service.telegram_service")
+@patch("app.services.chat_service.tg_service")
 async def test_handle_model_command_update_success(mock_telegram, mock_redis):
     """ส่ง /model <alias> เพื่อเปลี่ยนโมเดล"""
     mock_redis.set_user_model_preference = AsyncMock()
@@ -480,7 +479,7 @@ async def test_handle_model_command_update_success(mock_telegram, mock_redis):
 
 @pytest.mark.asyncio
 @patch("app.services.chat_service.redis_service")
-@patch("app.services.chat_service.telegram_service")
+@patch("app.services.chat_service.tg_service")
 async def test_handle_model_command_invalid_alias(mock_telegram, mock_redis):
     """ส่ง /model <alias> ที่ไม่มีอยู่จริง"""
     mock_redis.set_user_model_preference = AsyncMock()
@@ -508,7 +507,7 @@ async def test_handle_model_command_invalid_alias(mock_telegram, mock_redis):
 
 @pytest.mark.asyncio
 @patch("app.services.chat_service.redis_service")
-@patch("app.services.chat_service.telegram_service")
+@patch("app.services.chat_service.tg_service")
 @patch("app.services.chat_service.llm_service")
 async def test_standard_message_uses_preferred_model(mock_llm, mock_telegram, mock_redis, mock_update):
     """ข้อความปกติควรใช้โมเดลที่ผู้ใช้เลือกไว้ใน Redis"""
@@ -531,7 +530,7 @@ async def test_standard_message_uses_preferred_model(mock_llm, mock_telegram, mo
 
 @pytest.mark.asyncio
 @patch("app.services.chat_service.redis_service")
-@patch("app.services.chat_service.telegram_service")
+@patch("app.services.chat_service.tg_service")
 async def test_project_switch_with_saved_context_shows_summary(mock_telegram, mock_redis):
     """ทดสอบ /project select <name> เมื่อมี AgentState บันทึกไว้ ต้องแสดง Welcome back summary"""
     from app.models.agent_state import AgentState
@@ -582,7 +581,7 @@ async def test_project_switch_with_saved_context_shows_summary(mock_telegram, mo
 
 @pytest.mark.asyncio
 @patch("app.services.chat_service.redis_service")
-@patch("app.services.chat_service.telegram_service")
+@patch("app.services.chat_service.tg_service")
 async def test_handle_note_command_saves_agent_state(mock_telegram, mock_redis):
     """ทดสอบ /note <task> ต้องบันทึก AgentState ลง Redis"""
     from app.models.agent_state import AgentState
@@ -629,3 +628,60 @@ async def test_handle_note_command_saves_agent_state(mock_telegram, mock_redis):
     sent_message = mock_telegram.send_message.call_args[0][1]
     assert "✅ Note saved for project" in sent_message
     assert f"`{project_name}`" in sent_message
+
+
+# === Proactive Messaging Support (Issue #30) ===
+
+@pytest.mark.asyncio
+@patch("app.services.chat_service.redis_service.set_user_chat_id_mapping", new_callable=AsyncMock)
+@patch("app.services.chat_service.redis_service.get_current_project", new_callable=AsyncMock)
+@patch("app.services.chat_service.redis_service.get_chat_history", new_callable=AsyncMock)
+@patch("a
... (Diff truncated for size) ...


PR TEMPLATE:


INSTRUCTIONS:
1. Generate a comprehensive PR description in Markdown format.
2. If a template is provided, fill it out intelligently.
3. If no template, use a standard structure: Summary, Changes, Impact.
4. Focus on 'Why' and 'What'.
5. Do not include 'Here is the PR description' preamble. Just the body.
6. IMPORTANT: Always use the exact FULL URL for closing issues. You must write `Closes https://github.com/oatrice/Akasa/issues/30`. Do NOT use short syntax (e.g., #123) and do not invent an owner/repo.
