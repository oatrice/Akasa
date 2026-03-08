# Specification

| Feature Name | Project-Specific Memory & Context Restoration |
|--------------|-----------------------------------------|
| **ID** | #38 |
| **Description** | Enable the assistant to remember and restore the specific working context for each project upon switching. |
| **Status** | `📝 Spec in Progress` |

---

## 1. Goal (Why)

As a developer juggling multiple projects, I want the AI assistant to instantly recall my last working context (like the file I was editing or the bug I was fixing) when I switch back to a project. This allows me to seamlessly pick up right where I left off, eliminating the need to repeat myself and making my workflow much more efficient.

## 2. User Journey (How)

1.  A user has been working on `project-A`. Their last command was `/edit auth.py to fix the login bug`. The system saves a persistent "Agent State" for `project-A`, such as `{ current_task: "Fixing login bug", focus_file: "auth.py" }`.
2.  The user then switches to a different project by typing `/project select project-B` and works there for some time.
3.  Later, the user decides to return to `project-A` by typing `/project select project-A`.
4.  The system retrieves the saved Agent State for `project-A` from its memory (Redis).
5.  The system generates a concise summary from this state.
6.  The assistant sends a "welcome back" message that includes this summary: "✅ Switched to project `project-A`. Welcome back! We were last working on fixing the login bug in `auth.py`."
7.  The user can now immediately issue context-dependent commands like "Show me the file again" or "What was the error message?", and the assistant will understand the context of `auth.py`.

## 3. Specification by Example (SBE)

### Scenario 1: Switching to a Project with a Saved Context

-   **GIVEN** a user has previously worked on `project-luma` and its last saved state is `{'task': 'implementing redis cache', 'file': 'luma_core/state.py'}`.
-   **AND** the user is currently working in a different project.
-   **WHEN** the user sends the command `/project select luma`.
-   **THEN** the system retrieves the saved state for `luma`.
-   **AND** the system responds with a message summarizing that retrieved state.

**Examples:**

| Input Command | Saved State for `luma` | Expected System Response |
| :--- | :--- | :--- |
| `/project select luma` | `{'task': 'Fixing bug in redis_service.py', 'file': 'luma_core/redis_service.py'}` | "✅ Switched to project `luma`. Welcome back! We were last working on: Fixing the bug in `luma_core/redis_service.py`." |
| `/project select luma` | `{'task': 'Refactoring the main loop'}` | "✅ Switched to project `luma`. Welcome back! We were last working on: Refactoring the main loop." |

### Scenario 2: Switching to a Project with No Saved Context

-   **GIVEN** a project (`project-odin`) has no previously saved agent state.
-   **AND** the user is currently working in a different project.
-   **WHEN** the user sends the command `/project select odin`.
-   **THEN** the system attempts to retrieve a state for `odin` and finds none.
-   **AND** the system responds with a standard confirmation message **without** a context summary.

**Examples:**

| Input Command | Saved State for `odin` | Expected System Response |
| :--- | :--- | :--- |
| `/project select odin` | `None` | "✅ Switched to project `odin`." |

### Scenario 3: An Action Updates the Persistent State

-   **GIVEN** the user is in `project-luma` and the current state is empty.
-   **WHEN** the user issues a command that establishes a new context, like `/edit luma_core/actions.py 'add a new function'`.
-   **THEN** the system must execute the action.
-   **AND** the system must update and persist the agent state for `project-luma` to reflect this new context.

**Examples:**

| Input Command | Action Taken | New Saved State for `project-luma` |
| :--- | :--- | :--- |
| `/edit main.py "add cli arguments"` | File edit is performed. | `{'task': 'add cli arguments', 'file': 'main.py'}` |
| `/debug test_llm.py` | Debugging session starts. | `{'task': 'Debugging test_llm.py', 'file': 'test_llm.py'}` |

---

## 4. Out of Scope

-   This feature will not summarize the entire chat history. It only summarizes the structured `AgentState` (the last-known specific task).
-   Automatic context switching based on message content. The switch must be initiated explicitly by the user with the `/project` command.
-   Merging or transferring context between different projects. Each project's memory is completely isolated.

## 5. Open Questions

1.  What specific fields should the `AgentState` object contain? (Initial proposal: `current_task: str`, `focus_file: str`, `last_activity_timestamp: datetime`).
2.  How frequently should the agent state be updated? After every message, or only after specific "state-changing" commands (like `/edit`, `/debug`)? (Recommendation: Update only after specific commands to avoid noise).