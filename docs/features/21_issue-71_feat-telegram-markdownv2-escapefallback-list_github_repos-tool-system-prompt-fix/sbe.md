# SBE: Telegram MarkdownV2 Fixes & GitHub Repo Tool

> 📅 Created: 2026-03-16
> 🔗 Issue: https://github.com/oatrice/Akasa/issues/71

---

## Feature: Robust Messaging & Repository Management

This feature ensures Telegram messages are delivered reliably by escaping MarkdownV2 reserved characters and providing a fallback mechanism for parsing errors. It also expands the agent's capabilities to list GitHub repositories and discuss DevOps/Project Management topics.

### Scenario: Happy Path - MarkdownV2 Escaping

**Given** The LLM generates a response containing special MarkdownV2 characters
**When** The `_send_response` method processes the text before sending to Telegram
**Then** All reserved characters are escaped with a backslash to ensure valid MarkdownV2 syntax

#### Examples

| llm_output | sent_to_telegram | status |
|------------|------------------|--------|
| `Hello_World` | `Hello\_World` | 200 OK |
| `ERROR: [Critical]` | `ERROR: \[Critical\]` | 200 OK |
| `x * y + z` | `x \* y \+ z` | 200 OK |
| `User #123 (Admin)` | `User \#123 \(Admin\)` | 200 OK |

### Scenario: Error Handling - Message Send Fallback

**Given** A message is malformed or contains balanced bracket errors that escape logic missed
**When** The Telegram API returns a `400 Bad Request` error during the initial send attempt
**Then** The system catches the exception and automatically resends the message as plain text (no parse mode)

#### Examples

| original_parse_mode | error_response | fallback_action | final_result |
|---------------------|----------------|-----------------|--------------|
| `MarkdownV2` | `400 Bad Request: can't parse entities` | Resend with `parse_mode=None` | Message sent as plain text |
| `MarkdownV2` | `400 Bad Request: unmatched '['` | Resend with `parse_mode=None` | Message sent as plain text |

### Scenario: Happy Path - List GitHub Repositories Tool

**Given** The user has authorized the GitHub integration
**When** The user asks to list or show their repositories
**Then** The `list_github_repos` tool is invoked via the `GitHubService` and returns a formatted list of repos

#### Examples

| user_query | tool_invoked | tool_output_summary |
|------------|--------------|---------------------|
| "List my github repos" | `list_github_repos` | List of 30 repos (name, visibility, updated_at) |
| "Show me all repositories in this org" | `list_github_repos` | JSON array of repo objects |
| "What projects do I have on GitHub?" | `list_github_repos` | List of repos |

### Scenario: Happy Path - Expanded System Prompt Scope

**Given** The system prompt has been relaxed to include DevOps and Project Management
**When** The user asks a question related to these previously restricted domains
**Then** The agent answers the question instead of refusing it as "off-topic"

#### Examples

| user_query | previous_behavior | new_behavior |
|------------|-------------------|--------------|
| "How do I configure the CI pipeline?" | Refusal (Off-topic) | Detailed CI explanation |
| "What is the status of the current sprint?" | Refusal (Off-topic) | Analysis of project state |
| "Explain the deployment strategy" | Refusal (Off-topic) | Explanation of deployment |

### Scenario: Edge Case - Unrelated Topics (Boundary Check)

**Given** The system prompt still maintains boundaries for completely unrelated topics
**When** The user asks a question outside of Software, DevOps, or PM (e.g., Cooking)
**Then** The agent politely refuses to answer

#### Examples

| user_query | expected_response_type |
|------------|------------------------|
| "How do I bake a cake?" | Refusal |
| "What is the capital of France?" | Refusal (unless context implies geodata API) |
| "Write a poem about flowers" | Refusal |