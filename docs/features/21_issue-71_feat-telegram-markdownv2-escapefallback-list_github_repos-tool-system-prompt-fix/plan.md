# Implementation Plan: Telegram MarkdownV2 Robustness & GitHub Repo Listing

> **Refers to**: [Spec Link](./spec.md)
> **Status**: ✅ Completed

## 1. Architecture & Design
*This plan outlines the technical steps to enhance message reliability, add a new repository discovery tool, and broaden the AI's assistance scope.*

### Component View
- **Modified Components**:
    - `app/services/chat_service.py`: Will be updated to include the MarkdownV2 error handling fallback, register the new `list_github_repos` tool, and contain the relaxed system prompt.
    - `app/services/github_service.py`: A new method will be added to list repositories.
- **New Components**:
    - `app/utils/markdown_utils.py`: A new utility module to house the `escape_markdown_v2` function.
- **Dependencies**:
    - Relies on the `gh` CLI being installed and authenticated for the `list_github_repos` feature.

### Data Model Changes
```python
# No changes to Pydantic models or database schemas are required for this feature.
```

---

## 2. Step-by-Step Implementation

### Step 1: Implement `list_github_repos` Tool
- **Docs**: Create a new method in `GitHubService` to interact with the `gh` CLI and a corresponding tool function in `ChatService`.
- **Code**:
    - **`app/services/github_service.py`**:
        - Create a new async method `list_repos(self) -> List[str]`.
        - This method will execute the shell command `gh repo list --json name --limit 100`.
        - It will parse the JSON output and return a list of repository names.
    - **`app/services/chat_service.py`**:
        - Create a new tool function `list_github_repos()` that calls `github_service.list_repos()`.
        - Register this new tool in the `self.tools` list within the `ChatService` constructor.
- **Tests**:
    - **`tests/services/test_github_service.py`**:
        - Add a new test `test_list_repos_success`.
        - Mock the `asyncio.create_subprocess_shell` call to return a sample JSON output from the `gh` command.
        - Verify that `list_repos` correctly parses the JSON and returns the expected list of repository names.
    - **`tests/services/test_chat_service_tools.py`**:
        - Add a test to verify the `list_github_repos` tool is registered and can be called, mocking the underlying `GitHubService` method.

### Step 2: Implement MarkdownV2 Escaping and Fallback
- **Docs**: Create a robust messaging mechanism that attempts to send a MarkdownV2 formatted message and falls back to plain text upon failure.
- **Code**:
    - **`app/utils/markdown_utils.py`**:
        - Create a new file.
        - Implement a function `escape_markdown_v2(text: str) -> str` that escapes all special characters as defined by Telegram's API documentation.
    - **`app/services/telegram_service.py`**:
        - In the `send_message` method, wrap the `self.bot.send_message` call in a `try...except` block.
        - `try` to send the message with `parse_mode=ParseMode.MARKDOWN_V2`.
        - `except BadRequest as e:`: If the error message contains "can't parse entities", log a warning and re-attempt the send with `parse_mode=None`. If the second attempt fails, re-raise the exception.
    - **`app/services/chat_service.py`**:
        - In `_send_response`, before calling the `telegram_service`, apply the `escape_markdown_v2` function to the LLM response.
- **Tests**:
    - **`tests/utils/test_markdown_utils.py`**:
        - Create a new test file.
        - Add test cases to verify that `escape_markdown_v2` correctly escapes various special characters (e.g., `_`, `*`, `[`, `]`, `(`, `)`, `~`, `` ` ``, `>`, `#`, `+`, `-`, `=`, `|`, `{`, `}`, `.`, `!`).
    - **`tests/services/test_telegram_service.py`**:
        - Add a new test `test_send_message_fallback_to_plain_text`.
        - Use `@patch` to mock the `telegram.Bot` instance.
        - Configure the mocked `send_message` to raise a `telegram.error.BadRequest("Can't parse entities")` on the first call (when `parse_mode` is `MARKDOWN_V2`).
        - Verify that the mocked `send_message` is called a second time with `parse_mode=None` and the correct text.

### Step 3: Relax the System Prompt
- **Docs**: Update the system prompt in `ChatService` to allow for a broader range of software engineering topics.
- **Code**:
    - **`app/services/chat_service.py`**:
        - Locate the `SYSTEM_PROMPT` multi-line string variable.
        - Edit the text to remove over-restrictive phrases like "only assist with coding".
        - Replace with wording that explicitly includes topics like "DevOps, CI/CD, and project management methodologies" as part of the software development lifecycle.
- **Tests**:
    - This change does not lend itself well to automated unit tests. Verification will be done manually.

---

## 3. Verification Plan
*How will we verify success?*

### Automated Tests
- [ ] **Unit Tests**:
    - [ ] `tests/utils/test_markdown_utils.py`: Verify correct escaping of all special characters.
    - [ ] `tests/services/test_github_service.py`: Confirm `gh` CLI output is parsed correctly.
    - [ ] `tests/services/test_telegram_service.py`: Ensure the fallback mechanism from MarkdownV2 to plain text is triggered on `BadRequest` errors.
- [ ] **Integration Tests**:
    - [ ] `tests/services/test_chat_service_tools.py`: Ensure `list_github_repos` is correctly registered and callable.

### Manual Verification
- [ ] **Markdown Fallback**:
    - [ ] Send a message containing an unescaped character (e.g., `test.`) and verify it arrives as plain text instead of failing.
    - [ ] Send a message with valid markdown (e.g., `*bold*`) and verify it renders correctly.
- [ ] **Repository Listing**:
    - [ ] Send the message "list my github repos" to the bot.
    - [ ] Verify that the bot responds with a bulleted list of repository names from the linked GitHub account.
- [ ] **System Prompt**:
    - [ ] Ask the bot a question about GitHub Actions: "How do I set up a CI/CD pipeline for a Python project?". Verify it provides a helpful answer.
    - [ ] Ask the bot a non-technical question: "What is the best recipe for lasagna?". Verify it correctly refuses to answer as out of scope.