# Implementation Plan: GitHub Function Calling for ChatService

> **Refers to**: [Spec Link](./spec.md)
> **Status**: Draft

## 1. Architecture & Design
This feature will be implemented by enhancing the `ChatService` to support LLM function calling (tool usage). `ChatService` will act as the orchestrator between the LLM and the `GithubService`.

1.  When a user message is received, `ChatService` will provide the LLM with a list of available GitHub "tools" alongside the user's prompt.
2.  If the LLM determines a tool should be used, it will respond with a structured "tool call" request.
3.  `ChatService` will parse this request, identify the target function (e.g., `create_issue`), and invoke the corresponding method on the `GithubService`.
4.  The result from `GithubService` is then sent back to the LLM as a "tool response".
5.  The LLM generates a final, user-friendly natural language response, which is then sent back to the user.

### Component View
- **Modified Components**:
    - `app/services/chat_service.py`: Will be updated to manage the tool definitions, handle tool calls from the LLM, and orchestrate the interaction with `GithubService`.
- **New Components**:
    - None.
- **Dependencies**:
    - `ChatService` will now explicitly call methods on `GithubService`. We will ensure `GithubService` is properly injected into `ChatService` upon initialization.

### Data Model Changes
No database schema changes are required. The primary new data structures will be the in-code definitions of the tools provided to the LLM.

```python
# In app/services/chat_service.py
# Example structure for defining tools for the LLM

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_github_issue",
            "description": "Creates a new issue in a specified GitHub repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "owner": {"type": "string", "description": "The owner of the repository."},
                    "repo": {"type": "string", "description": "The name of the repository."},
                    "title": {"type": "string", "description": "The title of the issue."},
                    "body": {"type": "string", "description": "The body content of the issue."},
                },
                "required": ["owner", "repo", "title", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_github_open_prs",
            "description": "Lists all open pull requests for a specified GitHub repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "owner": {"type": "string", "description": "The owner of the repository."},
                    "repo": {"type": "string", "description": "The name of the repository."},
                },
                "required": ["owner", "repo"],
            },
        },
    },
]
```

---

## 2. Step-by-Step Implementation

### Step 1: Define Tool Specifications and Integrate into ChatService
- **Goal**: Make the `ChatService` aware of the GitHub tools and pass them to the LLM.
- **Code**:
    1.  **`app/services/chat_service.py`**:
        -   Create a new module-level constant or a private method `_get_tools()` that returns the list of tool definitions as shown in the Data Model section.
        -   Modify the primary chat method (e.g., `generate_response`) to include the `tools` parameter in its call to the `llm_service`.
- **Tests**:
    1.  **`tests/services/test_chat_service.py`**:
        -   Create a new test file if it doesn't exist.
        -   Write a test `test_generate_response_passes_tools_to_llm`.
        -   This test will mock the `llm_service`.
        -   It will call the chat method and assert that the mocked `llm_service` was called with a `tools` argument containing the correct GitHub tool definitions.

### Step 2: Implement Tool Call Handling and Execution Logic
- **Goal**: Enable `ChatService` to process a tool call from the LLM, execute the corresponding `GithubService` method, and complete the conversation loop.
- **Code**:
    1.  **`app/services/chat_service.py`**:
        -   In the chat method, add logic to inspect the LLM's response. If a tool call is present:
            -   Create a new private method `_execute_tool_call(tool_call)`.
            -   Inside this new method, use a simple dispatcher (e.g., `if/elif` on `tool_call.function.name`) to map the function name to the correct `GithubService` method.
            -   Parse the arguments from `tool_call.function.arguments`.
            -   Call the appropriate method on the `github_service` instance (e.g., `self.github_service.create_issue(**args)`).
            -   Format the return value from the `github_service` into a "tool response" structure.
            -   Make a second call to the `llm_service`, providing the original history plus the new tool response to get the final user-facing text.
- **Tests**:
    1.  **`tests/services/test_chat_service.py`**:
        -   **Test Case 1: Create Issue Flow**
            -   Write a test `test_chat_handles_create_issue_tool_call`.
            -   Mock `llm_service` to first return a `create_issue` tool call, and then a final user message.
            -   Mock `github_service.create_issue` to return a sample success message (e.g., an issue URL).
            -   Assert that `github_service.create_issue` is called with the correct arguments.
            -   Assert that the final response returned by the `ChatService` matches the expected user-facing message from the second LLM call.
        -   **Test Case 2: List PRs Flow**
            -   Write a test `test_chat_handles_list_prs_tool_call`.
            -   Similar to the above, but mock the `list_open_prs` tool call and `github_service.list_open_prs` method.
            -   Assert the `github_service` method is called correctly and the final formatted list is returned.

---

## 3. Verification Plan
*How will we verify success?*

### Automated Tests
- [ ] **Unit Tests**: `tests/services/test_chat_service.py`
    -   [ ] Verify tools are passed to the LLM on every call.
    -   [ ] Verify the `create_issue` tool call correctly invokes `GithubService.create_issue` and returns a final message.
    -   [ ] Verify the `list_open_prs` tool call correctly invokes `GithubService.list_open_prs` and returns a final message.
    -   [ ] Verify graceful failure if a tool call specifies a function that doesn't exist.
- [ ] **Integration Tests**: No new integration tests are required for this plan, as the core implementation of `GithubService` is out of scope. Unit tests with mocks are sufficient.

### Manual Verification
- [ ] **Setup**:
    -   [ ] Run the Akasa application locally.
    -   [ ] Ensure `GITHUB_TOKEN`, `TELEGRAM_BOT_TOKEN`, and other necessary environment variables are set correctly.
- [ ] **Scenario 1: Create Issue**
    -   [ ] Send a message via a chat client: `ช่วยสร้าง issue ในโปรเจกต์ oatrice/Akasa หน่อย หัวข้อ 'Manual Test Issue' เนื้อหาคือ 'This is a test from the manual verification plan.'`
    -   [ ] **Expected Result**: The bot replies with a confirmation message containing a link to the newly created issue.
    -   [ ] Verify the issue exists on GitHub with the correct title and body.
- [ ] **Scenario 2: List Pull Requests**
    -   [ ] Send a message via a chat client: `ขอดู PR ทั้งหมดของโปรเจกต์ oatrice/Akasa หน่อย`
    -   [ ] **Expected Result**: The bot replies with a formatted list of all open pull requests for that repository, including title, number, and author.