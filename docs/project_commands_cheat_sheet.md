# Project Commands Cheat Sheet

Quick reference for tracking work per project in Akasa.

## Core Flow

1. Select the project you want to work on.
2. Save a note for the current task.
3. Check project status or overview.
4. Run project-specific commands.

## Telegram Commands

### Project Context

```text
/project
Show current project and known project list

/project select <name>
Switch to a project

/project new <name>
Create and switch to a new project

/project rename <old> <new>
Rename a project

/project status
Show detailed status for the active project

/project status <name>
Show detailed status for a specific project

/project path [name]
Show the bound folder path for the current project or a named project

/project bind [name] <absolute_path>
Bind a project to a local folder path
If the project name is omitted, Akasa binds the current project

/projects overview
Show a compact overview of all known projects

/projects overview verbose
Show overview plus recent history snippet per project

/projects overview markdown
Force human-readable markdown output

/projects overview json
Return machine-readable JSON in a fenced code block
```

### Task Tracking

```text
/note <task description>
Save the current task for the active project
```

### GitHub Shortcuts

```text
/github repo <owner/repo>
/github issues [owner/repo]
/github issue new <repo> <title> [body]
/github pr [owner/repo]
/github pr new <repo> <title> [body]
```

If the repo is omitted for `/github issues` or `/github pr`, Akasa uses the current project name. For best results, use project names in `owner/repo` format.

### Local Tool Queue

```text
/queue <tool> <command> [args_json]
```

Examples:

```text
/queue gemini check_status {}
/queue gemini run_task {"task":"review open PRs","branch":"main"}
/queue luma list_issues {"project":"akasa","state":"open"}
/queue zed open_file {"path":"README.md"}
```

Available tools and commands are controlled by:
[command_whitelist.yaml](/Users/oatrice/Software-projects/Akasa/config/command_whitelist.yaml)

## Local API Flow

Use `X-Akasa-API-Key` for authenticated local tools.

### Sync active project

```bash
curl -H "X-Akasa-API-Key: $AKASA_KEY" \
  "$BASE_URL/api/v1/context/project"

curl -X PUT \
  -H "X-Akasa-API-Key: $AKASA_KEY" \
  -H "Content-Type: application/json" \
  -d '{"active_project":"akasa"}' \
  "$BASE_URL/api/v1/context/project"

curl -X PUT \
  -H "X-Akasa-API-Key: $AKASA_KEY" \
  -H "Content-Type: application/json" \
  -d '{"active_project":"akasa","project_path":"/Users/oatrice/Software-projects/Akasa"}' \
  "$BASE_URL/api/v1/context/project"
```

### Enqueue and poll command status

```bash
curl -X POST \
  -H "X-Akasa-API-Key: $AKASA_KEY" \
  -H "Content-Type: application/json" \
  -d '{"tool":"gemini","command":"check_status","args":{}}' \
  "$BASE_URL/api/v1/commands"

curl -H "X-Akasa-API-Key: $AKASA_KEY" \
  "$BASE_URL/api/v1/commands/<command_id>"
```

### Deployment status

```bash
curl -X POST \
  -H "X-Akasa-API-Key: $AKASA_KEY" \
  -H "Content-Type: application/json" \
  -d '{"command":"vercel deploy","cwd":"/path/to/repo","project":"akasa"}' \
  "$BASE_URL/api/v1/deployments"

curl -H "X-Akasa-API-Key: $AKASA_KEY" \
  "$BASE_URL/api/v1/deployments/<deployment_id>"
```

## What Status Views Show

`/project status` includes:
- saved task note
- bound folder path if configured
- focus file if present
- recent command queue activity
- recent deployment activity
- recent agent task notifications

`/projects overview` includes:
- all known projects for the current chat
- active project marker
- latest saved task per project
- bound folder path per project when available
- last updated timestamp per project
- recent history count per project
- latest command, deployment, and agent-task summary per project

`/projects overview verbose` adds:
- recent history snippet per project
