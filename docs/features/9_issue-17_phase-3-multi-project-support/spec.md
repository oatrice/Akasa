# Specification

| Feature Name | Multi-Project Context Switching in Chat |
|--------------|-----------------------------------------|
| **ID** | #17 |
| **Description** | Allow users to switch their active project context within a single chat interface using a command. |
| **Status** | `📝 Spec in Progress` |

---

## 1. Goal (Why)

As a developer working on multiple software projects, I want to command the AI assistant to switch its focus between my different projects directly within our conversation. This will allow me to seamlessly manage tasks, ask questions, and run operations for any of my projects without having to leave the chat or use different channels, making my workflow faster and less prone to error.

## 2. User Journey (How)

1.  The user starts a conversation with the assistant. By default, the context is set to their primary or most recently used project (e.g., `luma-project`).
2.  The user needs to perform a task on a different project, `akasa-project`.
3.  The user types the command `/project akasa-project` and sends it.
4.  The assistant confirms that the context has been switched with a message: "Switched to project 'akasa-project'."
5.  The user now sends a command like `/list-open-issues`.
6.  The assistant executes this command specifically for `akasa-project` and shows the relevant results.
7.  Later, the user wants to switch back. They type `/project luma-project`.
8.  The assistant confirms the switch, and the context is now back to the original project.

## 3. Specification by Example (SBE)

### Scenario 1: Successful Project Switch

- **GIVEN** a user is authorized to access projects `luma` and `akasa`.
- **AND** the current active project is `luma`.
- **WHEN** the user sends the command `/project akasa`.
- **THEN** the system sets the active project context to `akasa`.
- **AND** the system responds with a confirmation message.

**Examples:**

| Input Command | Current Context (Before) | System Response | New Context (After) |
|---|---|---|---|
| `/project akasa` | `luma` | "Switched to project 'akasa'." | `akasa` |

### Scenario 2: Attempting to Switch to a Non-existent or Unauthorized Project

- **GIVEN** a user is in a valid project context.
- **WHEN** the user tries to switch to a project that either doesn't exist or they are not authorized to access.
- **THEN** the system's active project context MUST NOT change.
- **AND** the system responds with a generic error message.

**Examples:**

| Input Command | Current Context (Before) | System Response | New Context (After) |
|---|---|---|---|
| `/project unknown-project` | `luma` | "Error: Project 'unknown-project' not found or you do not have permission to access it." | `luma` |
| `/project secret-project` | `luma` | "Error: Project 'secret-project' not found or you do not have permission to access it." | `luma` |

### Scenario 3: Command with Missing Project Name

- **GIVEN** a user is in a valid project context.
- **WHEN** the user sends the `/project` command without specifying a project name.
- **THEN** the system's active project context MUST NOT change.
- **AND** the system responds with a helpful error message.

**Examples:**

| Input Command | Current Context (Before) | System Response | New Context (After) |
|---|---|---|---|
| `/project` | `luma` | "Error: Please specify a project name. Usage: /project <project_name>" | `luma` |
| `/project ` | `luma` | "Error: Please specify a project name. Usage: /project <project_name>" | `luma` |


---

## 4. Out of Scope

-   This feature only covers switching projects via a text command. A graphical UI menu for switching is not included in this phase.
-   The creation, deletion, or configuration of projects. This specification assumes projects are pre-configured in the system.
-   Displaying a list of available projects (e.g., via `/project --list`). This could be a future enhancement.
-   Running a single command against a different project without permanently switching the context (e.g., `/run --project=akasa "list issues"`).

## 5. Open Questions

1.  How will the system determine the "default" or initial project context when a user starts a new conversation? Will it be the most recently used, or a pre-defined primary project?
2.  Should project names be case-sensitive? (Recommendation: No, for better UX).

[SYSTEM] Gemini CLI failed to process the request. The prompt has been saved to: /Users/oatrice/Software-projects/Luma/docs/ai_brain/luma_failed_prompt_1772959298.md. Please use an external AI to process it.