# SBE: Markdown Code Formatting

> 📅 Created: 2026-03-07
> 🔗 Issue: [#7](https://github.com/oatrice/Akasa/issues/7)

---

## Feature: Markdown Code Block Formatting

This feature enables rich formatting for code snippets in messages sent by the bot. By setting Telegram's `parse_mode` to `MarkdownV2`, the system will render code blocks with proper styling and syntax highlighting. It must also correctly escape special Markdown characters in plain text to prevent formatting errors and API rejections.

### Scenario: Message with Code Block (Happy Path)

**Given** the LLM generates a response containing a valid Markdown code block
**When** the system sends the message to the user
**Then** the `parse_mode` sent to the Telegram API must be `MarkdownV2` and the user must see a properly formatted code block

#### Examples

| llm_response | expected_api_payload |
|---|---|
| "Here is the code:\n```python\nprint('Hello')\n```" | `{"parse_mode": "MarkdownV2", "text": "Here is the code:\n```python\nprint('Hello')\n```"}` |
| "```javascript\nconst x = 1;\n```" | `{"parse_mode": "MarkdownV2", "text": "```javascript\nconst x = 1;\n```"}` |
| "A one-liner: `x = 1+1`" | `{"parse_mode": "MarkdownV2", "text": "A one-liner: `x = 1+1`"}` |

### Scenario: Edge Case - Text with Special Characters

**Given** the LLM generates a response containing special Markdown characters outside of a code block
**When** the system prepares the message for Telegram
**Then** all special characters (`.`, `-`, `!`, `(`, `)`) in the plain text portion must be escaped with a backslash (`\`)

#### Examples

| llm_response | expected_escaped_text_sent_to_api |
|---|---|
| "The IP is 127.0.0.1. It's a localhost address." | "The IP is 127\\.0\\.0\\.1\\. It's a localhost address\\." |
| "This is important! (really important)" | "This is important\\! \\(really important\\)" |
| "Use the command `ls -l`." | "Use the command `ls -l`\\." |
| "Here is a list:\n- Item 1\n- Item 2" | "Here is a list:\n\\- Item 1\n\\- Item 2" |

### Scenario: Edge Case - Special Characters inside a Code Block

**Given** the LLM generates a response with a code block containing special Markdown characters
**When** the system prepares the message
**Then** the characters *inside* the code fences (```) must NOT be escaped, while characters outside must be.

#### Examples

| llm_response | expected_escaped_text_sent_to_api |
|---|---|
| "The result is `[1, 2, 3]`. \n```python\nmy_list = [1, 2, 3]\nprint(my_list[0]) # prints 1\n```" | "The result is `[1, 2, 3]`\\. \n```python\nmy_list = [1, 2, 3]\nprint(my_list[0]) # prints 1\n```" |
| "Run this: ```sh\necho 'Hello-World!'\n```. It works." | "Run this: ```sh\necho 'Hello-World!'\n```\\. It works\\." |
| "This is an object: `{\"key\": \"value\"}`." | "This is an object: `{\"key\": \"value\"}`\\." |