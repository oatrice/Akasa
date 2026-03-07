# Akasa Code Review Refactoring & Tests

This plan addresses the code review findings specifically for the **Akasa** repository (`code_review.md`). It also converts the suggested manual test procedures into automated unit tests.

## Proposed Changes

### `app/services/chat_service.py`
#### [MODIFY] chat_service.py (file:///Users/oatrice/Software-projects/Akasa/app/services/chat_service.py)
- **Fix Silent Failure**: In `handle_chat_message`, update the `except Exception as e:` block catching the LLM call to also notify the user: `await telegram_service.send_message(chat_id, "ขออภัย เกิดข้อผิดพลาดที่ไม่คาดคิด โปรดลองอีกครั้งในภายหลัง")`.
- **PEP8 Global Imports**: Move `from app.config import settings` from inside `get_build_info` and `handle_chat_message` to the top level of the file.

### `app/services/llm_service.py`
#### [MODIFY] llm_service.py (file:///Users/oatrice/Software-projects/Akasa/app/services/llm_service.py)
- **Generic API Config**: Change `settings.OPENROUTER_API_KEY` to `settings.LLM_API_KEY` for consistency with configuration intent.
- **Dynamic Configuration URL**: Construct the API endpoint conditionally using `settings.LLM_BASE_URL` instead of hardcoding `https://openrouter.ai/api/v1/...`.
- **PEP8 Global Imports**: Move `import logging` and `logger = logging.getLogger(__name__)` from inside `get_llm_reply` to the top level.

### `tests/services/test_chat_service.py`
#### [MODIFY] test_chat_service.py (file:///Users/oatrice/Software-projects/Akasa/tests/services/test_chat_service.py)
To fulfill the "Test Suggestions", we will add the following automated unit tests in true TDD style (Red -> Green -> Refactor):
1. **Test `handle_chat_message` unexpected LLM error fallback**: Ensure the generic error message is sent to Telegram and the silent failure is resolved.
2. **Test Redis History excludes System Prompts**: Assert that the calls to `redis_service.add_message_to_history` inside `handle_chat_message` only add "user" and "assistant" roles, and perfectly omit the "system" prompt. (Replacing the manual Step 4 in the review).

## Verification Plan

### Automated Tests
Run the updated `pytest` test suite.
```bash
pytest tests/services/test_chat_service.py -v
```
To adhere to the TDD cycle, I will write the tests first (RED phase), ensure they fail, implement the changes (GREEN phase), and run again.

### Manual Verification
As the final fallback check, run:
```bash
uvicorn app.main:app --reload
```
And manually message the bot in Telegram to verify it responds normally and declines off-topic requests.
