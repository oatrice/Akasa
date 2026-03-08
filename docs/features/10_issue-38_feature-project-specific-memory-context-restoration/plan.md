# Implementation Plan: Project-Specific Memory & Context Restoration

> **Refers to**: [Spec Link](./spec.md)
> **Status**: Draft

## 1. Architecture & Design
*High-level technical approach.*

This feature will be implemented by introducing a persistent, structured `AgentState` for each project. This state will be stored as a JSON object in Redis, separate from the chat history.

1.  **State Definition**: A new dataclass, `AgentState`, will be defined in `luma_core/state.py` to standardize the structure of the context we want to remember (e.g., current task, focused file).
2.  **State Persistence**: The `StateManager` will be enhanced with methods to save and load these `AgentState` objects to/from Redis using a new key pattern like `agent_state:{chat_id}:{project_id}`.
3.  **State Update**: Key functions in `luma_core/actions.py` that imply a change in context (e.g., editing a file, starting a debug session) will be modified to construct and persist the `AgentState` object via the `StateManager`.
4.  **State Restoration**: The command handler for `/project select` in `luma_core/gemini_cli.py` will be updated. Upon a successful switch, it will attempt to load the `AgentState` for the target project.
5.  **Context Summarization**: If a state is found, a new `ContextSummarizer` service will be called. This service will use an LLM to generate a concise, human-readable "welcome back" summary from the structured state data, which is then sent to the user. If no state is found, the system will gracefully fall back to the standard confirmation message.

### Component View
-   **Modified Components**:
    -   `luma_core/state_manager.py`: To add CRUD operations for the new `AgentState` object in Redis.
    -   `luma_core/gemini_cli.py`: To orchestrate the context restoration flow upon project switching.
    -   `luma_core/actions.py`: To update the persistent `AgentState` after a context-changing action is performed.
-   **New Components**:
    -   `luma_core/state.py`: Will contain the new `AgentState` dataclass definition.
    -   `luma_core/context_summarizer.py`: A new service to handle the logic of generating a summary from the `AgentState` using an LLM.
    -   `tests/test_context_summarizer.py`, `tests/test_state_restoration.py`: New test files for the new logic.
-   **Dependencies**: No new external dependencies are required.

### Data Model Changes
```python
# In luma_core/state.py
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class AgentState:
    """Represents the last known working context of an agent for a specific project."""
    version: int = 1
    current_task: Optional[str] = None
    focus_file: Optional[str] = None
    last_activity_timestamp: Optional[datetime] = None
```

---

## 2. Step-by-Step Implementation

### Step 1: Define AgentState and Update StateManager
-   **Description**: Create the `AgentState` dataclass and add the necessary methods to `StateManager` to handle its persistence in Redis.
-   **Files**:
    -   `luma_core/state.py`: Create this new file and define the `AgentState` dataclass as specified above.
    -   `luma_core/state_manager.py`: Add `save_agent_state(state: AgentState)` and `load_agent_state() -> Optional[AgentState]` methods. These will serialize/deserialize the `AgentState` object to/from a JSON string stored in a Redis key like `agent_state:<chat_id>:<project_id>`.
-   **Verification**:
    -   Add unit tests to `tests/test_state_manager.py` to verify that an `AgentState` object can be correctly saved to and loaded from the mock Redis. Test the case where a state does not exist (should return `None`).

### Step 2: Implement the Context Summarizer
-   **Description**: Create a service that can take an `AgentState` object and generate a human-readable summary.
-   **Files**:
    -   `luma_core/context_summarizer.py`: Create this file. Implement an `async def generate_welcome_summary(state: AgentState) -> str` function. This function will create a prompt for the LLM, call `llm_service.get_llm_reply`, and return the result.
-   **Verification**:
    -   Create `tests/test_context_summarizer.py`. Write a unit test for `generate_welcome_summary` that mocks the `llm_service` call and asserts that the prompt is constructed correctly based on a sample `AgentState` input.

### Step 3: Integrate State Updates into Actions
-   **Description**: Modify existing "action" functions to update the `AgentState` after they are executed.
-   **Files**:
    -   `luma_core/actions.py`: In functions like `edit_file_action` or `run_shell_command`, after the primary logic is complete, create an instance of `AgentState` with the relevant details (e.g., file path, task description). Then, call the new `state_manager.save_agent_state()` method to persist it.
-   **Verification**:
    -   Modify existing tests for actions in `tests/test_actions.py`. Mock the `state_manager` and verify that `save_agent_state` is called with the correct `AgentState` payload after an action is successfully performed.

### Step 4: Implement the Context Restoration Flow
-   **Description**: Update the `/project select` command handler to trigger the new restoration workflow.
-   **Files**:
    -   `luma_core/gemini_cli.py`: In the logic for `/project select`, after the project context is switched, add the following steps:
        1.  Call `state_manager.load_agent_state()`.
        2.  If a state is returned, call `context_summarizer.generate_welcome_summary(state)`.
        3.  Send the resulting summary back to the user.
        4.  If no state is returned, send the standard "Switched to project..." message.
-   **Verification**:
    -   Create a new integration test file, `tests/test_state_restoration.py`.
    -   This test will simulate the full user journey: switch to project A, perform an action, switch to project B, switch back to project A, and assert that the welcome summary is received. Mock the LLM call to return a predictable summary.

---

## 3. Verification Plan
*How will we verify success?*

### Automated Tests
-   [ ] Unit Tests: `tests/test_state_manager.py` will be updated to cover `AgentState` serialization and deserialization.
-   [ ] Unit Tests: `tests/test_context_summarizer.py` will be created to test the LLM prompt generation for summaries.
-   [ ] Integration Tests: `tests/test_state_restoration.py` will be created to test the end-to-end flow as described in SBE Scenario 1 and 2.

### Manual Verification
-   [ ] **VC1 (No State):** Run the application with a clean Redis. Use `/project select my-project`.
    -   **Expected:** Bot responds with the standard "✅ Switched to project `my-project`." message.
-   [ ] **VC2 (State Creation):** In `my-project`, issue a command that creates context, such as `/edit README.md "add new setup instructions"`.
    -   **Expected:** The command executes successfully.
-   [ ] **VC3 (Context Switch Away):** Switch to another project, e.g., `/project select default`.
    -   **Expected:** Bot confirms the switch to `default`.
-   [ ] **VC4 (Context Restoration):** Switch back to the original project: `/project select my-project`.
    -   **Expected:** Bot responds with a context-aware message, e.g., "✅ Switched to project `my-project`. Welcome back! We were last working on adding new setup instructions to `README.md`."