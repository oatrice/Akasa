# SBE: Check Kanban and ROADMAP.md via Telegram

> 📅 Created: 2026-03-19
> 🔗 Issue: https://github.com/oatrice/Akasa/issues/82

---

## Feature: Check Kanban and ROADMAP.md via Telegram

Enable users to view a summary of a GitHub project's Kanban board and the content of the `ROADMAP.md` file directly from Telegram. This functionality is accessible via slash commands (`/gh kanban`, `/gh roadmap`) and natural language prompts through LLM function calling. The system resolves the target repository using a priority of: explicit argument > current project context > bound project path.

### Scenario: Happy Path

**Given** The user is authenticated with GitHub and has a valid project context or provides an explicit repository name
**When** The user sends a command or a natural language request to view the Kanban or Roadmap
**Then** Akasa returns a compact, Telegram-friendly summary with status counts, key items, and relevant links

#### Examples

| input | context_repo | expected_output_contains |
|-------|--------------|--------------------------|
| `/gh kanban oatrice/Akasa` | None | "Kanban for oatrice/Akasa", "Todo: 5", "In Progress: 2", "Done: 10" |
| `/gh roadmap` | `oatrice/Akasa` | "Roadmap for oatrice/Akasa", "Current Phase", "Future Goals", "Link" |
| "ขอดู kanban ของโปรเจกต์นี้" | `oatrice/Akasa` | "Kanban summary", "Status: Backlog (8)", "Status: In Progress (3)" |
| "Summarize the roadmap for oatrice/Akasa" | None | "Summary of ROADMAP.md", "Milestones", "Upcoming Features" |
| `/gh roadmap oatrice/Akasa` | None | "Roadmap for oatrice/Akasa", "View on GitHub" |

### Scenario: Edge Cases

**Given** The target repository exists but has specific configuration states (e.g., missing files, multiple boards, or local path priority)
**When** The user requests the Kanban or Roadmap
**Then** Akasa resolves the most relevant board or provides a specific fallback message regarding the missing content

#### Examples

| input | repo_state | expected_output_contains |
|-------|------------|--------------------------|
| `/gh roadmap oatrice/Legacy` | No `ROADMAP.md` file | "No ROADMAP.md found in oatrice/Legacy. Please check docs folder." |
| `/gh kanban oatrice/LargeOrg` | 3 Project Boards | "Multiple boards found. Showing 'Product Roadmap' (best match)." |
| `/gh kanban oatrice/NewRepo` | No Project Boards | "No GitHub Project boards found for oatrice/NewRepo." |
| `/gh roadmap` | Local path bound with `docs/ROADMAP.md` | "Reading local ROADMAP.md summary from bound path..." |
| `/gh roadmap oatrice/Akasa` | Local file missing, Repo file exists | "Local roadmap not found. Fetching from oatrice/Akasa repository..." |

### Scenario: Error Handling

**Given** The user provides invalid repository names or requests data without establishing a context
**When** The user sends an invalid action or lacks required permissions
**Then** Akasa returns a helpful error message guiding the user on how to resolve the issue

#### Examples

| input | context_repo | error_msg_contains |
|-------|--------------|--------------------|
| `/gh kanban` | None | "Please specify a repository or set a project context first." |
| `/gh roadmap my-broken-repo` | None | "Invalid repository format. Please use 'owner/repo' (e.g., oatrice/Akasa)." |
| `/gh kanban private/secret-repo` | No Access | "Repository not found or Access Denied. Check your permissions." |
| "Show me the kanban for nonexistent/project" | None | "Could not find repository: nonexistent/project." |
| `/gh roadmap` | Invalid Context | "Could not resolve project context or bound local path." |