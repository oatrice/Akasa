# Implementation Plan: GitHub CLI Wrapper Service

> **Refers to**: [Spec Link](./spec.md)
> **Status**: Ready for Dev

## 1. Architecture & Design
*High-level technical approach.*

The `GithubService` will act as a Pythonic abstraction layer over the GitHub CLI (`gh`). It will use the standard library's `subprocess` module to execute commands. 

- **Execution Model**: A centralized private method `_run_gh_command` will handle the complexity of calling `subprocess.run`, capturing output, and injecting the necessary environment variables (specifically `GH_TOKEN`).
- **Data Exchange**: Most commands will use the `--json` flag to receive structured data, which will then be parsed into Python dictionaries using `json.loads()`.
- **Security**: The `GH_TOKEN` will be sourced from the application's configuration. To prevent accidental leaks, the token will be injected into the environment of the subprocess only, and the command arguments logged will have the token omitted.
- **Error Handling**: Custom exceptions (`GitHubServiceError`, `GitHubAuthError`) will be raised based on the CLI's return code and stderr content to allow the calling `ChatService` to provide meaningful feedback to the user.

### Component View
- **Modified Components**:
    - `app/config.py`: To include `GITHUB_TOKEN`.
    - `.env.example`: To document the new requirement.
- **New Components**:
    - `app/services/github_service.py`: The service implementation.
    - `tests/services/test_github_service.py`: Unit tests with comprehensive mocking.

### Data Model Changes
```python
# No new database models. 
# Internal data structures will reflect GitHub's JSON schema.
class GitHubIssue(TypedDict):
    number: int
    title: str
    state: str
    url: str
```

---

## 2. Step-by-Step Implementation

### Step 1: Configuration Update
- **Docs**: Update `.env.example`.
- **Code**: Add `GITHUB_TOKEN` to `app/config.py`.
- **Verification**: Ensure `settings.GITHUB_TOKEN` is accessible.

### Step 2: Base Service Scaffolding and Execution Logic
- **Code**: 
    - Create `app/services/github_service.py`.
    - Define `GitHubServiceError(Exception)` and `GitHubAuthError(GitHubServiceError)`.
    - Implement `_run_gh_command(args: list[str]) -> subprocess.CompletedProcess`.
    - Logic should check if `gh` is installed (`FileNotFoundError`).
    - Logic should inject `env={"GH_TOKEN": settings.GITHUB_TOKEN, ...}`.
- **Tests**: Mock `subprocess.run` to simulate a missing CLI and an authentication error.

### Step 3: Implement Core Features
- **Code**:
    - `list_issues(repo: str)`: Executes `gh issue list --repo <repo> --json number,title,state,url`.
    - `create_issue(repo: str, title: str, body: str)`: Executes `gh issue create --repo <repo> --title <title> --body <body>`.
    - `get_pr_status(repo: str)`: Executes `gh pr status --repo <repo> --json ...`.
- **Tests**: Mock successful JSON responses and verify the parsing logic.

### Step 4: Integration and Final Polish
- **Code**: Add logging for command execution (sans token).
- **Tests**: Verify that no sensitive info is leaked in `logger` calls if possible, or verify by code review.

---

## 3. Verification Plan
*How will we verify success?*

### Automated Tests
- [ ] **Unit Tests**: `tests/services/test_github_service.py`.
    - Mock `subprocess.run` to return specific stdout/stderr/returncodes.
    - Test `list_issues` with valid JSON.
    - Test `create_issue` and verify the URL is extracted from stdout.
    - Test failure cases: `gh` not installed, 401 Unauthorized, Repo not found.
- [ ] **Linting**: Ensure PEP8 compliance.

### Manual Verification
- [ ] **Requirement**: Ensure `gh` CLI is installed on the local machine and a valid `GITHUB_TOKEN` is in `.env`.
- [ ] **List Issues**: Run a temporary test script or use a Python shell to call `GithubService.list_issues("oatrice/Akasa")`.
- [ ] **Create Issue**: Call `create_issue` with a test title and verify the issue appears on GitHub.
- [ ] **Token Missing**: Temporarily remove the token from `.env` and verify the service raises `GitHubAuthError`.