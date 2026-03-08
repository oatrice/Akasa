# SBE: Project-Specific Memory & Context Restoration

> 📅 Created: 2026-03-08
> 🔗 Issue: https://github.com/oatrice/Akasa/issues/38

---

## Feature: Project-Specific Memory & Context Restoration

This feature enables the assistant to remember and restore the specific working context of each project. When a user switches back to a project, the assistant will greet them with a concise summary of their last activity (e.g., the file they were editing or the task they were performing). This provides a seamless workflow, allowing the user to pick up exactly where they left off without needing to manually re-establish context.

### Scenario: Happy Path - Switching to a Project with Saved Context

**Given** the user has previously worked on a project and a specific "Agent State" was saved for it.
**And** the user is currently active in a different project.
**When** the user sends the command `/project select` with the name of the previous project.
**Then** the system retrieves the saved Agent State for that project.
**And** the system responds with a "welcome back" message that summarizes the retrieved state.

#### Examples

| current_project | input_command | saved_state_for_target | expected_response |
|---|---|---|---|
| `akasa-api` | `/project select luma-web` | `{'task': 'Fixing login bug', 'file': 'src/auth.js'}` | "✅ Switched to project `luma-web`. Welcome back! We were last working on: Fixing the login bug in `src/auth.js`." |
| `luma-web` | `/project select akasa-api` | `{'task': 'Refactoring the user model'}` | "✅ Switched to project `akasa-api`. Welcome back! We were last working on: Refactoring the user model." |
| `akasa-api` | `/project select mobile-ios`| `{'task': 'Debugging CI pipeline failure'}` | "✅ Switched to project `mobile-ios`. Welcome back! We were last working on: Debugging the CI pipeline failure." |

### Scenario: Edge Case - Switching to a Project with No Saved Context

**Given** a project has no previously saved Agent State (e.g., it is a new project or has never had a state-changing action).
**When** the user sends the command `/project select` for that project.
**Then** the system attempts to retrieve an Agent State but finds none.
**And** the system responds with the standard switch confirmation message, without a summary.

#### Examples

| current_project | input_command | saved_state_for_target | expected_response |
|---|---|---|---|
| `luma-web` | `/project select odin` | `None` | "✅ Switched to project `odin`." |
| `odin` | `/project select default` | `None` | "✅ Switched to project `default`." |
| `luma-web` | `/project new brand-new-project` | `None` (Implicit) | "🆕 Created and switched to project: `brand-new-project`" |

### Scenario: State Update - Performing an Action that Updates Context

**Given** the user is currently active in a project.
**When** the user executes a command that defines a new working context (e.g., editing a file, starting a debug session).
**Then** the system must create or update the persistent Agent State for the current project in the background.
**And** this new state will be used for future context restoration.

#### Examples

| current_project | input_command | expected_saved_state_for_project |
|---|---|---|
| `luma-web` | `/edit package.json "upgrade dependencies"` | `{'task': 'upgrade dependencies', 'file': 'package.json'}` |
| `akasa-api` | `/debug tests/test_auth.py` | `{'task': 'Debugging tests/test_auth.py', 'file': 'tests/test_auth.py'}` |
| `mobile-ios` | `Analyze the performance issue in Main.swift` | `{'task': 'Analyzing performance issue in Main.swift', 'file': 'Main.swift'}` |