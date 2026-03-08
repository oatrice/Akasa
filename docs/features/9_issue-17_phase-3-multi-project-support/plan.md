# Implementation Plan: Multi-Project Context Switching in Chat

> **Refers to**: [Spec Link](./spec.md)
> **Status**: Draft

## 1. Architecture & Design
*High-level technical approach.*

The implementation will focus on introducing a project-aware context layer into the application's core. The current monolithic state will be refactored into a namespaced state managed by a central `StateManager`. A new `/project` command will be intercepted by the main command processor (`gemini_cli.py`) to switch this active context. All subsequent operations that depend on project-specific configurations (like API clients) will be modified to retrieve their settings from the currently active project state.

### Component View
- **Modified Components**:
    - `luma_core/state_manager.py`: To be heavily refactored from managing a single global state to a dictionary of project-specific states. It will also track the currently active project for the session.
    - `luma_core/config.py`: To be updated with a new data structure for defining and loading a list of available projects and their configurations (e.g., name, repo URL, API keys).
    - `luma_core/gemini_cli.py`: The main command processing loop will be modified to recognize and handle the `/project` command as a special case before attempting to execute other actions.
    - `luma_core/github_client.py` (and similar clients): Functions will be updated to accept a `project_context` object to ensure they use the correct credentials and endpoints.

- **New Components**:
    - `luma_core/auth.py`: A new module responsible for handling authorization logic. It will contain functions to verify if a user has permission to access a given project.
    - `tests/test_auth.py`: Unit tests for the new authorization module.

- **Dependencies**: No new external dependencies are required.

### Data Model Changes
```python
# In luma_core/config.py
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class ProjectConfig:
    name: str
    github_repo: str
    # Other project-specific settings...

@dataclass
class LumaConfig:
    # ... existing fields
    projects: List[ProjectConfig] = field(default_factory=list)
    project_map: Dict[str, ProjectConfig] = field(default_factory=dict) # For O(1) lookup

# In luma_core/state_manager.py
# The State object itself remains the same, but how it's stored changes.
class StateManager:
    # Old structure (conceptual)
    # _state: State 

    # New structure (conceptual)
    _active_project_id: str
    _project_states: Dict[str, State] 
```

---

## 2. Step-by-Step Implementation

### Step 1: Update Configuration to be Project-Aware
- **Description**: Modify the configuration system to load and manage a list of projects. This provides the foundational data for what projects are available to switch between.
- **Files**:
    - `luma_core/config.py`: Introduce `ProjectConfig` and update `LumaConfig` as shown in the data model. Add logic to parse projects from the config file and build the `project_map` for quick lookups.
- **Verification**:
    - Modify `tests/test_config.py` to assert that a sample configuration with multiple projects is parsed correctly into the `LumaConfig` object.

### Step 2: Refactor StateManager for Multi-Project State
- **Description**: This is the core architectural change. The `StateManager` will no longer manage a single state but a dictionary of states keyed by project name. It will also manage which project is currently "active".
- **Files**:
    - `luma_core/state_manager.py`:
        - Change internal storage from a single `State` object to `Dict[str, State]`.
        - Add methods like `set_active_project(project_name: str)`, `get_active_project_state() -> State`, and `get_active_project_id() -> str`.
        - Update `save_state` and `load_state` to handle the new dictionary-based structure.
- **Verification**:
    - Update `tests/test_state_manager.py`. Test that you can set an active project, modify its state, switch to another project, modify its state, and then switch back to find the first project's state preserved. Test that saving and loading persists all project states correctly.

### Step 3: Implement Authorization Logic
- **Description**: Create a simple authorization module to check if a project is valid and accessible. For this phase, it can be a simple check against the loaded configuration.
- **Files**:
    - `luma_core/auth.py`: Create this new file. Add a function `is_project_authorized(project_name: str, config: LumaConfig) -> bool`. For now, this function will simply check if `project_name.lower()` exists as a key in `config.project_map`.
    - `tests/test_auth.py`: Create this new file. Write unit tests for `is_project_authorized`, checking for valid, invalid, and case-insensitive project names.
- **Verification**: Run the new unit tests.

### Step 4: Implement the `/project` Command Handler
- **Description**: Modify the main application loop to intercept the `/project` command, validate it, and use the `StateManager` and `Auth` module to perform the context switch.
- **Files**:
    - `luma_core/gemini_cli.py`:
        - In the main input processing function, add a check: `if input_text.startswith('/project'):`.
        - Parse the command to extract the `project_name`. Handle cases with missing names.
        - Call `auth.is_project_authorized()` to validate the project.
        - If authorized, call `state_manager.set_active_project()`.
        - Return the appropriate confirmation or error message to the user.
- **Verification**:
    - Add tests to `tests/test_gemini_cli.py` to simulate user input for the `/project` command.
    - Test the SBE scenarios: successful switch, switching to an unknown project, and using the command without a project name.

### Step 5: Integrate Project Context into Application Logic
- **Description**: Refactor existing functions that perform project-specific actions to use the active project's context.
- **Files**:
    - `luma_core/github_client.py`, `luma_core/actions.py`, etc.:
        - Identify functions that interact with external project resources (e.g., `list_issues`).
        - These functions should now retrieve the active project's state and config via the `StateManager`. For example: `active_project_config = config.project_map[state_manager.get_active_project_id()]`.
        - Use `active_project_config` to get the correct repository, API keys, etc.
- **Verification**:
    - Manually run existing commands after switching projects to ensure they operate on the correct project's resources.
    - Adapt existing integration tests (if any) to first set a project context before executing their actions.

---

## 3. Verification Plan
*How will we verify success?*

### Automated Tests
- [ ] **Unit Tests**:
    - `tests/test_config.py`: Verify multi-project configuration is loaded correctly.
    - `tests/test_state_manager.py`: Verify CRUD operations for multi-project states and active project switching.
    - `tests/test_auth.py`: Verify project authorization logic.
    - `tests/test_gemini_cli.py`: Verify the `/project` command handler logic for all SBE scenarios.
- [ ] **Integration Tests**:
    - An integration test will be created to:
        1. Start with project 'A'.
        2. Run a command (e.g., `list_issues`) and verify results are for 'A'.
        3. Switch context to project 'B' using the `/project` command.
        4. Run the same command and verify results are now for 'B'.

### Manual Verification
- [ ] **VC1**: Run the application and start with the default project. Run a simple command like `/status`.
- [ ] **VC2**: Switch to a valid, configured project using `/project <project_name>`. Verify the confirmation message is shown.
- [ ] **VC3**: Run the `/status` command again and confirm the context has changed to the new project.
- [ ] **VC4**: Attempt to switch to a project that does not exist in the configuration. Verify the correct error message is displayed and the context has not changed.
- [ ] **VC5**: Run the command `/project` with no name. Verify the usage error message is displayed and the context has not changed.