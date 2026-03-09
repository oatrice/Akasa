# Luma Code Review Report

**Date:** 2026-03-09 08:52:49
**Files Reviewed:** ['tests/services/test_telegram_service.py', 'docs/features/10_issue-38_feature-project-specific-memory-context-restoration/sbe.md', 'docs/features/10_issue-38_feature-project-specific-memory-context-restoration/ai_brain/analysis_issue50.md', 'tests/services/test_chat_service.py', 'docs/features/11_issue-30_service-support-outbound-messaging-in-telegramservice/spec.md', 'VERSION', 'app/services/redis_service.py', 'CHANGELOG.md', 'docs/ROADMAP.md', 'tests/services/test_redis_service.py']

## 📝 Reviewer Feedback

In `tests/services/test_redis_service.py`, the test `test_set_and_get_user_chat_id_mapping` uses string values for `user_id` and `chat_id`, which contradicts the `int` type hints in the function signatures it's testing in `app/services/redis_service.py`.

**The Problem:**

In `tests/services/test_redis_service.py`:
```python
@pytest.mark.asyncio
async def test_set_and_get_user_chat_id_mapping(patch_redis):
    # ...
    user_id = "user-123"  # <-- Incorrect type (should be int)
    chat_id = "chat-456"  # <-- Incorrect type (should be int)
    # ...
    await set_user_chat_id_mapping(user_id, chat_id)
    # ...
    retrieved_chat_id = await get_chat_id_for_user(user_id)
    assert retrieved_chat_id == chat_id
```

The corresponding function signatures in `app/services/redis_service.py` are:
```python
async def set_user_chat_id_mapping(user_id: int, chat_id: int):
    # ...

async def get_chat_id_for_user(user_id: int) -> Optional[str]:
    # ...
```

While this may pass due to Python's dynamic typing, it's incorrect from a static analysis and contract perspective. The test should use data that conforms to the specified types.

**The Fix:**

Update the test in `tests/services/test_redis_service.py` to use integer values for IDs and ensure the final assertion correctly compares the retrieved string value.

```python
# In tests/services/test_redis_service.py

@pytest.mark.asyncio
async def test_set_and_get_user_chat_id_mapping(patch_redis):
    """ทบทวนการเก็บและดึง mapping ระหว่าง user_id และ chat_id"""
    from app.services.redis_service import set_user_chat_id_mapping, get_chat_id_for_user

    user_id = 12345  # CORRECTED: Use int
    chat_id = 67890  # CORRECTED: Use int

    # 1. ทดสอบ get user ที่ยังไม่มี -> ควรได้ None
    retrieved_chat_id = await get_chat_id_for_user(user_id)
    assert retrieved_chat_id is None

    # 2. ตั้งค่า mapping
    await set_user_chat_id_mapping(user_id, chat_id)

    # 3. ดึงค่ากลับมา -> ต้องตรงกับที่ตั้งไว้ (และเป็น string)
    retrieved_chat_id = await get_chat_id_for_user(user_id)
    assert retrieved_chat_id == str(chat_id)  # CORRECTED: Assert against string value

    # 4. Key ต้องมี TTL
    ttl = await patch_redis.ttl(f"user_chat_id:{user_id}")
    assert ttl > 0
```

## 🧪 Test Suggestions

นี่คือคู่มือการตรวจสอบด้วยตนเองสำหรับฟีเจอร์การส่งข้อความเชิงรุก (Proactive Messaging)

เนื่องจากฟีเจอร์นี้เป็นความสามารถของฝั่ง Backend และยังไม่มีส่วนที่ผู้ใช้เรียกได้โดยตรง เราจึงต้องสร้าง Endpoint ชั่วคราวขึ้นมาเพื่อทดสอบ

### ส่วนที่ 1: การเตรียมการ - สร้าง Endpoint สำหรับทดสอบ

1.  เปิดไฟล์ `app/main.py`
2.  เพิ่มโค้ดด้านล่างนี้เข้าไปเพื่อสร้าง Endpoint ชั่วคราวสำหรับใช้ทดสอบฟีเจอร์:

    ```python
    # === TEMPORARY: Add this at the end of app/main.py for testing Issue #30 ===
    import logging
    from app.services.telegram_service import tg_service
    from app.exceptions import UserChatIdNotFoundException, BotBlockedException

    @app.get("/test_proactive/{user_id}")
    async def test_proactive_messaging(user_id: int):
        """Endpoint ชั่วคราวสำหรับทดสอบการส่งข้อความหาผู้ใช้โดยตรง"""
        logger = logging.getLogger(__name__)
        logger.info(f"--- [MANUAL TEST] Testing proactive message for user_id: {user_id} ---")
        try:
            success = await tg_service.send_proactive_message(
                user_id=user_id,
                text=f"This is a proactive test message for user_id: {user_id}"
            )
            if success:
                return {"status": "success", "message": "Proactive message sent successfully."}
            else:
                # This case should ideally not happen if exceptions are raised correctly
                return {"status": "failed", "reason": "Unknown failure in service."}
        except UserChatIdNotFoundException:
            logger.warning(f"--- [MANUAL TEST] FAILED: User {user_id} not found. ---")
            return {"status": "failed", "reason": "User not found in Redis."}
        except BotBlockedException:
            logger.warning(f"--- [MANUAL TEST] FAILED: Bot was blocked by user {user_id}. ---")
            return {"status": "failed", "reason": "Bot blocked by user."}
        except Exception as e:
            logger.error(f"--- [MANUAL TEST] FAILED: An unexpected error occurred: {e} ---")
            return {"status": "failed", "reason": str(e)}

    # =========================================================================
    ```

3.  **หา User ID ของคุณ**: ไปที่ Telegram แล้วคุยกับบอท `@userinfobot` เพื่อให้ได้ **Telegram User ID** ของคุณ (ซึ่งเป็นตัวเลข)

### ส่วนที่ 2: ขั้นตอนการตรวจสอบ

- **ขั้นตอนที่ 1 (ลงทะเบียน ID)**: ส่งข้อความใดๆ ไปหา Akasa Bot ของคุณใน Telegram ก่อน 1 ครั้ง การทำเช่นนี้จะทำให้ระบบบันทึก `user_id` กับ `chat_id` ของคุณลงใน Redis

- **ขั้นตอนที่ 2 (ทดสอบ Happy Path)**: เปิด Terminal แล้วรันคำสั่ง `curl` โดยแทนที่ `{YOUR_USER_ID}` ด้วย User ID ที่คุณได้มาจาก `@userinfobot`
  ```bash
  curl http://localhost:8000/test_proactive/{YOUR_USER_ID}
  ```
- **ผลลัพธ์ที่คาดหวัง**: คุณควรจะได้รับข้อความ "This is a proactive test message for user_id: ..." ในแอป Telegram ของคุณทันที

---

- **ขั้นตอนที่ 3 (ทดสอบกรณีไม่พบผู้ใช้)**: รันคำสั่ง `curl` อีกครั้ง แต่ใช้ User ID ปลอมที่ไม่มีอยู่จริง
  ```bash
  curl http://localhost:8000/test_proactive/12345
  ```
- **ผลลัพธ์ที่คาดหวัง**: คุณต้อง **ไม่** ได้รับข้อความใดๆ ใน Telegram และใน Log ของแอปพลิเคชันควรจะแสดงข้อความเตือนว่า "User 12345 not found" หรือ "Chat ID not found"

---

- **ขั้นตอนที่ 4 (ทดสอบกรณีบอทถูกบล็อก)**:
    1.  ในแอป Telegram ให้ไปที่โปรไฟล์ของ Akasa Bot ของคุณแล้วกด "Block user"
    2.  รันคำสั่ง `curl` ใน **ขั้นตอนที่ 2** ซ้ำอีกครั้ง (โดยใช้ User ID จริงของคุณ)
- **ผลลัพธ์ที่คาดหวัง**: คุณต้อง **ไม่** ได้รับข้อความใดๆ และใน Log ของแอปพลิเคชันควรจะแสดงข้อความเตือนว่า "Bot was blocked by user ..."
- **อย่าลืม**: Unblock บอทของคุณหลังจากทดสอบเสร็จ

### ส่วนที่ 3: การลบโค้ดทดสอบ

เมื่อตรวจสอบเสร็จสิ้นแล้ว ให้ลบโค้ดของ Endpoint ชั่วคราวที่เพิ่มเข้าไปใน `app/main.py` ออกทั้งหมด

