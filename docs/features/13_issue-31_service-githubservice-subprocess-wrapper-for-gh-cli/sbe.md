# SBE: GitHub CLI Wrapper Service

> 📅 Created: 2026-03-09
> 🔗 Issue: https://github.com/oatrice/Akasa/issues/31

---

## Feature: GitHub CLI Wrapper Service

This service provides a Python interface to the GitHub CLI (`gh`) by using the `subprocess` module. It allows the Akasa bot to perform repository management tasks such as listing and creating issues, and checking Pull Request status, leveraging the existing authentication and capabilities of the `gh` tool.

### Scenario: List Issues Successfully (Happy Path)

**Given** the `gh` CLI is installed and authenticated with a valid `GITHUB_TOKEN`
**When** the service calls `list_issues` for a valid repository
**Then** the system executes `gh issue list --json ...` and returns a list of issue objects

#### Examples

| repository | mock_cli_json_output | expected_result_count | first_issue_title |
|------------|-----------------------|-----------------------|-------------------|
| "oatrice/Akasa" | `[{"number": 1, "title": "Setup", "state": "OPEN"}]` | 1 | "Setup" |
| "oatrice/Akasa" | `[]` | 0 | n/a |
| "google/fastapi" | `[{"number": 10, "title": "Bug A", "state": "OPEN"}, {"number": 11, "title": "Task B", "state": "OPEN"}]` | 2 | "Bug A" |

### Scenario: Create Issue Successfully (Happy Path)

**Given** the `gh` CLI is authenticated and the user has write access to the repo
**When** the service calls `create_issue` with a title and body
**Then** the system executes `gh issue create` and returns the URL of the new issue

#### Examples

| repository | title | body | mock_cli_stdout | expected_url |
|------------|-------|------|-----------------|--------------|
| "oatrice/Akasa" | "Fix Bug" | "Description here" | "https://github.com/oatrice/Akasa/issues/5" | "https://github.com/oatrice/Akasa/issues/5" |
| "oatrice/Akasa" | "New Idea" | "More details" | "https://github.com/oatrice/Akasa/issues/6" | "https://github.com/oatrice/Akasa/issues/6" |

### Scenario: Error Handling - Authentication Failure

**Given** the `GITHUB_TOKEN` environment variable is invalid, expired, or missing
**When** any GitHub service method is called
**Then** the system catches the non-zero exit code from `gh` and raises a `GitHubAuthError`

#### Examples

| action | env_token_state | cli_stderr_contains | expected_exception |
|--------|-----------------|---------------------|--------------------|
| list_issues | "invalid" | "GraphQL: Your token has not been granted..." | `GitHubAuthError` |
| create_issue | "expired" | "error: oauth2: cannot fetch token" | `GitHubAuthError` |
| pr_status | "missing" | "not logged in to any GitHub hosts" | `GitHubAuthError` |

### Scenario: Edge Case - Repository Not Found

**Given** the bot is authenticated but the requested repository does not exist
**When** `list_issues` or `get_pr_status` is called
**Then** the system returns an error indicating the repository was not found

#### Examples

| repository | cli_stderr_output | expected_error_msg |
|------------|-------------------|--------------------|
| "oatrice/fake-repo" | "Could not find repository" | "Repository 'oatrice/fake-repo' not found" |
| "unknown/unknown" | "HTTP 404: Not Found" | "Repository 'unknown/unknown' not found" |

### Scenario: Edge Case - GitHub CLI Missing

**Given** the `gh` executable is not installed or not in the system's PATH
**When** any service method is called
**Then** the system catches the `FileNotFoundError` and returns a descriptive installation error

#### Examples

| environment | action | system_error | expected_user_feedback |
|-------------|--------|--------------|------------------------|
| No `gh` installed | list_issues | `[Errno 2] No such file or directory: 'gh'` | "GitHub CLI (gh) is not installed on the server." |