# SBE: Multi-Project Context Switching

> 📅 Created: 2026-03-08
> 🔗 Issue: https://github.com/oatrice/Akasa/issues/17

---

## Feature: Multi-Project Context Switching via Chat Command

This feature allows a user to switch the active project context within a single chat interface. By using a slash command (`/project <project_name>`), the user can direct all subsequent commands and queries to the specified project without changing chat windows or channels. The system must confirm a successful switch or provide a clear error if the switch cannot be completed, ensuring the user is always aware of the current active context.

### Scenario: Happy Path - Successfully Switching Between Authorized Projects

**Given** the user is authenticated and authorized to access projects `luma-web`, `akasa-api`, and `mobile-ios`.
**And** the current active project is `luma-web`.
**When** the user sends the command `/project` followed by the name of another authorized project.
**Then** the system's active context is updated to the new project.
**And** the system sends a confirmation message `Active project switched to '<new_project_name>'`.

#### Examples

| current_context | input_command | expected_response | final_context |
|---|---|---|---|
| `luma-web` | `/project akasa-api` | `Active project switched to 'akasa-api'` | `akasa-api` |
| `akasa-api` | `/project mobile-ios` | `Active project switched to 'mobile-ios'` | `mobile-ios` |
| `mobile-ios` | `/project luma-web` | `Active project switched to 'luma-web'` | `luma-web` |
| `luma-web` | `/project AKASA-API` | `Active project switched to 'akasa-api'` | `akasa-api` |

### Scenario: Error Handling - Attempting to Switch to an Invalid or Unauthorized Project

**Given** the user's current active project is `luma-web`.
**When** the user sends the command `/project` followed by a project name that is non-existent or they are not authorized to access.
**Then** the system's active context MUST NOT change.
**And** the system sends the error message `Error: Project '<project_name>' not found or access denied`.

#### Examples

| current_context | input_command | expected_error_message | final_context |
|---|---|---|---|
| `luma-web` | `/project unknown-project` | `Error: Project 'unknown-project' not found or access denied` | `luma-web` |
| `luma-web` | `/project secret-ops` | `Error: Project 'secret-ops' not found or access denied` | `luma-web` |
| `luma-web` | `/project _-badly-formatted-name` | `Error: Project '_-badly-formatted-name' not found or access denied` | `luma-web` |
| `luma-web` | `/project luma-web-typo` | `Error: Project 'luma-web-typo' not found or access denied` | `luma-web` |

### Scenario: Edge Cases - Malformed or Incomplete Command

**Given** the user's current active project is `luma-web`.
**When** the user sends an incomplete or malformed `/project` command.
**Then** the system's active context MUST NOT change.
**And** the system sends a helpful error message explaining the correct usage.

#### Examples

| current_context | input_command | expected_error_message | final_context |
|---|---|---|---|
| `luma-web` | `/project` | `Error: Command is incomplete. Usage: /project <project_name>` | `luma-web` |
| `luma-web` | `/project ` | `Error: Command is incomplete. Usage: /project <project_name>` | `luma-web` |
| `luma-web` | `/project luma-web akasa-api` | `Error: Too many arguments. Usage: /project <project_name>` | `luma-web` |
| `luma-web` | `project luma-web` | `Error: Command not recognized. Did you mean '/project'?` | `luma-web` |
| `luma-web` | `/proyect luma-web` | `Error: Command not recognized. Did you mean '/project'?` | `luma-web` |

[SYSTEM] Gemini CLI failed to process the request. The prompt has been saved to: /Users/oatrice/Software-projects/Luma/docs/ai_brain/luma_failed_prompt_1772959322.md. Please use an external AI to process it.