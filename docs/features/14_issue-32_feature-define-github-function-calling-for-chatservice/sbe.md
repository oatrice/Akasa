# SBE: GitHub Function Calling Integration in ChatService

> 📅 Created: 2026-03-10
> 🔗 Issue: https://github.com/oatrice/Akasa/issues/32

---

## Feature: GitHub Function Calling Integration in ChatService

To empower the ChatService to understand user requests related to GitHub and execute them by calling the appropriate functions from `GithubService`. This enables users to manage GitHub issues and comments directly from the chat interface, streamlining their workflow.

### Scenario: Happy Path - Creating a GitHub Issue

**Given** The user is having a conversation with the AI assistant.
**When** The user sends a message with a clear intent to create a GitHub issue, providing all necessary details (repository, title, and body).
**Then** The `ChatService` should correctly parse the intent and parameters, and successfully call the `GithubService.create_issue` function.

#### Examples

| input | expected_tool_call |
|-------|----------|
| "สร้าง issue ใน 'oatrice/Akasa' title: 'Refactor Database' body: 'Need to refactor the user table schema.'" | `GithubService.create_issue(repo='oatrice/Akasa', title='Refactor Database', body='Need to refactor the user table schema.')` |
| "I want to open a new issue in 'oatrice/Akasa'. Title is 'UI Bug on Mobile', description is 'The main menu overlaps on mobile view.'" | `GithubService.create_issue(repo='oatrice/Akasa', title='UI Bug on Mobile', body='The main menu overlaps on mobile view.')` |
| "ช่วยสร้างบั๊กหน่อย repo: 'oatrice/Akasa', title: 'Auth Error', body: 'Getting 500 error on login page.'" | `GithubService.create_issue(repo='oatrice/Akasa', title='Auth Error', body='Getting 500 error on login page.')` |
| "New issue for 'oatrice/Akasa': 'Update Dependencies'. Body: 'All project dependencies need to be updated to their latest versions.'"| `GithubService.create_issue(repo='oatrice/Akasa', title='Update Dependencies', body='All project dependencies need to be updated to their latest versions.')` |


### Scenario: Happy Path - Commenting on a GitHub Issue

**Given** The user is having a conversation with the AI assistant.
**When** The user sends a message with a clear intent to add a comment to an existing GitHub issue.
**Then** The `ChatService` should correctly parse the intent and parameters, and successfully call the `GithubService.create_comment` function.

#### Examples

| input | expected_tool_call |
|-------|----------|
| "Add a comment to issue #32 in 'oatrice/Akasa': 'I will take a look at this tomorrow.'" | `GithubService.create_comment(repo='oatrice/Akasa', issue_number=32, body='I will take a look at this tomorrow.')` |
| "ช่วยคอมเมนต์ใน issue #40 ของ 'oatrice/Akasa' ว่า 'This is blocked by #39.'" | `GithubService.create_comment(repo='oatrice/Akasa', issue_number=40, body='This is blocked by #39.')` |
| "Reply to 'oatrice/Akasa' issue 101: 'Can you provide the logs?'" | `GithubService.create_comment(repo='oatrice/Akasa', issue_number=101, body='Can you provide the logs?')` |
| "ฝากคอมเมนต์ issue 5, repo 'oatrice/Akasa' หน่อย 'Done. It has been deployed to staging.'" | `GithubService.create_comment(repo='oatrice/Akasa', issue_number=5, body='Done. It has been deployed to staging.')` |


### Scenario: Error Handling - Ambiguous or Incomplete Requests

**Given** The user is having a conversation with the AI assistant.
**When** The user sends a message to perform a GitHub action but omits necessary information.
**Then** The AI assistant should respond by asking for the missing details, without calling any GitHub tool.

#### Examples

| input | expected_response |
|-------|-------|
| "Create a new issue." | "Of course! Which repository should I create it in, and what are the title and body of the issue?" |
| "Add a comment to the latest issue." | "I can do that. Could you please specify the repository and the issue number?" |
| "ช่วยสร้าง issue 'Fix the button' ให้ที" | "ได้เลยครับ จะให้สร้างใน repository ไหน และมีรายละเอียดเพิ่มเติมสำหรับ body ของ issue ไหมครับ" |


### Scenario: Error Handling - Unsupported GitHub Actions

**Given** The user is having a conversation with the AI assistant.
**When** The user asks to perform a GitHub action that is not supported by the defined tools.
**Then** The AI assistant should inform the user that it cannot perform the requested action.

#### Examples

| input | error |
|-------|-------|
| "Delete the 'oatrice/Akasa' repository." | "I'm sorry, I don't have the capability to delete repositories." |
| "Merge the pull request #55 in 'oatrice/Akasa'." | "I cannot merge pull requests at the moment. I can only create issues and comments." |
| "Close issue #30." | "I'm sorry, I can only create issues and add comments. I cannot close them." |