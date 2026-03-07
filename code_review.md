# Luma Code Review Report

**Date:** 2026-03-07 20:58:11
**Files Reviewed:** ['tests/services/test_telegram_service.py', 'app/utils/__init__.py', 'app/utils/markdown_utils.py', 'tests/utils/test_markdown_utils.py', 'app/services/telegram_service.py']

## 📝 Reviewer Feedback

The local import `from app.utils.markdown_utils import escape_markdown_v2` in `app/services/telegram_service.py` should be moved to the top of the file to follow PEP8 standards.

```python
# In app/services/telegram_service.py

# Fix: Move import to the top of the file
import httpx
from app.config import settings
from app.utils.markdown_utils import escape_markdown_v2

async def send_message(chat_id: int, text: str) -> None:
    """
    Sends a text message to a specific chat using the Telegram Bot API.
    """
    api_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    # from app.utils.markdown_utils import escape_markdown_v2 # Remove this line
    
    payload = {
        "chat_id": chat_id,
        "text": escape_markdown_v2(text),
        "parse_mode": "MarkdownV2"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            api_url,
            json=payload,
            timeout=10.0
        )
        response.raise_for_status()

```

## 🧪 Test Suggestions

*   **Nested or Unbalanced Backticks:** A test with a string like `Use `docker run --env 'VAR=`cat .env`'` to run.` This is critical because the current non-greedy regex ` `.*?` ` will incorrectly match only up to the second backtick (`` `docker run --env 'VAR=` ``), corrupting the rest of the string. This tests the robustness of the parsing logic against realistic, complex shell commands.
*   **Special Characters Adjacent to Code Blocks:** A test case with a string where reserved Markdown characters are immediately next to a code block, such as `The result is `5-3=2`!`. This ensures the splitting logic correctly isolates the code block and escapes the surrounding special characters (`!` becomes `\\!`) without any off-by-one errors at the boundary.
*   **Unclosed Multi-line Code Blocks:** A test with a string that starts a multi-line code block but never closes it, like `Here is the code: ```python \n print('hello')`. This is a critical edge case to ensure the parser doesn't hang or fail. It should default to treating the entire string as plain text and escape the ` ``` ` sequence to prevent formatting errors.

