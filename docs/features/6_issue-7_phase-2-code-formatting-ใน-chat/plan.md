# Implementation Plan: [Phase 2] Code Formatting in Chat

> **Refers to**: [Spec Link](./spec.md)
> **Status**: Ready for Dev

## 1. Architecture & Design
*High-level technical approach.*

The core of this implementation is to intelligently format the bot's reply text to be compliant with Telegram's `MarkdownV2` specification. This involves two key parts:
1.  **Escaping Special Characters**: All reserved MarkdownV2 characters in the plain text portion of a message must be escaped with a preceding backslash (`\`) to be rendered literally.
2.  **Preserving Code Blocks**: The content within single-line (`` ` ``) and multi-line (``````) code blocks must *not* be escaped, as this would corrupt the code.

To achieve this, we will create a utility function, `escape_markdown_v2`, that parses the input string. It will iterate through the string, identify code blocks, and apply the escaping logic only to the text segments outside of these blocks. This function will be integrated into the `telegram_service` before the final message is sent to the Telegram API, along with the `parse_mode="MarkdownV2"` parameter.

### Component View
- **Modified Components**:
    - `app/services/telegram_service.py`: This is the primary file to be modified. It will house the new escaping logic and be updated to send the `parse_mode` parameter.
- **New Components**:
    - `app/utils.py`: A new file to potentially store the `escape_markdown_v2` helper function for better separation of concerns. (Decision: To keep it simple, we will implement it directly in `telegram_service.py` for now).
- **Dependencies**:
    - No new external dependencies are required.

### Data Model Changes
```python
# No data model changes are required for this feature.
```

---

## 2. Step-by-Step Implementation

### Step 1: Create the MarkdownV2 Escaping Logic

- **Code**:
    1.  **Create a helper function** within `app/services/telegram_service.py`. This function needs to parse the text and escape only the parts outside of code blocks.
        ```python
        # In app/services/telegram_service.py
        import re

        def escape_markdown_v2(text: str) -> str:
            """
            Escapes text for Telegram's MarkdownV2 parse mode, ignoring code blocks.
            """
            # Characters to escape
            escape_chars = r'([!#()*+\-.[\]^_`{|}~>])'
            
            # Use regex to find all code blocks (single and multi-line)
            code_blocks = list(re.finditer(r'`[^`]*`|```[^`]*```', text))
            
            if not code_blocks:
                return re.sub(escape_chars, r'\\\1', text)

            escaped_parts = []
            last_end = 0
            for block in code_blocks:
                start, end = block.span()
                # Escape the part before the code block
                escaped_parts.append(re.sub(escape_chars, r'\\\1', text[last_end:start]))
                # Add the code block as is (unescaped)
                escaped_parts.append(text[start:end])
                last_end = end
            
            # Escape the final part of the string after the last code block
            escaped_parts.append(re.sub(escape_chars, r'\\\1', text[last_end:]))
            
            return "".join(escaped_parts)
        ```
- **Verification**:
    - Create a separate test file `tests/services/test_telegram_service_utils.py` (or similar) to unit test the `escape_markdown_v2` function extensively.
    - Test cases must include strings with no special characters, strings with only special characters, strings with only code blocks, and mixed content.

### Step 2: Integrate Escaping into `send_message` Service

- **Code**:
    1.  **Modify `app/services/telegram_service.py`**: Update the `send_message` function to use the new helper and send the `parse_mode` parameter.
        ```python
        # In app/services/telegram_service.py
        ...
        async def send_message(chat_id: int, text: str) -> None:
            """
            Sends a text message to a specific chat using the Telegram Bot API.
            The text is automatically formatted for MarkdownV2.
            """
            api_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
            
            escaped_text = escape_markdown_v2(text)

            payload = {
                "chat_id": chat_id,
                "text": escaped_text,
                "parse_mode": "MarkdownV2"
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    api_url,
                    json=payload,
                    timeout=10.0
                )
                # Add logging for failed requests for easier debugging
                if response.status_code != 200:
                    logging.error(f"Telegram API Error: {response.status_code} - {response.text}")
                response.raise_for_status()
        ```
- **Verification**:
    - The existing unit tests for `send_message` will need to be updated.
    - `respx` mocks should now check that the `json` payload sent to the Telegram API includes `"parse_mode": "MarkdownV2"` and that the `text` field is correctly escaped.

### Step 3: Update Unit Tests

- **Code**:
    1.  **Create `tests/services/test_telegram_service_utils.py`** (if separating):
        - Add tests to verify correct escaping for various inputs.
            - `assert escape_markdown_v2("Hello. World!") == "Hello\\. World\\!"`
            - `assert escape_markdown_v2("Code: `print()`.") == "Code: `print()`\\."`
            - `assert escape_markdown_v2("Code: ```py\nprint(1-1)\n```") == "Code: ```py\nprint(1-1)\n```"`
    2.  **Modify `tests/services/test_telegram_service.py`**:
        - Update the mock API calls to check for the new payload structure.
- **Verification**:
    - Run `pytest`. All new and updated tests must pass.

---

## 3. Verification Plan
*How will we verify success?*

### Automated Tests
- [ ] **Unit Tests**: All tests for `escape_markdown_v2` must pass, covering all special characters and combinations with code blocks. The `send_message` tests must be updated to reflect the new API payload.

### Manual Verification
- [ ] **Test with Code**: Ask the bot a question that will generate a Python code block. Verify it renders correctly in the Telegram chat client.
- [ ] **Test with Special Characters**: Ask the bot a question that will generate a response with special characters (e.g., "What is the IP 127.0.0.1?"). Verify the characters are displayed as text and not interpreted as Markdown.
- [ ] **Test with Mixed Content**: Ask a question that produces a response containing both plain text with special characters *and* a code block. Verify both parts are rendered correctly in the same message.

[SYSTEM] Gemini CLI failed to process the request. The prompt has been saved to: /Users/oatrice/Software-projects/Akasa/docs/features/6_issue-7_phase-2-code-formatting-ใน-chat/ai_brain/luma_failed_prompt_1772885630.md. Please use an external AI to process it.