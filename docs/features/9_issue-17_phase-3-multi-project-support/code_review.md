# Luma Code Review Report

**Date:** 2026-03-08 16:06:53
**Files Reviewed:** ['docs/ROADMAP.md', 'docs/features/9_issue-17_phase-3-multi-project-support/plan.md', 'docs/features/9_issue-17_phase-3-multi-project-support/analysis.md', 'app/services/redis_service.py', 'app/services/chat_service.py', 'docs/features/9_issue-17_phase-3-multi-project-support/sbe.md', 'docs/akasa_analysis.md', 'tests/services/test_redis_service_multi_project.py', 'tests/services/test_redis_service.py', 'README.md', 'docs/features/9_issue-17_phase-3-multi-project-support/spec0.md', 'docs/features/9_issue-17_phase-3-multi-project-support/spec.md']

## 📝 Reviewer Feedback

FAIL

The implementation in `app/services/chat_service.py` for the `_handle_project_command` function does not follow the user journey and SBE scenarios outlined in the provided specification documents.

### 1. Incorrect Command Structure

-   **Issue**: The implementation requires subcommands like `/project select <name>` or `/project new <name>`.
-   **Specification**: The `spec.md` and `sbe.md` files clearly define a simpler, more direct command: `/project <project_name>`. The user should be able to switch projects with a single command.

### 2. Unspecified and Buggy Features

-   **Issue**: The code introduces `new` and `rename` subcommands which were not part of the specification.
-   **`new`**: This allows creating projects on the fly, which contradicts the SBE scenario that requires projects to exist for a switch to be successful.
-   **`rename`**: This feature is incomplete and has a known bug where chat history is not migrated, leading to data loss for the user. Unspecified and buggy features should not be included.

### Recommended Fix

Refactor `_handle_project_command` in `app/services/chat_service.py` to simplify its logic and align with the specification:

1.  **No arguments (`/project`)**: List available projects and show the current one. The existing implementation for this is good.
2.  **One argument (`/project <name>`)**:
    -   Validate if the project `<name>` exists in the user's list of projects (as returned by `redis_service.get_project_list(chat_id)`).
    -   If it exists, switch the context using `redis_service.set_current_project(chat_id, target)`.
    -   If it does not exist, return an error message like `"Project '<name>' not found."` as specified in the SBE.
3.  **Remove the `select`, `new`, `list`, and `rename` subcommands entirely.**

Here is an example of the corrected logic:

```python
async def _handle_project_command(chat_id: int, args: list[str]) -> None:
    """Handles /project command to switch or view project context."""
    
    # Case 1: /project (no arguments) -> Show status
    if not args:
        current = await redis_service.get_current_project(chat_id)
        projects = await redis_service.get_project_list(chat_id)
        
        msg = f"📂 Current Project: `{current}`\\n\\n"
        msg += "Available Projects:\\n"
        for p in sorted(projects):
            marker = "✅" if p == current else "•"
            msg += f"{marker} `{p}`\\n"
        
        msg += "\\nUsage: `/project <name>` to switch."
        await _send_response(chat_id, msg)
        return

    # Case 2: /project <name> (one argument) -> Switch project
    if len(args) == 1:
        target_project = args[0].lower()
        available_projects = await redis_service.get_project_list(chat_id)
        
        if target_project in available_projects:
            await redis_service.set_current_project(chat_id, target_project)
            await _send_response(chat_id, f"✅ Switched to project: `{target_project}`")
        else:
            # Per SBE, we should error on non-existent projects
            await _send_response(chat_id, f"❌ Project `{target_project}` not found. Use `/project` to see available projects.")
        return

    # Case 3: Too many arguments
    await _send_response(chat_id, "❌ Invalid usage. Use `/project <name>` or just `/project`.")
```

## 🧪 Test Suggestions

### Manual Verification Guide

This guide will help you manually test the new multi-project functionality. Please perform these steps in your Telegram chat with the running bot.

---

### Part 1: Initial State & Basic Commands

1.  **Step 1:** Ensure you have a clean Redis instance (or run `redis-cli FLUSHALL`).
2.  **Step 2:** Start the bot.
3.  **Step 3:** Send the command `/project` to the bot.
    *   **Expected Result:** The bot should reply with a message indicating that the current project is `default` and show `default` in the list of available projects. It should also display usage instructions for `select`, `new`, and `rename`.

---

### Part 2: Creating New Projects

1.  **Step 1:** Send the command `/project new project-a`.
    *   **Expected Result:** The bot should reply with a confirmation like "Created and switched to project: `project-a`".
2.  **Step 2:** Send the command `/project new project-b`.
    *   **Expected Result:** The bot should reply with a confirmation like "Created and switched to project: `project-b`".
3.  **Step 3:** Send the command `/project`.
    *   **Expected Result:** The bot should now show that the current project is `project-b`. The list of available projects should contain `default`, `project-a`, and `project-b`.

---

### Part 3: Verifying Context Switching & History Isolation

1.  **Step 1:** You should currently be in `project-b`. Send the message: `My favorite color is blue.` The bot will respond; the exact response doesn't matter.
2.  **Step 2:** Switch to `project-a` by sending the command: `/project select project-a`.
    *   **Expected Result:** The bot confirms the switch with "Switched to project: `project-a`".
3.  **Step 3:** In `project-a`, send the message: `My favorite color is red.`
4.  **Step 4:** Now, ask the bot a question that relies on context: `What is my favorite color?`
    *   **Expected Result:** The bot should reply with something related to "red", as it's in the context of `project-a`. It should *not* mention "blue".
5.  **Step 5:** Switch back to `project-b`: `/project select project-b`.
6.  **Step 6:** Ask the same question again: `What is my favorite color?`
    *   **Expected Result:** The bot should now reply with something related to "blue", as it is using the history from `project-b`. It should *not* mention "red".

---

### Part 4: Error Handling

1.  **Step 1:** Send an invalid subcommand: `/project switch project-a`.
    *   **Expected Result:** The bot should reply with an error message like "Invalid usage. Try `/project` for help."
2.  **Step 2:** Try to select a project that does not exist: `/project select non-existent-project`.
    *   **Expected Result:** The bot should reply with an error message like "Project `non-existent-project` not found."
3.  **Step 3:** Send the command with too many arguments: `/project select project-a project-b`.
    *   **Expected Result:** The bot should reply with the "Invalid usage" error message.

