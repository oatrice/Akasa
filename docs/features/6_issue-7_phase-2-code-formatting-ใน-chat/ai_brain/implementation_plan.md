# Implementation Plan: Code Formatting in Chat

## Proposed Changes

### Utilities
#### [NEW] `app/utils/markdown_utils.py`
- Create a pure function `escape_markdown_v2(text: str) -> str`
- This function will use regular expressions to find all Markdown code blocks (both inline \`...\` and multi-line \`\`\`...\`\`\`)
- It will escape all Telegram MarkdownV2 reserved characters (`_`, `*`, `[`, `]`, `(`, `)`, `~`, `` ` ``, `>`, `#`, `+`, `-`, `=`, `|`, `{`, `}`, `.`, `!`) that appear *outside* of code blocks with a backslash `\`.
- Characters *inside* code blocks are returned as-is.

### Services
#### [MODIFY] `app/services/telegram_service.py`
- Import `escape_markdown_v2` from `app/utils/markdown_utils.py`.
- Apply the escape function to the `text` variable before constructing the API payload.
- Add `parse_mode: "MarkdownV2"` to the payload in `send_message`.

---

## Verification Plan

### Automated Tests
#### [NEW] `tests/utils/test_markdown_utils.py`
- Add comprehensive test cases:
  - Text with no special characters.
  - Text with special characters only.
  - Text with inline code block.
  - Text with multi-line code block.
  - Text with mixed content.
  - Code block containing special characters (must not be escaped).
- Run with: `pytest tests/utils/test_markdown_utils.py -v`

#### [MODIFY] `tests/services/test_telegram_service.py`
- Update expectations in `test_send_message_success` to verify that `parse_mode: "MarkdownV2"` is passed in the JSON payload, and the text is the properly escaped version.
- Run with: `pytest tests/services/test_telegram_service.py -v`
