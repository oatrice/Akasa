# Specification: GitHub Function Calling for ChatService

> Document detailing the feature to enable GitHub tool usage for the LLM within `ChatService`.

---

## 📌 Feature Overview

| รายการ | รายละเอียด |
|---|---|
| **Feature Name** | Define GitHub Function Calling for ChatService |
| **Version** | v1.0.0 |
| **Created Date** | 2026-03-10 |
| **Last Updated** | 2026-03-10 |
| **Author** | Gemini |
| **Status** | 📝 Draft |

---

## 1. Executive Summary
This feature enables the Akasa AI assistant to understand and execute GitHub-related tasks directly from chat. By defining specific "tools" for the LLM, the `ChatService` can interpret user intent (e.g., "create an issue") and trigger corresponding actions in the `GithubService`. This provides a seamless, conversational interface for developers to manage their GitHub workflow.

---

## 2. Goals and User Stories

### Goals
*   **G1:** Enable the LLM to recognize user intent related to GitHub actions.
*   **G2:** Allow users to perform basic GitHub operations (like creating issues) through natural language commands in chat.
*   **G3:** Provide informative feedback to the user upon successful or failed execution of a GitHub action.

### User Stories

#### Story 1: Create a GitHub Issue via Chat
```
As a developer
I want to command the assistant to create a GitHub issue
So that I can quickly capture tasks and bugs without leaving my chat client.
```
**Acceptance Criteria:**
- **Given** I am in a chat session with the assistant
- **When** I send a message like, "Help me create an issue in the `oatrice/Akasa` repo. Title is 'Fix login button'. The body should be 'The login button is not working on the main page.'"
- **Then** the system identifies the intent to create an issue.
- **And** it calls the appropriate GitHub tool with parameters: `owner='oatrice'`, `repo='Akasa'`, `title='Fix login button'`, and `body='The login button is not working on the main page.'`.
- **And** the assistant replies with a confirmation message, including the URL of the newly created issue.

#### Story 2: List Open Pull Requests for a Repository
```
As a developer
I want to ask the assistant for a list of open pull requests
So that I can get a quick overview of pending code reviews.
```
**Acceptance Criteria:**
- **Given** I am in a chat session with the assistant
- **When** I ask, "What are the open PRs for `oatrice/Akasa`?"
- **Then** the system identifies the intent to list pull requests.
- **And** it calls the appropriate GitHub tool with parameters: `owner='oatrice'`, `repo='Akasa'`.
- **And** the assistant replies with a formatted list of open pull requests, showing their title, number, and author.

---

## 3. Specification by Example (SBE)

### Scenario 1: User successfully creates a GitHub issue

| GIVEN | The user wants to create a new issue. |
|---|---|
| **WHEN** | The user sends the following message: |
| | `ช่วยสร้าง issue ในโปรเจกต์ Akasa หน่อย หัวข้อ 'UI Glitch on Dashboard' เนื้อหาคือ 'The main chart is not rendering correctly.'` |
| **THEN** | The `ChatService` understands the intent and parameters from the user's message. |
| **AND** | The `ChatService` invokes the `create_issue` tool with the following arguments: |
| | **Example:** |
| | ```json |
| | { |
| |   "owner": "oatrice", |
| |   "repo": "Akasa", |
| |   "title": "UI Glitch on Dashboard", |
| |   "body": "The main chart is not rendering correctly." |
| | } |
| | ``` |
| **AND** | The `GithubService` successfully creates the issue. |
| **AND** | The system sends a confirmation message back to the user: |
| | `สร้าง Issue #124 เรียบร้อยแล้วค่ะ: https://github.com/oatrice/Akasa/issues/124` |

### Scenario 2: User requests to list open Pull Requests

| GIVEN | The user wants to see all open pull requests for a repository. |
|---|---|
| **WHEN** | The user sends the following message: |
| | `ขอดู PR ทั้งหมดของโปรเจกต์ Akasa หน่อย` |
| **THEN** | The `ChatService` understands the intent to list pull requests. |
| **AND** | The `ChatService` invokes the `list_prs` tool with the following arguments: |
| | **Example:** |
| | ```json |
| | { |
| |   "owner": "oatrice", |
| |   "repo": "Akasa" |
| | } |
| | ``` |
| **AND** | The `GithubService` successfully retrieves the list of open PRs. |
| **AND** | The system formats the information and sends it back to the user: |
| | `นี่คือรายการ PR ที่ยังเปิดอยู่สำหรับ oatrice/Akasa:`<br/>`- #122: Feature - Add new login flow by @developerA`<br/>`- #123: Fix - Correct typo in README by @developerB` |

---

## 4. Scope

### In Scope
*   Defining the function/tool specifications for GitHub actions within `ChatService` so the LLM knows what it can call.
*   Mapping the LLM's tool-call request to the appropriate method in `GithubService`.
*   Supported GitHub actions for this iteration:
    *   `create_issue(owner, repo, title, body)`
    *   `list_open_prs(owner, repo)`

### Out of Scope
*   The underlying implementation of the `GithubService` methods (this feature only concerns defining the "bridge" in `ChatService`).
*   User authentication with GitHub. The system will use a single, pre-configured GitHub token for all operations.
*   Support for any GitHub actions other than the ones listed as "In Scope".
*   Complex interactions such as commenting on issues/PRs, creating branches, or merging code.