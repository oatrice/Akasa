"""
Chat Service — ประสานงานระหว่าง Telegram, Redis, และ LLM

Flow: Telegram → ดึง history จาก Redis → สร้าง messages context → LLM → บันทึก history → ส่งกลับ Telegram
Graceful degradation: ถ้า Redis ล่ม ยังทำงานได้เป็น stateless
"""

from app.models.telegram import Update, Message, CallbackQuery
from app.models.agent_state import AgentState
from app.services import redis_service
from app.services import rate_limiter
from app.services.telegram_service import tg_service
from app.services.github_service import GitHubService, GitHubServiceError, GitHubAuthError
from app.utils.markdown_utils import escape_markdown_v2, escape_markdown_v2_content, split_markdown_message
# Re-import module to support existing tests that patch 'llm_service'
from app.services import llm_service
from app.services.llm_service import OpenRouterInsufficientCreditsError
from app.services import command_queue_service
from app.services import agent_task_service
from app.services import deploy_service
from app.models.command import CommandQueueRequest
from app.models.notification import TaskNotificationRequest
from app.exceptions import LLMTimeoutError, LLMUpstreamError, LLMMalformedResponseError
import httpx
import logging
import os
import subprocess
import json
from typing import Optional
from datetime import datetime, timezone
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize GitHub Service
github_service = GitHubService()

# --- Issue #32: GitHub Tool Definitions ---
GITHUB_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_github_issue",
            "description": "Creates a new issue in a specified GitHub repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {"type": "string", "description": "The full name of the repository (e.g., 'owner/repo')."},
                    "title": {"type": "string", "description": "The title of the issue."},
                    "body": {"type": "string", "description": "The body content of the issue."},
                    "duration": {"type": "string", "description": "Optional estimated or observed duration for the GitHub Project card (e.g., '90m', '2h', '1h 30m', '38883s')."},
                },
                "required": ["repo", "title", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_github_open_prs",
            "description": "Lists all open pull requests for a specified GitHub repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {"type": "string", "description": "The full name of the repository (e.g., 'owner/repo')."},
                },
                "required": ["repo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_github_comment",
            "description": "Adds a comment to an existing GitHub issue or pull request.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {"type": "string", "description": "The full name of the repository (e.g., 'owner/repo')."},
                    "issue_number": {"type": "integer", "description": "The number of the issue or pull request."},
                    "body": {"type": "string", "description": "The body content of the comment."},
                },
                "required": ["repo", "issue_number", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "close_github_issue",
            "description": "Closes an existing GitHub issue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {"type": "string", "description": "The full name of the repository (e.g., 'owner/repo')."},
                    "issue_number": {"type": "integer", "description": "The number of the issue."},
                },
                "required": ["repo", "issue_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_github_issue",
            "description": "Deletes an existing GitHub issue (Permanent).",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {"type": "string", "description": "The full name of the repository (e.g., 'owner/repo')."},
                    "issue_number": {"type": "integer", "description": "The number of the issue."},
                },
                "required": ["repo", "issue_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_github_issue",
            "description": "Gets details of a specific GitHub issue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {"type": "string", "description": "The full name of the repository (e.g., 'owner/repo')."},
                    "issue_number": {"type": "integer", "description": "The number of the issue."},
                },
                "required": ["repo", "issue_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_github_issues",
            "description": "Searches for GitHub issues based on a query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {"type": "string", "description": "The full name of the repository (e.g., 'owner/repo')."},
                    "query": {"type": "string", "description": "The search query (e.g., 'bug', 'feature')."},
                },
                "required": ["repo", "query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_github_pr",
            "description": "Creates a new Pull Request. PREREQUISITE: Changes must be committed and pushed to the remote branch first. If not sure, call 'git_status' first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {"type": "string", "description": "The full name of the repository (e.g., 'owner/repo')."},
                    "title": {"type": "string", "description": "The title of the Pull Request."},
                    "body": {"type": "string", "description": "The body content of the Pull Request."},
                    "head": {"type": "string", "description": "The name of the branch where your changes are implemented."},
                    "base": {"type": "string", "description": "The name of the branch you want your changes pulled into (default: 'main')."},
                },
                "required": ["repo", "title", "body", "head", "base"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_github_repos",
            "description": "Lists GitHub repositories for the authenticated user. Use this when the user asks about their projects, repositories, or active repos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "owner": {"type": "string", "description": "GitHub username or organization (optional, defaults to authenticated user)."},
                    "limit": {"type": "integer", "description": "Max number of repos to return (default: 30)."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_github_kanban",
            "description": "Gets a compact kanban-style summary for a GitHub repository. Use this when the user asks what is in progress, what is on the board, what is next, current project status, backlog, open work, kanban, or board status. If no project board exists, it should summarize open issues instead.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Optional repository in owner/repo format. Omit this when the current Telegram project context should be used.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_github_roadmap",
            "description": "Gets a compact roadmap summary from docs/ROADMAP.md for a GitHub repository or the current project context. Use this when the user asks about the roadmap, future plans, milestones, phases, strategic direction, upcoming work, or what the project will do next.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Optional repository in owner/repo format. Omit this when the current Telegram project context should be used.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_status",
            "description": "Check local git status (uncommitted changes).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_add",
            "description": "Stage files for commit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to add (default: '.')"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_commit",
            "description": "Commit staged changes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Commit message."},
                },
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_push",
            "description": "Push commits to remote origin. (Requires Confirmation)",
            "parameters": {
                "type": "object",
                "properties": {
                    "branch": {"type": "string", "description": "Branch name (default: 'main')."},
                },
            },
        },
    },
]

TOOLS_REQUIRING_CONFIRMATION = ["delete_github_issue", "git_push", "git_commit", "git_add"]
COMMAND_ALIASES = {
    "/pj": "/project",
    "/gh": "/github",
    "/q": "/queue",
}

KANBAN_SHORTCUT_PHRASES = (
    "งานถึงไหนแล้ว",
    "สถานะโปรเจกต์",
    "สถานะโปรเจ็ค",
    "สถานะโปรเจกต์นี้",
    "สถานะโปรเจ็คนี้",
    "มีอะไรค้างอยู่",
    "ค้างอะไรอยู่",
    "what is in progress",
    "project status",
    "board status",
    "backlog",
    "kanban",
)

ROADMAP_SHORTCUT_PHRASES = (
    "โปรเจกต์นี้จะทำอะไรต่อ",
    "โปรเจ็คนี้จะทำอะไรต่อ",
    "แผนต่อไป",
    "roadmap",
    "future plans",
    "what's next",
    "what is next",
    "next milestone",
    "next milestones",
    "milestone",
    "milestones",
)

CURRENT_WORK_SHORTCUT_PHRASES = (
    "ตอนนี้โปรเจ็คทำ",
    "ตอนนี้ทำอะไรอยู่",
    "ทำ issue ไหนอยู่",
    "current work",
    "current status",
)
# ------------------------------------------

# Cache build info at startup
_BUILD_INFO_CACHE = None

def get_build_info() -> str:
    global _BUILD_INFO_CACHE
    if _BUILD_INFO_CACHE:
        return _BUILD_INFO_CACHE

    # Version
    version = "Unknown"
    version_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "VERSION")
    if os.path.exists(version_file):
        with open(version_file, "r") as f:
            version = f.read().strip()

    # Time (Server Startup time)
    built_at = datetime.now().astimezone().isoformat()

    # Git Hash
    git_hash = "Unknown"
    try:
        git_hash = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], 
            cwd=os.path.dirname(os.path.abspath(__file__)),
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
    except Exception:
        pass

    _BUILD_INFO_CACHE = f"🤖 Version {version}\n🌍 Env {settings.ENVIRONMENT}\n🏗️ Built at {built_at}\n🔗 Commit {git_hash}"
    return _BUILD_INFO_CACHE


async def _send_response(chat_id: int, text: str) -> None:
    """Helper สำหรับส่งข้อความพร้อมเติม Local Dev Info ถ้าอยู่ในโหมด development"""
    final_text = text
    if settings.ENVIRONMENT == "development":
        build_info = get_build_info()
        final_text = f"{text}\n\n---\n*Local Dev Info*\n{build_info}"
    
    # Chunk the text to fit Telegram's 4096 character limit
    # Safe chunk size of 4000 characters, using smart markdown chunking
    chunks = split_markdown_message(final_text, max_length=4000)
    
    for chunk in chunks:
        # Escape MarkdownV2 special characters before sending
        escaped_text = escape_markdown_v2(chunk)
        
        try:
            await tg_service.send_message(chat_id, escaped_text)
        except httpx.HTTPStatusError as e:
            if e.response is not None and e.response.status_code == 400:
                logger.warning(f"MarkdownV2 parse failed for {chat_id}, falling back to plain text: {e}")
                try:
                    await tg_service.send_message(chat_id, chunk, parse_mode=None)
                except Exception as fallback_err:
                    logger.error(f"Plain text fallback also failed for {chat_id}: {fallback_err}")
            else:
                logger.error(f"HTTP error sending to Telegram for {chat_id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error sending to Telegram for {chat_id}: {e}")
            logger.debug(f"Failed message content: {chunk[:200]}...")


async def _send_escaped_response(chat_id: int, text: str) -> None:
    """
    Helper สำหรับส่งข้อความที่ escape แล้วโดยตรง (ไม่ผ่าน send_message)
    ใช้สำหรับ error messages ที่มีอักขระพิเศษเยอะ เช่น `_`, `*`, `[]`
    
    NOTE: ไม่ลบ function นี้ตาม code review suggestion เพราะ:
    - escape_markdown_v2() ไม่ escape `_` (underscore) เพื่อ preserve italic formatting
    - แต่ `_` ใน command names เช่น 'delete_all', 'run_task' ทำให้ Telegram ตีความเป็น italic ผิด
    - ส่งผลให้ได้ 400 Bad Request เวลาส่ง error messages ที่มี command names
    - Function นี้ใช้ escape_markdown_v2_content() ที่ escape ทุกอย่างรวมถึง `_` และ `*`
    """
    # Escape ALL special characters including _ and *
    safe_text = escape_markdown_v2_content(text)
    
    if settings.ENVIRONMENT == "development":
        build_info = get_build_info()
        safe_build = escape_markdown_v2_content(build_info)
        safe_text = f"{safe_text}\n\n\\-\\-\\-\n*Local Dev Info*\n{safe_build}"
    
    try:
        await tg_service.client.post(
            f"{tg_service.api_url}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": safe_text,
                "parse_mode": "MarkdownV2",
            },
            timeout=10.0,
        )
    except Exception as e:
        logger.error(f"Unexpected error sending escaped message to Telegram for {chat_id}: {e}")


async def _check_telegram_rate_limit(message: "Message") -> bool:
    """Check inbound Telegram message rate limits before command or LLM handling."""
    identifier = (
        message.from_user.id
        if message.from_user is not None
        else message.chat.id
    )

    try:
        allowed, retry_after = await rate_limiter.check_telegram_message_rate_limit(
            identifier
        )
    except Exception as e:
        logger.warning(f"Telegram rate-limit check failed for {identifier}: {e}")
        return True

    if allowed:
        return True

    await _send_response(
        message.chat.id,
        f"⏳ คุณส่งข้อความถี่เกินไป กรุณารอสักครู่แล้วลองใหม่อีกครั้งใน {retry_after} วินาที",
    )
    return False


async def handle_chat_message(update: Update) -> None:
    # 1. จัดการ Message ปกติ
    if update.message and update.message.text:
        if update.message.from_user:
            try:
                await redis_service.set_user_chat_id_mapping(
                    user_id=update.message.from_user.id,
                    chat_id=update.message.chat.id
                )
            except Exception as e:
                logger.warning(f"Failed to set user_chat_id mapping for user {update.message.from_user.id}: {e}")

        if not await _check_telegram_rate_limit(update.message):
            return

        if update.message.text.startswith("/"):
            await _handle_command(update.message)
        else:
            await _handle_standard_message(update.message)
        return

    # 2. จัดการ Callback Query (ปุ่มกด)
    if update.callback_query:
        await _handle_callback_query(update.callback_query)
        return


async def _handle_command(message: "Message") -> None:
    chat_id = message.chat.id
    parts = message.text.split()
    raw_cmd = parts[0].lower()
    cmd = COMMAND_ALIASES.get(raw_cmd, raw_cmd)
    args = parts[1:] if len(parts) > 1 else []
    
    if cmd == "/model":
        await _handle_model_command(chat_id, args)
    elif cmd == "/project":
        await _handle_project_command(chat_id, args)
    elif cmd == "/projects":
        await _handle_projects_command(chat_id, args)
    elif cmd == "/note" and len(parts) > 1:
        await _handle_note_command(chat_id, args)
    elif cmd == "/github":
        await _handle_github_command(chat_id, args)
    elif cmd == "/gemini":
        await _handle_gemini_command(message, args)
    elif cmd == "/queue":
        await _handle_queue_command(message, args)
    elif cmd == "/testsource":
        await _handle_testsource_command(chat_id, args)
    else:
        await _send_response(chat_id, f"❌ Unknown command: {cmd}")

async def _handle_testsource_command(chat_id: int, args: list[str]) -> None:
    """
    Developer utility: trigger a Task Notification directly from Telegram to
    verify source mapping / formatting without calling the HTTP API.
    """
    if not args:
        await _send_response(
            chat_id,
            "🧪 Usage: `/testsource <source>`\nExamples:\n"
            "• `/testsource Cursor`\n"
            "• `/testsource Windsurf`\n"
            "• `/testsource Codex`\n"
            "• `/testsource Antigravity`\n"
            "• `/testsource Luma`",
        )
        return

    source = " ".join(args).strip()
    project = None
    try:
        project = await redis_service.get_current_project(chat_id)
    except Exception:
        project = "General"

    req = TaskNotificationRequest(
        project=project or "General",
        task="Manual verify source mapping",
        status="success",
        source=source,
        chat_id=str(chat_id),
    )

    # send_task_notification() builds a pre-escaped MarkdownV2 payload; call it
    # directly to avoid double escaping via _send_response().
    await tg_service.send_task_notification(chat_id=chat_id, request=req)


async def _handle_queue_command(message: "Message", args: list[str]) -> None:
    if len(args) < 2:
        await _send_response(
            message.chat.id,
            "❌ Usage: `/queue <tool> <command> [args_json]` (alias: `/q`)",
        )
        return

    tool = args[0]
    command = args[1]
    payload_str = " ".join(args[2:]) if len(args) > 2 else "{}"

    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError:
        await _send_response(message.chat.id, "❌ Invalid JSON payload.")
        return

    if not isinstance(payload, dict):
        await _send_response(message.chat.id, "❌ Payload must be a JSON object.")
        return

    await _enqueue_telegram_command(message, tool, command, payload)


async def _resolve_queued_command_context(chat_id: int, tool: str) -> dict[str, Optional[str]]:
    context = {
        "project_name": None,
        "cwd": None,
        "note": None,
    }

    if tool.strip().lower() != "gemini":
        return context

    try:
        project_name = await redis_service.get_current_project(chat_id)
    except Exception as exc:
        logger.warning(f"Failed to resolve current project for queued {tool} command: {exc}")
        return context

    if not project_name:
        return context

    context["project_name"] = project_name

    try:
        project_path = await redis_service.get_project_path(chat_id, project_name)
    except Exception as exc:
        logger.warning(
            f"Failed to resolve bound project path for queued {tool} command on {project_name}: {exc}"
        )
        context["note"] = (
            f"Project `{project_name}` could not resolve a bound path. "
            "Gemini will use the daemon default cwd."
        )
        return context

    if project_path:
        context["cwd"] = project_path
        return context

    context["note"] = (
        f"Project `{project_name}` has no bound path yet. "
        "Gemini will use the daemon default cwd."
    )
    return context


async def _enqueue_telegram_command(
    message: "Message",
    tool: str,
    command: str,
    payload: dict,
) -> None:
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else 0

    context = await _resolve_queued_command_context(chat_id, tool)
    request_kwargs = {
        "tool": tool,
        "command": command,
        "args": payload,
    }
    if context["cwd"]:
        request_kwargs["cwd"] = context["cwd"]

    allowed, retry_after = await command_queue_service.check_rate_limit(user_id)
    if not allowed:
        await _send_response(chat_id, f"❌ Rate limit exceeded. Retry after {retry_after}s.")
        return

    try:
        request = CommandQueueRequest(**request_kwargs)
        result = await command_queue_service.enqueue_command(
            request,
            user_id=user_id,
            chat_id=chat_id
        )
        safe_tool = escape_markdown_v2_content(tool)
        safe_command = escape_markdown_v2_content(command)
        lines = [
            "⏳ *Command Enqueued*",
            f"ID: `{result.command_id}`",
            f"Tool: {safe_tool}",
            f"Command: {safe_command}",
        ]
        if context["project_name"]:
            safe_project = escape_markdown_v2_content(context["project_name"])
            lines.append(f"Project: `{safe_project}`")
        if result.cwd:
            safe_cwd = escape_markdown_v2_content(result.cwd)
            lines.append(f"CWD: `{safe_cwd}`")
        elif context["note"]:
            safe_note = escape_markdown_v2_content(context["note"])
            lines.append(f"Note: {safe_note}")
        msg = "\n".join(lines)
        await _send_response(chat_id, msg)
    except ValueError as e:
        await _send_escaped_response(chat_id, f"❌ {e}")
    except ConnectionError:
        await _send_response(chat_id, "❌ Queue service unavailable.")
    except Exception as e:
        logger.error(f"Error enqueuing command from Telegram: {e}")
        await _send_response(chat_id, "❌ Internal error.")


async def _handle_gemini_command(message: "Message", args: list[str]) -> None:
    chat_id = message.chat.id

    if not args:
        await _send_response(
            chat_id,
            "\n".join(
                [
                    "🧠 *Gemini CLI Commands*",
                    "• `/gemini status [model] [fallback_model]`",
                    "• `/gemini <task>`",
                    "",
                    "Akasa will use the active project's bound path as `cwd` when available.",
                    "Tip: bind the project first with `/project bind <absolute_path>`.",
                ]
            ),
        )
        return

    sub_cmd = args[0].lower()
    if sub_cmd in {"status", "check_status"}:
        payload = {}
        if len(args) > 1:
            payload["model"] = args[1]
        if len(args) > 2:
            payload["fallback_model"] = args[2]
        await _enqueue_telegram_command(message, "gemini", "check_status", payload)
        return

    task_args = args[1:] if sub_cmd in {"run", "task"} and len(args) > 1 else args
    task_text = " ".join(task_args).strip()
    if not task_text:
        await _send_response(
            chat_id,
            "❌ Usage: `/gemini <task>` or `/gemini status [model] [fallback_model]`",
        )
        return

    await _enqueue_telegram_command(
        message,
        "gemini",
        "run_task",
        {"task": task_text},
    )

async def _handle_github_command(chat_id: int, args: list[str]) -> None:
    if not args:
        msg = "🐙 *GitHub Commands* (alias: `/gh`)\n"
        msg += "• `/gh repo <owner/repo>` - View repo info\n"
        msg += "• `/gh issues [owner/repo]` - List issues\n"
        msg += "• `/gh issue new <repo> <title> [body]` - Create issue\n"
        msg += "• `/gh pr [owner/repo]` - View PR status\n"
        msg += "• `/gh pr new <repo> <title> [body]` - Create PR\n"
        msg += "• `/gh kanban [owner/repo]` - View kanban or fallback open issues\n"
        msg += "• `/gh roadmap [owner/repo]` - Summarize `docs/ROADMAP.md`\n\n"
        msg += (
            "💡 *Tip:* If repo is omitted, Akasa first tries the project's bound GitHub repo, "
            "then the current project name. `/gh kanban` and `/gh roadmap` can also derive "
            "from the bound project path."
        )
        await _send_response(chat_id, msg)
        return

    sub_cmd = args[0].lower()
    try:
        if sub_cmd == "repo" and len(args) > 1:
            repo = github_service.get_repo_info(args[1])
            msg = f"📦 *{repo.full_name}*\n📝 {repo.description or 'No description'}\n⭐ Stars: {repo.stargazers_count}\n🔗 [View on GitHub]({repo.html_url})"
            await _send_response(chat_id, msg)
        elif sub_cmd == "issues":
            explicit_repo = args[1] if len(args) > 1 else None
            if explicit_repo and not _looks_like_repo_name(explicit_repo):
                await _send_response(chat_id, "⚠️ Please specify repository in format `owner/repo`.")
                return

            target = await _resolve_github_target(chat_id, explicit_repo=explicit_repo)
            repo_name = target.get("repo")
            if not repo_name or not _looks_like_repo_name(repo_name):
                await _send_response(
                    chat_id,
                    "⚠️ Please specify repository or bind a GitHub repo first, for example `/project repo akasa owner/repo`.",
                )
                return
            issues = github_service.list_issues(repo_name)
            if not issues:
                await _send_response(chat_id, f"✅ No open issues found for `{repo_name}`")
                return
            msg = f"🎯 *Open Issues for {repo_name}:*\n"
            for issue in issues:
                msg += f"• #{issue.number} {issue.title} ([link]({issue.url}))\n"
            await _send_response(chat_id, msg)
        elif sub_cmd == "issue" and len(args) > 3 and args[1] == "new":
            url = github_service.create_issue(args[2], args[3], " ".join(args[4:]) if len(args) > 4 else "Created via Akasa Bot")
            await _send_response(chat_id, f"✅ Issue created: {url}")
        elif sub_cmd == "pr":
            if len(args) > 1 and args[1] == "new" and len(args) > 3:
                url = github_service.pr_create(args[2], args[3], " ".join(args[4:]) if len(args) > 4 else "Created via Akasa Bot")
                await _send_response(chat_id, f"✅ Pull Request created: {url}")
            else:
                explicit_repo = args[1] if len(args) > 1 else None
                if explicit_repo and not _looks_like_repo_name(explicit_repo):
                    await _send_response(chat_id, "⚠️ Please specify repository in format `owner/repo`.")
                    return

                target = await _resolve_github_target(chat_id, explicit_repo=explicit_repo)
                repo_name = target.get("repo")
                if not repo_name or not _looks_like_repo_name(repo_name):
                    await _send_response(
                        chat_id,
                        "⚠️ Please specify repository or bind a GitHub repo first, for example `/project repo akasa owner/repo`.",
                    )
                    return
                prs = github_service.get_pr_status(repo_name)
                if not prs:
                    await _send_response(chat_id, f"✅ No active PRs found for `{repo_name}`")
                    return
                msg = f"🔀 *PR Status for {repo_name}:*\n"
                for pr in prs:
                    status = "🛠️ Draft" if pr.is_draft else "🚀 Active"
                    msg += f"• #{pr.number} {pr.title} ({status}) [link]({pr.url})\n"
                await _send_response(chat_id, msg)
        elif sub_cmd == "kanban":
            explicit_repo = args[1] if len(args) > 1 else None
            if explicit_repo and not _looks_like_repo_name(explicit_repo):
                await _send_response(chat_id, "⚠️ Please specify repository in format `owner/repo`.")
                return

            target = await _resolve_github_target(chat_id, explicit_repo=explicit_repo)
            repo_name = target.get("repo")
            if not repo_name or not _looks_like_repo_name(repo_name):
                await _send_response(
                    chat_id,
                    "⚠️ Please specify repository or bind a GitHub repo first, for example `/project repo akasa owner/repo` or `/gh kanban owner/repo`.",
                )
                return

            summary = github_service.get_repo_kanban_summary(repo_name)
            await _send_response(chat_id, _render_kanban_summary(summary))
        elif sub_cmd == "roadmap":
            explicit_repo = args[1] if len(args) > 1 else None
            if explicit_repo and not _looks_like_repo_name(explicit_repo):
                await _send_response(chat_id, "⚠️ Please specify repository in format `owner/repo`.")
                return

            target = await _resolve_github_target(chat_id, explicit_repo=explicit_repo)
            try:
                summary = _load_roadmap_summary(
                    repo=target.get("repo"),
                    project_name=target.get("project_name", "current project"),
                    project_path=target.get("roadmap_project_path"),
                )
            except GitHubServiceError as e:
                await _send_response(chat_id, f"⚠️ {str(e)}")
                return

            await _send_response(chat_id, _render_roadmap_summary(summary))
        else:
            await _send_response(chat_id, f"❌ Invalid GitHub command or missing arguments.")
    except Exception as e:
        await _send_response(chat_id, f"❌ GitHub Error: {str(e)}")


async def _handle_note_command(chat_id: int, args: list[str]) -> None:
    note_text = " ".join(args)
    current_project = await redis_service.get_current_project(chat_id)
    agent_state = await redis_service.get_agent_state(chat_id, current_project) or AgentState()
    agent_state.current_task = note_text
    agent_state.last_activity_timestamp = datetime.now(timezone.utc)
    await redis_service.set_agent_state(chat_id, current_project, agent_state)
    await _send_response(chat_id, f"✅ Note saved for project: `{current_project}`")


async def _handle_model_command(chat_id: int, args: list[str]) -> None:
    available_models = settings.AVAILABLE_MODELS
    if not args:
        current_pref = await redis_service.get_user_model_preference(chat_id)
        if current_pref:
            model_name = current_pref
            for alias, info in available_models.items():
                if info["identifier"] == current_pref:
                    model_name = info["name"]
                    break
        else:
            default_id = settings.LLM_MODEL
            model_name = default_id
            for alias, info in available_models.items():
                if info["identifier"] == default_id:
                    model_name = info["name"]
                    break
            model_name = f"{model_name} (default)"
        message = f"❇️ Current model: `{model_name}`\n\nTo switch, use `/model <alias>`:\n"
        for alias, info in available_models.items():
            message += f"- `{alias}`: {info['name']}\n"
        await _send_response(chat_id, message)
        return
    alias = args[0].lower()
    if alias in available_models:
        await redis_service.set_user_model_preference(chat_id, available_models[alias]["identifier"])
        await _send_response(chat_id, f"✅ Model selection updated to: {available_models[alias]['name']}")
    else:
        message = f"❌ Invalid model '{alias}'.\nAvailable models:\n"
        for a in available_models.keys():
            message += f"- `{a}`\n"
        await _send_response(chat_id, message)


def _resolve_project_bind_target_and_path(
    current_project: str,
    args: list[str],
) -> tuple[str, str]:
    """
    Parse `/project bind` arguments.

    Supported forms:
    - `/project bind <name> <absolute_path>`
    - `/project bind <absolute_path>` (bind current project)
    """
    if not args:
        raise ValueError("missing bind arguments")

    second = args[0]
    if len(args) == 1 and not (second.startswith("/") or second.startswith("~")):
        raise ValueError("missing project path")

    if second.startswith("/") or second.startswith("~"):
        target_project = current_project
        raw_path = " ".join(args)
    else:
        target_project = second.lower()
        raw_path = " ".join(args[1:])

    raw_path = raw_path.strip()
    if not raw_path:
        raise ValueError("missing project path")

    return target_project, raw_path


def _looks_like_repo_name(value: Optional[str]) -> bool:
    if not value or "/" not in value:
        return False
    owner, repo = value.split("/", 1)
    return bool(owner.strip() and repo.strip())


async def _get_project_repo_binding(chat_id: int, project_name: Optional[str]) -> Optional[str]:
    if not project_name:
        return None

    try:
        repo_name = await redis_service.get_project_repo(chat_id, project_name)
    except Exception as e:
        logger.warning(f"Failed to resolve bound GitHub repo for {project_name}: {e}")
        return None

    return repo_name if _looks_like_repo_name(repo_name) else None


async def _resolve_github_target(
    chat_id: int,
    explicit_repo: Optional[str] = None,
    current_project: Optional[str] = None,
) -> dict:
    target_project = current_project or await redis_service.get_current_project(chat_id)
    project_repo = await _get_project_repo_binding(chat_id, target_project)

    project_path = None
    try:
        project_path = await redis_service.get_project_path(chat_id, target_project)
    except Exception as e:
        logger.warning(f"Failed to resolve project path for {target_project}: {e}")

    current_project_repo = target_project if _looks_like_repo_name(target_project) else None

    repo_from_path = None
    if project_path:
        try:
            repo_from_path = github_service.get_repo_from_local_path(project_path)
        except Exception as e:
            logger.warning(f"Failed to resolve repo from path {project_path}: {e}")

    normalized_explicit_repo = (explicit_repo or "").strip() or None
    resolved_repo = normalized_explicit_repo
    repo_source = "explicit" if normalized_explicit_repo else None

    if not resolved_repo and project_repo:
        resolved_repo = project_repo
        repo_source = "bound_repo"

    if not resolved_repo and current_project_repo:
        resolved_repo = current_project_repo
        repo_source = "current_project"

    if not resolved_repo and repo_from_path:
        resolved_repo = repo_from_path
        repo_source = "bound_path"

    roadmap_project_path = None
    if project_path:
        target_roadmap_repo = normalized_explicit_repo or project_repo
        if target_roadmap_repo:
            if repo_from_path and repo_from_path.lower() == target_roadmap_repo.lower():
                roadmap_project_path = project_path
        else:
            roadmap_project_path = project_path

    return {
        "project_name": target_project,
        "project_path": project_path,
        "project_repo": project_repo,
        "repo": resolved_repo,
        "repo_source": repo_source or "unresolved",
        "repo_from_path": repo_from_path,
        "roadmap_project_path": roadmap_project_path,
    }


def _summarize_roadmap_content(content: str, max_sections: int = 5) -> list[str]:
    raw_lines = [line.rstrip() for line in content.splitlines()]
    sections: list[dict] = []
    current_section: Optional[dict] = None

    def flush_current_section():
        if current_section and current_section.get("title"):
            sections.append(current_section.copy())

    for raw_line in raw_lines:
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            title = line[level:].strip()
            if level == 1:
                continue
            flush_current_section()
            current_section = {"title": title, "lines": []}
            continue

        if current_section is None:
            current_section = {"title": "Highlights", "lines": []}

        current_section["lines"].append(line)

    flush_current_section()

    summary_lines: list[str] = []
    for section in sections:
        title = str(section["title"]).strip()
        lines = section.get("lines", [])
        complete = sum("✅" in line for line in lines)
        todo = sum("🔲" in line for line in lines)
        in_progress = sum(
            ("🟡" in line) or ("in progress" in line.lower()) or ("running" in line.lower())
            for line in lines
        )

        status_parts = []
        if complete:
            status_parts.append(f"{complete} complete")
        if in_progress:
            status_parts.append(f"{in_progress} in progress")
        if todo:
            status_parts.append(f"{todo} todo")

        if status_parts:
            summary_lines.append(f"{title} — {', '.join(status_parts)}")
            continue

        bullet_line = next(
            (
                line.lstrip("-*0123456789. ").strip()
                for line in lines
                if line.startswith(("-", "*")) or line[:1].isdigit()
            ),
            None,
        )
        if bullet_line:
            summary_lines.append(f"{title} — {bullet_line}")
            continue

        text_line = next(
            (
                line.replace("|", " ").strip()
                for line in lines
                if set(line) != {"-"} and not line.startswith("|---")
            ),
            None,
        )
        if text_line:
            compact = " ".join(text_line.split())
            summary_lines.append(f"{title} — {compact[:90]}")

        if len(summary_lines) >= max_sections:
            break

    if summary_lines:
        return summary_lines[:max_sections]

    fallback_lines = []
    for line in raw_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("|---"):
            continue
        fallback_lines.append(" ".join(stripped.replace("|", " ").split()))
        if len(fallback_lines) >= max_sections:
            break
    return fallback_lines


def _render_kanban_summary(summary: dict) -> str:
    repo = summary.get("repo", "unknown/repo")
    lines = [f"🗂️ *Kanban for {repo}*"]

    if summary.get("source") == "project":
        lines.append(f"Board: *{summary.get('project_title', 'GitHub Project')}*")
        if summary.get("selection_note"):
            lines.append(summary["selection_note"])

        columns = summary.get("columns", [])
        if not columns:
            lines.append("No linked project items found.")
        else:
            for column in columns[:5]:
                items = column.get("items", [])
                item_parts = []
                for item in items[:2]:
                    prefix = f"#{item['number']}" if item.get("number") else "item"
                    item_parts.append(f"{prefix} {item.get('title', 'Untitled')}")
                if item_parts:
                    lines.append(
                        f"• {column.get('name', 'Open')}: {column.get('count', 0)} — "
                        + "; ".join(item_parts)
                    )
                else:
                    lines.append(f"• {column.get('name', 'Open')}: {column.get('count', 0)}")

        if summary.get("project_url"):
            lines.append(f"🔗 [View project]({summary['project_url']})")
        return "\n".join(lines)

    lines.append("Source: open issues fallback")
    issues = summary.get("issues", [])
    if not issues:
        lines.append("No open issues found.")
        return "\n".join(lines)

    lines.append(f"Open issues: {len(issues)}")
    for issue in issues[:5]:
        lines.append(f"• #{issue.get('number')} {issue.get('title')}")
    lines.append(f"🔗 [View issues](https://github.com/{repo}/issues)")
    return "\n".join(lines)


def _render_roadmap_summary(summary: dict) -> str:
    display_name = summary.get("repo") or summary.get("project_name") or "current project"
    lines = [f"🗺️ *Roadmap for {display_name}*"]

    if summary.get("source") == "local":
        lines.append("Source: local `docs/ROADMAP.md`")
    else:
        lines.append("Source: repository `docs/ROADMAP.md`")

    for line in summary.get("summary_lines", [])[:5]:
        lines.append(f"• {line}")

    if summary.get("url"):
        lines.append(f"🔗 [View ROADMAP.md]({summary['url']})")
    return "\n".join(lines)


def _load_roadmap_summary(
    repo: Optional[str],
    project_name: str,
    project_path: Optional[str],
) -> dict:
    local_error = None

    if project_path:
        try:
            _, content = github_service.get_local_roadmap_content(project_path)
            return {
                "repo": repo,
                "project_name": project_name,
                "source": "local",
                "summary_lines": _summarize_roadmap_content(content),
                "url": (
                    f"https://github.com/{repo}/blob/HEAD/docs/ROADMAP.md"
                    if repo
                    else None
                ),
            }
        except GitHubServiceError as e:
            local_error = str(e)

    if repo:
        url, content = github_service.get_remote_roadmap_content(repo)
        return {
            "repo": repo,
            "project_name": project_name,
            "source": "remote",
            "summary_lines": _summarize_roadmap_content(content),
            "url": url,
        }

    if local_error:
        raise GitHubServiceError(local_error)

    raise GitHubServiceError(
        "Could not resolve project context or docs/ROADMAP.md for the current project."
    )


def _normalize_prompt_for_shortcuts(prompt: str) -> str:
    return " ".join((prompt or "").strip().lower().split())


def _matches_shortcut_phrase(prompt: str, phrases: tuple[str, ...]) -> bool:
    normalized_prompt = _normalize_prompt_for_shortcuts(prompt)
    return any(phrase in normalized_prompt for phrase in phrases)


async def _try_handle_project_insight_shortcut(
    chat_id: int,
    prompt: str,
    current_project: str,
) -> Optional[str]:
    if _matches_shortcut_phrase(prompt, ROADMAP_SHORTCUT_PHRASES):
        target = await _resolve_github_target(chat_id, current_project=current_project)
        try:
            summary = _load_roadmap_summary(
                repo=target.get("repo"),
                project_name=target.get("project_name", current_project),
                project_path=target.get("roadmap_project_path"),
            )
        except GitHubServiceError as e:
            return f"⚠️ {str(e)}"
        return _render_roadmap_summary(summary)

    if _matches_shortcut_phrase(prompt, KANBAN_SHORTCUT_PHRASES):
        target = await _resolve_github_target(chat_id, current_project=current_project)
        repo_name = target.get("repo")
        if not repo_name or not _looks_like_repo_name(repo_name):
            return (
                "⚠️ Please specify repository or bind a GitHub repo first, "
                "for example `/project repo akasa owner/repo`."
            )
        summary = github_service.get_repo_kanban_summary(repo_name)
        return _render_kanban_summary(summary)

    if _matches_shortcut_phrase(prompt, CURRENT_WORK_SHORTCUT_PHRASES):
        target = await _resolve_github_target(chat_id, current_project=current_project)
        repo_name = target.get("repo")
        project_path = target.get("project_path") or target.get("roadmap_project_path")

        sections = []
        project_display = target.get("project_name", current_project)
        sections.append(f"📊 **Current Work Status: `{project_display}`**")

        if project_path:
            # Luma State
            luma_state = github_service.get_local_luma_state(project_path)
            if luma_state:
                phase = luma_state.get("phase", "Unknown")
                active_branch = luma_state.get("active_branch", "None")
                sections.append(f"\n💡 **Luma State**\n• Phase: `{phase}`\n• Branch: `{active_branch}`")
                
                active_issues = luma_state.get("active_issues", [])
                if active_issues:
                    sections.append("• Active Issues:")
                    for idx, issue in enumerate(active_issues[:3], 1):
                        num = issue.get("number", "?")
                        title = issue.get("title", "Unknown")
                        sections.append(f"  {idx}. #{num} - {title}")
            
            # Git History
            git_log = github_service.get_local_git_history(project_path, limit=5)
            if git_log:
                sections.append(f"\n🕰 **Recent Commits**\n```\n{git_log}\n```")

        # Kanban (In Progress)
        if repo_name and _looks_like_repo_name(repo_name):
            try:
                summary = github_service.get_repo_kanban_summary(repo_name)
                in_progress_cols = [c for c in summary.get("columns", []) if "progress" in c["name"].lower() or "doing" in c["name"].lower() or "active" in c["name"].lower()]
                if not in_progress_cols and summary.get("columns"):
                    in_progress_cols = summary.get("columns")[:1]

                sections.append(f"\n📋 **Kanban ({repo_name})**")
                for col in in_progress_cols:
                    sections.append(f"*{col['name']}* ({col['count']})")
                    for item in col.get("items", []):
                        title = item.get("title", "")
                        num_text = f"[#{item['number']}]({item['url']})" if item.get("number") and item.get("url") else ""
                        sections.append(f"• {num_text} {title}".strip())
                    if col["count"] > len(col.get("items", [])):
                        sections.append("  ... (more hidden)")
            except Exception as e:
                logger.error(f"Failed to load kanban for current work: {e}")
                sections.append(f"\n📋 **Kanban**\n⚠️ Failed to load kanban: {e}")
        else:
            sections.append("\n📋 **Kanban**\n⚠️ Repository not bound. Cannot fetch GitHub board.")

        final_response = "\n".join(sections)
        return escape_markdown_v2(final_response)

    return None


async def _handle_project_command(chat_id: int, args: list[str]) -> None:
    if not args or args[0].lower() == "list":
        current = await redis_service.get_current_project(chat_id)
        projects = await redis_service.get_project_list(chat_id)
        ordered_projects = [current] + sorted(
            [project for project in projects if project != current]
        )
        msg = f"📁 Current Project: `{current}`\nAlias: `/pj`\n\nAvailable Projects:\n"
        for p in ordered_projects:
            repo_name = await _get_project_repo_binding(chat_id, p)
            repo_suffix = f" → `{repo_name}`" if repo_name else ""
            msg += f"{'✅' if p == current else '-'} `{p}`{repo_suffix}\n"
        msg += (
            "\nUsage:\n"
            "• `/project list`\n"
            "• `/project select <name>`\n"
            "• `/project status [name]`\n"
            "• `/project path [name]`\n"
            "• `/project bind [name] <absolute_path>`\n"
            "• `/project repo [name] [owner/repo]`\n"
            "• `/gemini <task>`\n"
            "• `/project new <name>`\n"
            "• `/project rename <old> <new>`"
        )
        await _send_response(chat_id, msg)
        return
    sub_cmd = args[0].lower()
    if sub_cmd == "status":
        current = await redis_service.get_current_project(chat_id)
        target = args[1].lower() if len(args) > 1 else current
        await _handle_project_status_command(chat_id, target, current)
    elif sub_cmd == "path":
        current = await redis_service.get_current_project(chat_id)
        target = args[1].lower() if len(args) > 1 else current
        project_path = await redis_service.get_project_path(chat_id, target)
        if project_path:
            await _send_response(
                chat_id,
                f"📂 Project path for `{target}`:\n`{project_path}`",
            )
        else:
            await _send_response(
                chat_id,
                f"ℹ️ No folder path is bound to `{target}` yet.\nUse `/project bind {target} /absolute/path` to save one.",
            )
    elif sub_cmd == "bind":
        current = await redis_service.get_current_project(chat_id)
        try:
            target, raw_path = _resolve_project_bind_target_and_path(current, args[1:])
            bound_path = await redis_service.set_project_path(chat_id, target, raw_path)
        except ValueError as exc:
            await _send_response(
                chat_id,
                "❌ "
                + (
                    str(exc)
                    if str(exc) not in {"missing bind arguments", "missing project path"}
                    else "Usage: `/project bind <name> <absolute_path>` or `/project bind <absolute_path>` for the current project. Alias: `/pj`."
                ),
            )
            return

        await _send_response(
            chat_id,
            f"✅ Bound project `{target}` to:\n`{bound_path}`",
        )
    elif sub_cmd in {"repo", "github"}:
        current = await redis_service.get_current_project(chat_id)

        if len(args) == 1:
            target = current
            repo_name = await _get_project_repo_binding(chat_id, target)
            if repo_name:
                await _send_response(
                    chat_id,
                    f"🐙 GitHub repo for `{target}`:\n`{repo_name}`\n🔗 [View on GitHub](https://github.com/{repo_name})",
                )
            else:
                await _send_response(
                    chat_id,
                    f"ℹ️ No GitHub repo is bound to `{target}` yet.\nUse `/project repo {target} owner/repo` to save one.",
                )
            return

        if len(args) == 2 and _looks_like_repo_name(args[1]):
            target = current
            repo_value = args[1]
        elif len(args) == 2:
            target = args[1].lower()
            repo_name = await _get_project_repo_binding(chat_id, target)
            if repo_name:
                await _send_response(
                    chat_id,
                    f"🐙 GitHub repo for `{target}`:\n`{repo_name}`\n🔗 [View on GitHub](https://github.com/{repo_name})",
                )
            else:
                await _send_response(
                    chat_id,
                    f"ℹ️ No GitHub repo is bound to `{target}` yet.\nUse `/project repo {target} owner/repo` to save one.",
                )
            return
        else:
            target = args[1].lower()
            repo_value = args[2]

        if not _looks_like_repo_name(repo_value):
            await _send_response(
                chat_id,
                "❌ Usage: `/project repo <name> <owner/repo>` or `/project repo <owner/repo>` for the current project.",
            )
            return

        bound_repo = await redis_service.set_project_repo(chat_id, target, repo_value)
        await _send_response(
            chat_id,
            f"✅ Bound GitHub repo for `{target}` to:\n`{bound_repo}`\n🔗 [View on GitHub](https://github.com/{bound_repo})",
        )
    elif sub_cmd == "select" and len(args) > 1:
        target = args[1].lower()
        await redis_service.set_current_project(chat_id, target)
        agent_state = await redis_service.get_agent_state(chat_id, target)
        if agent_state and agent_state.current_task:
            await _send_response(chat_id, f"✅ Switched to project: `{target}`\n\n👋 Welcome back! Last known task:\n```{agent_state.current_task}```")
        else:
            await _send_response(chat_id, f"✅ Switched to project: `{target}`")
    elif sub_cmd == "new" and len(args) > 1:
        await redis_service.set_current_project(chat_id, args[1].lower())
        await _send_response(chat_id, f"🆕 Created and switched to project: `{args[1].lower()}`")
    elif sub_cmd == "rename" and len(args) > 2:
        await redis_service.rename_project(chat_id, args[1].lower(), args[2].lower())
        await _send_response(chat_id, f"✅ Project renamed from `{args[1].lower()}` to `{args[2].lower()}`.\n(Current project updated if needed)")
    else:
        await _send_response(chat_id, "❌ Invalid usage. Try `/project` or `/pj` for help.")


def _format_project_timestamp(value) -> Optional[str]:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _parse_project_datetime(value) -> Optional[datetime]:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value

    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _truncate_project_text(text: str, limit: int = 90) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def _build_history_snippet(history_entry: dict) -> Optional[str]:
    if not history_entry:
        return None

    role = str(history_entry.get("role", "unknown"))
    content = history_entry.get("content")
    if content is None:
        if history_entry.get("tool_calls"):
            content = "[tool calls]"
        else:
            return None

    return f"{role}: {_truncate_project_text(str(content))}"


def _format_history_count(count: int) -> str:
    suffix = "message" if count == 1 else "messages"
    return f"{count} recent {suffix}"


def _compute_last_updated(
    agent_state,
    recent_command_statuses,
    recent_deployments,
    recent_tasks,
) -> Optional[str]:
    candidates = []

    if agent_state and getattr(agent_state, "last_activity_timestamp", None):
        parsed = _parse_project_datetime(agent_state.last_activity_timestamp)
        if parsed:
            candidates.append(parsed)

    for status in recent_command_statuses:
        for value in (status.completed_at, status.picked_up_at, status.queued_at):
            parsed = _parse_project_datetime(value)
            if parsed:
                candidates.append(parsed)

    for deployment in recent_deployments:
        for value in (deployment.finished_at, deployment.started_at):
            parsed = _parse_project_datetime(value)
            if parsed:
                candidates.append(parsed)

    for task in recent_tasks:
        for value in (task.completed_at, task.started_at):
            parsed = _parse_project_datetime(value)
            if parsed:
                candidates.append(parsed)

    if not candidates:
        return None

    return max(candidates).isoformat()


async def _load_project_status_snapshot(
    chat_id: int,
    project_name: str,
    command_limit: int = 3,
    deployment_limit: int = 3,
    task_limit: int = 3,
):
    agent_state = None
    recent_command_ids = []
    recent_deployment_ids = []
    recent_tasks = []
    recent_history = []
    project_path = None
    project_repo = None
    project_repo_source = None

    try:
        agent_state = await redis_service.get_agent_state(chat_id, project_name)
    except Exception as e:
        logger.warning(f"Failed to load AgentState for project {project_name}: {e}")

    try:
        project_path = await redis_service.get_project_path(chat_id, project_name)
    except Exception as e:
        logger.warning(f"Failed to load project path for project {project_name}: {e}")

    project_repo = await _get_project_repo_binding(chat_id, project_name)
    if project_repo:
        project_repo_source = "bound_repo"
    elif _looks_like_repo_name(project_name):
        project_repo = project_name
        project_repo_source = "project_name"
    elif project_path:
        try:
            project_repo = github_service.get_repo_from_local_path(project_path)
        except Exception as e:
            logger.warning(f"Failed to derive repo from path for {project_name}: {e}")
        if project_repo:
            project_repo_source = "bound_path"

    try:
        recent_command_ids = await redis_service.get_recent_command_ids(
            chat_id, project_name, limit=command_limit
        )
    except Exception as e:
        logger.warning(f"Failed to load recent command IDs for project {project_name}: {e}")

    try:
        recent_deployment_ids = await redis_service.get_recent_deployment_ids(
            chat_id, project_name, limit=deployment_limit
        )
    except Exception as e:
        logger.warning(
            f"Failed to load recent deployment IDs for project {project_name}: {e}"
        )

    try:
        recent_tasks = await agent_task_service.get_tasks_by_project(project_name)
    except Exception as e:
        logger.warning(f"Failed to load agent tasks for project {project_name}: {e}")

    try:
        recent_history = await redis_service.get_chat_history(
            chat_id, project_name=project_name
        )
    except Exception as e:
        logger.warning(f"Failed to load chat history for project {project_name}: {e}")

    recent_command_statuses = []
    for command_id in recent_command_ids:
        try:
            status = await command_queue_service.get_command_status(command_id)
        except Exception as e:
            logger.warning(f"Failed to read command status for {command_id}: {e}")
            status = None
        if status is not None:
            recent_command_statuses.append(status)

    recent_deployments = []
    for deployment_id in recent_deployment_ids:
        try:
            deployment = await deploy_service.get_deployment(deployment_id)
        except Exception as e:
            logger.warning(f"Failed to read deployment status for {deployment_id}: {e}")
            deployment = None
        if deployment is not None:
            recent_deployments.append(deployment)

    filtered_tasks = [
        task
        for task in recent_tasks
        if not task.chat_id or task.chat_id == str(chat_id)
    ]
    filtered_tasks.sort(
        key=lambda task: task.completed_at or task.started_at or "",
        reverse=True,
    )

    history_snippet = None
    if recent_history:
        history_snippet = _build_history_snippet(recent_history[-1])

    last_updated = _compute_last_updated(
        agent_state,
        recent_command_statuses,
        recent_deployments,
        filtered_tasks,
    )

    return {
        "agent_state": agent_state,
        "project_path": project_path,
        "project_repo": project_repo,
        "project_repo_source": project_repo_source,
        "recent_command_statuses": recent_command_statuses,
        "recent_deployments": recent_deployments,
        "recent_tasks": filtered_tasks[:task_limit],
        "last_updated": last_updated,
        "history_snippet": history_snippet,
        "history_count": len(recent_history),
    }


async def _handle_project_status_command(
    chat_id: int,
    project_name: str,
    current_project: Optional[str] = None,
) -> None:
    current_project = current_project or await redis_service.get_current_project(chat_id)
    snapshot = await _load_project_status_snapshot(chat_id, project_name)
    agent_state = snapshot["agent_state"]
    project_path = snapshot["project_path"]
    project_repo = snapshot["project_repo"]
    project_repo_source = snapshot["project_repo_source"]
    recent_command_statuses = snapshot["recent_command_statuses"]
    recent_deployments = snapshot["recent_deployments"]
    filtered_tasks = snapshot["recent_tasks"]
    last_updated = snapshot["last_updated"]

    lines = [f"📊 Project Status: `{project_name}`"]
    if project_name == current_project:
        lines.append("✅ This is the active project.")
    else:
        lines.append(f"Current active project: `{current_project}`")

    if project_path:
        lines.append(f"📂 Bound path: `{project_path}`")
    else:
        lines.append("📂 Bound path: not set")

    if project_repo:
        source_label = {
            "bound_repo": "bound repo",
            "project_name": "project name",
            "bound_path": "bound path",
        }.get(project_repo_source, "resolved")
        lines.append(f"🐙 GitHub repo: `{project_repo}` ({source_label})")
        lines.append(f"🔗 [View on GitHub](https://github.com/{project_repo})")
    else:
        lines.append("🐙 GitHub repo: not set")

    lines.append("")
    if agent_state and agent_state.current_task:
        lines.append(f"📝 Current task: {agent_state.current_task}")
        if agent_state.focus_file:
            lines.append(f"📄 Focus file: `{agent_state.focus_file}`")
        last_note_update = _format_project_timestamp(agent_state.last_activity_timestamp)
        if last_note_update:
            lines.append(f"🕒 Last note update: `{last_note_update}`")
    else:
        lines.append("📝 Current task: No saved note")

    if last_updated:
        lines.append(f"🗓️ Last updated: `{last_updated}`")

    lines.append("")
    lines.append("⚙️ Recent commands:")
    if recent_command_statuses:
        for status in recent_command_statuses:
            line = (
                f"• `{status.command_id}` — `{status.tool} {status.command}` → `{status.status}`"
            )
            if status.cwd:
                line += f" @ `{status.cwd}`"
            lines.append(line)
    else:
        lines.append("• No recent command queue activity")

    lines.append("")
    lines.append("🚀 Recent deployments:")
    if recent_deployments:
        for deployment in recent_deployments:
            lines.append(
                f"• `{deployment.deployment_id}` — `{deployment.command}` → `{deployment.status}`"
            )
    else:
        lines.append("• No recent deployments")

    lines.append("")
    lines.append("🤖 Recent agent tasks:")
    if filtered_tasks:
        for task in filtered_tasks[:3]:
            source = f" ({task.source})" if task.source else ""
            lines.append(f"• `{task.status}` — {task.task}{source}")
    else:
        lines.append("• No recent agent task notifications")

    await _send_response(chat_id, "\n".join(lines))


async def _handle_projects_command(chat_id: int, args: list[str]) -> None:
    if not args or args[0].lower() != "overview":
        await _send_response(
            chat_id,
            "🗂️ Usage:\n• `/projects overview`\n• `/projects overview verbose`\n• `/projects overview markdown`\n• `/projects overview json`\n\nYou can combine options, for example: `/projects overview verbose json`",
        )
        return

    options = {arg.lower() for arg in args[1:]}
    allowed_options = {"verbose", "markdown", "json"}
    unknown_options = sorted(options - allowed_options)
    if unknown_options:
        await _send_response(
            chat_id,
            f"❌ Unknown `/projects overview` option(s): {', '.join(unknown_options)}",
        )
        return

    verbose = "verbose" in options
    output_format = "json" if "json" in options else "markdown"

    current_project = await redis_service.get_current_project(chat_id)
    projects = await redis_service.get_project_list(chat_id)
    unique_projects = []
    seen = set()
    for project in projects:
        normalized = project.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        unique_projects.append(normalized)

    unique_projects.sort()
    if current_project in unique_projects:
        unique_projects.remove(current_project)
    ordered_projects = [current_project] + unique_projects

    overview_items = []
    for project_name in ordered_projects:
        snapshot = await _load_project_status_snapshot(
            chat_id,
            project_name,
            command_limit=1,
            deployment_limit=1,
            task_limit=1,
        )
        agent_state = snapshot["agent_state"]
        recent_command_statuses = snapshot["recent_command_statuses"]
        recent_deployments = snapshot["recent_deployments"]
        recent_tasks = snapshot["recent_tasks"]
        last_updated = snapshot["last_updated"]
        history_snippet = snapshot["history_snippet"]
        history_count = snapshot["history_count"]
        project_path = snapshot["project_path"]
        project_repo = snapshot["project_repo"]
        project_repo_source = snapshot["project_repo_source"]

        latest_command = None
        if recent_command_statuses:
            status = recent_command_statuses[0]
            latest_command = {
                "command_id": status.command_id,
                "tool": status.tool,
                "command": status.command,
                "status": status.status,
            }

        latest_deployment = None
        if recent_deployments:
            deployment = recent_deployments[0]
            latest_deployment = {
                "deployment_id": deployment.deployment_id,
                "command": deployment.command,
                "status": deployment.status,
            }

        latest_agent_task = None
        if recent_tasks:
            task = recent_tasks[0]
            latest_agent_task = {
                "task_id": task.task_id,
                "task": task.task,
                "status": task.status,
                "source": task.source,
            }

        overview_items.append(
            {
                "project": project_name,
                "active": project_name == current_project,
                "task": agent_state.current_task if agent_state and agent_state.current_task else None,
                "project_path": project_path,
                "project_repo": project_repo,
                "project_repo_source": project_repo_source,
                "last_updated": last_updated,
                "history_count": history_count,
                "history_snippet": history_snippet if verbose else None,
                "latest_command": latest_command,
                "latest_deployment": latest_deployment,
                "latest_agent_task": latest_agent_task,
            }
        )

    if output_format == "json":
        payload = {
            "current_project": current_project,
            "verbose": verbose,
            "projects": overview_items,
        }
        rendered = "```json\n" + json.dumps(payload, ensure_ascii=False, indent=2) + "\n```"
        await _send_response(chat_id, rendered)
        return

    lines = ["🗂️ Projects Overview" + (" (Verbose)" if verbose else ""), ""]
    for item in overview_items:
        prefix = "✅" if item["active"] else "•"
        lines.append(f"{prefix} `{item['project']}`")
        lines.append(f"Task: {item['task'] or 'No saved note'}")
        lines.append(f"Path: `{item['project_path']}`" if item["project_path"] else "Path: none")
        lines.append(
            f"GitHub: `{item['project_repo']}`"
            if item["project_repo"]
            else "GitHub: none"
        )
        lines.append(
            f"Last updated: `{item['last_updated']}`" if item["last_updated"] else "Last updated: unknown"
        )
        lines.append(f"History count: {_format_history_count(item['history_count'])}")

        latest_command = item["latest_command"]
        if latest_command:
            lines.append(
                f"Command: `{latest_command['tool']} {latest_command['command']}` → `{latest_command['status']}`"
            )
        else:
            lines.append("Command: none")

        latest_deployment = item["latest_deployment"]
        if latest_deployment:
            lines.append(
                f"Deploy: `{latest_deployment['command']}` → `{latest_deployment['status']}`"
            )
        else:
            lines.append("Deploy: none")

        latest_agent_task = item["latest_agent_task"]
        if latest_agent_task:
            source = f" ({latest_agent_task['source']})" if latest_agent_task["source"] else ""
            lines.append(
                f"Agent: `{latest_agent_task['status']}` — {latest_agent_task['task']}{source}"
            )
        else:
            lines.append("Agent: none")

        if verbose:
            lines.append(f"History: {item['history_snippet'] or 'none'}")

        lines.append("")

    lines.append("Tip: use `/project status <name>` for full details.")
    await _send_response(chat_id, "\n".join(lines))


async def _execute_tool_call(
    function_name: str,
    arguments_str: str,
    chat_id: Optional[int] = None,
    current_project: Optional[str] = None,
) -> str:
    try:
        args = json.loads(arguments_str)
        print(f"--- [DEBUG] Executing tool: {function_name} ---")
        if function_name == "create_github_issue":
            create_kwargs = {
                "repo": args.get("repo"),
                "title": args.get("title"),
                "body": args.get("body"),
            }
            if args.get("duration"):
                create_kwargs["duration"] = args.get("duration")
            return github_service.create_issue(**create_kwargs)
        elif function_name == "list_github_open_prs":
            prs = github_service.get_pr_status(repo=args.get("repo"))
            return "\n".join([f"#{pr.number}: {pr.title} by @{pr.author.get('login') if pr.author else 'unknown'} ({pr.url})" for pr in prs]) if prs else "No open PRs."
        elif function_name == "create_github_comment":
            return github_service.create_comment(repo=args.get("repo"), issue_number=args.get("issue_number"), body=args.get("body"))
        elif function_name == "close_github_issue":
            return github_service.close_issue(repo=args.get("repo"), issue_number=args.get("issue_number"))
        elif function_name == "delete_github_issue":
            return github_service.delete_issue(repo=args.get("repo"), issue_number=args.get("issue_number"))
        elif function_name == "get_github_issue":
            issue = github_service.get_issue(repo=args.get("repo"), issue_number=args.get("issue_number"))
            return f"Issue #{issue.number}: {getattr(issue, 'title', 'No Title')}\nStatus: {getattr(issue, 'state', 'Unknown')}\nAuthor: @{issue.author.get('login') if issue.author else 'unknown'}\nURL: {issue.url}\n\nBody:\n{getattr(issue, 'body', '')}"
        elif function_name == "search_github_issues":
            issues = github_service.search_issues(repo=args.get("repo"), query=args.get("query"))
            return "\n".join([f"#{i.number}: {i.title} (@{i.author.get('login') if i.author else 'unknown'})" for i in issues]) if issues else "No issues found."
        elif function_name == "create_github_pr":
            return github_service.pr_create(repo=args.get("repo"), title=args.get("title"), body=args.get("body"), head=args.get("head"), base=args.get("base", "main"))
        elif function_name == "list_github_repos":
            repos = github_service.list_repos(owner=args.get("owner", ""), limit=args.get("limit", 30))
            if not repos:
                return "No repositories found."
            lines = []
            for r in repos:
                desc = f" — {r.description}" if r.description else ""
                stars = f" ⭐{r.stargazers_count}" if r.stargazers_count else ""
                lines.append(f"• {r.full_name}{desc}{stars}")
            return f"Found {len(repos)} repositories:\n" + "\n".join(lines)
        elif function_name == "get_github_kanban":
            explicit_repo = args.get("repo")
            if explicit_repo and not _looks_like_repo_name(explicit_repo):
                return "Error: Invalid repository format. Please use owner/repo."
            if chat_id is None:
                return "Error: Missing Telegram chat context for kanban lookup."
            target = await _resolve_github_target(
                chat_id,
                explicit_repo=explicit_repo,
                current_project=current_project,
            )
            repo_name = target.get("repo")
            if not repo_name or not _looks_like_repo_name(repo_name):
                return "Error: Could not resolve repository from the current project context."
            summary = github_service.get_repo_kanban_summary(repo_name)
            return _render_kanban_summary(summary)
        elif function_name == "get_github_roadmap":
            explicit_repo = args.get("repo")
            if explicit_repo and not _looks_like_repo_name(explicit_repo):
                return "Error: Invalid repository format. Please use owner/repo."
            if chat_id is None:
                return "Error: Missing Telegram chat context for roadmap lookup."
            target = await _resolve_github_target(
                chat_id,
                explicit_repo=explicit_repo,
                current_project=current_project,
            )
            summary = _load_roadmap_summary(
                repo=target.get("repo"),
                project_name=target.get("project_name", "current project"),
                project_path=target.get("roadmap_project_path"),
            )
            return _render_roadmap_summary(summary)
        elif function_name == "git_status":
            return github_service.git_status() or "Working tree clean."
        elif function_name == "git_add":
            return github_service.git_add(path=args.get("path", "."))
        elif function_name == "git_commit":
            return github_service.git_commit(message=args.get("message"))
        elif function_name == "git_push":
            return github_service.git_push(branch=args.get("branch", "main"))
        return f"Error: Tool {function_name} not implemented."
    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        return f"Error: {str(e)}"


async def _handle_standard_message(message: "Message") -> None:
    chat_id = message.chat.id
    prompt = message.text.strip()
    
    # 1. ดึงโปรเจ็กต์ปัจจุบัน (ทนทานต่อ Redis ล่ม)
    try:
        current_project = await redis_service.get_current_project(chat_id)
    except Exception:
        current_project = "default"

    try:
        model_pref = await redis_service.get_user_model_preference(chat_id)
    except Exception:
        model_pref = None

    # 0. Action Confirmation Handler
    if prompt.lower() in ["ยืนยัน", "ตกลง", "confirm", "yes", "จัดไป"]:
        try:
            pending_message = await redis_service.get_pending_tool_call(chat_id)
        except Exception:
            pending_message = None

        if pending_message:
            await _send_response(chat_id, "👌 กำลังดำเนินการรันคำสั่งที่รอยืนยัน...")
            try:
                await redis_service.clear_pending_tool_call(chat_id)
            except Exception:
                pass

            try:
                history = await redis_service.get_chat_history(chat_id, project_name=current_project)
            except Exception:
                history = []

            messages = [{"role": "system", "content": f"{settings.SYSTEM_PROMPT}\nYou are continuing a confirmed action."}] + history
            response = pending_message
            while isinstance(response, dict) and "tool_calls" in response:
                tool_calls = response["tool_calls"]
                if not any(msg.get("tool_calls") == tool_calls for msg in messages):
                    messages.append(response)
                for tc in tool_calls:
                    call_id = tc["id"] if hasattr(tc, "__getitem__") else tc.id
                    fname = tc["function"]["name"] if hasattr(tc, "__getitem__") else tc.function.name
                    args_str = tc["function"]["arguments"] if hasattr(tc, "__getitem__") else tc.function.arguments
                    result = await _execute_tool_call(
                        fname,
                        args_str,
                        chat_id=chat_id,
                        current_project=current_project,
                    )
                    tool_msg = {"role": "tool", "tool_call_id": call_id, "name": fname, "content": str(result)}
                    messages.append(tool_msg)
                    try:
                        await redis_service.add_message_to_history(chat_id, "tool", tool_msg, project_name=current_project)
                    except Exception:
                        pass
                response = await llm_service.get_llm_reply(messages, model=model_pref, tools=GITHUB_TOOLS)
            
            reply = response if isinstance(response, str) else "ดำเนินการเรียบร้อยแล้วครับ"
            await _send_response(chat_id, reply)
            try:
                await redis_service.add_message_to_history(chat_id, "assistant", reply, project_name=current_project)
            except Exception:
                pass
            return

    shortcut_reply = await _try_handle_project_insight_shortcut(
        chat_id,
        prompt,
        current_project,
    )
    if shortcut_reply:
        await _send_response(chat_id, shortcut_reply)
        try:
            await redis_service.add_message_to_history(chat_id, "user", prompt, project_name=current_project)
            await redis_service.add_message_to_history(chat_id, "assistant", shortcut_reply, project_name=current_project)
        except Exception:
            pass
        return

    # 1. Normal Message Handling
    try:
        history = await redis_service.get_chat_history(chat_id, project_name=current_project)
    except Exception:
        history = []

    workflow_instruction = (
        "\n\n[GIT WORKFLOW]\n"
        "If user wants a PR, call 'git_status' first. If dirty, ASK to add/commit/push first."
        "\n\n[PROJECT INSIGHTS]\n"
        "If the user asks about kanban, board status, backlog, what is in progress, "
        "what is next, current project status, roadmap, future plans, milestones, "
        "or what the project will do next, prefer the dedicated GitHub kanban/roadmap tools."
    )
    messages = [{"role": "system", "content": f"{settings.SYSTEM_PROMPT}\nProject: {current_project}{workflow_instruction}"}] + history + [{"role": "user", "content": prompt}]

    try:
        response = await llm_service.get_llm_reply(messages, model=model_pref, tools=GITHUB_TOOLS)
        while isinstance(response, dict) and "tool_calls" in response:
            tool_calls = response["tool_calls"]
            for tc in tool_calls:
                fname = tc["function"]["name"] if hasattr(tc, "__getitem__") else tc.function.name
                if fname in TOOLS_REQUIRING_CONFIRMATION:
                    try:
                        await redis_service.set_pending_tool_call(chat_id, response)
                    except Exception:
                        pass
                    args = json.loads(tc["function"]["arguments"] if hasattr(tc, "__getitem__") else tc.function.arguments)
                    await _send_response(chat_id, f"⚠️ *Akasa ต้องการการยืนยัน*\n\nรันคำสั่ง: `{fname}`\nรายละเอียด: `{args}`\n\nพิมพ์ **'ยืนยัน'** เพื่อดำเนินการ")
                    try:
                        await redis_service.add_message_to_history(chat_id, "user", prompt, project_name=current_project)
                        await redis_service.add_message_to_history(chat_id, "assistant", response, project_name=current_project)
                    except Exception:
                        pass
                    return
            messages.append(response)
            for tc in tool_calls:
                call_id = tc["id"] if hasattr(tc, "__getitem__") else tc.id
                fname = tc["function"]["name"] if hasattr(tc, "__getitem__") else tc.function.name
                args_str = tc["function"]["arguments"] if hasattr(tc, "__getitem__") else tc.function.arguments
                result = await _execute_tool_call(
                    fname,
                    args_str,
                    chat_id=chat_id,
                    current_project=current_project,
                )
                tool_msg = {"role": "tool", "tool_call_id": call_id, "name": fname, "content": str(result)}
                messages.append(tool_msg)
                try:
                    await redis_service.add_message_to_history(chat_id, "tool", tool_msg, project_name=current_project)
                except Exception:
                    pass
            response = await llm_service.get_llm_reply(messages, model=model_pref, tools=GITHUB_TOOLS)

        reply = response if isinstance(response, str) else "เรียบร้อยครับ"
        await _send_response(chat_id, reply)
        try:
            await redis_service.add_message_to_history(chat_id, "user", prompt, project_name=current_project)
            await redis_service.add_message_to_history(chat_id, "assistant", reply, project_name=current_project)
        except Exception:
            pass

    except Exception as e:
        if isinstance(e, OpenRouterInsufficientCreditsError):
            await _send_response(chat_id, "🔴 *ยอดเงินใน OpenRouter ไม่เพียงพอ*\n\nไม่สามารถใช้โมเดลปัจจุบันได้เนื่องจากยอดเงินคงเหลือหมดครับ\n\n💡 *คำแนะนำ:*\n1. เติมเงินใน OpenRouter\n2. สลับไปใช้โมเดลอื่น (เช่น Gemini ผ่าน Google SDK หรือโมเดลฟรี) โดยใช้คำสั่ง `/model`")
            return
        if isinstance(e, LLMTimeoutError):
            logger.error(f"LLM timeout: {e}")
            await _send_response(chat_id, "ขออภัย คำขอใช้เวลานานเกินไป โปรดลองใหม่อีกครั้งในอีกสักครู่ 🙇‍♂️")
            return
        if isinstance(e, LLMUpstreamError):
            logger.error(f"LLM upstream error: {e}")
            await _send_response(chat_id, "ขออภัย ระบบ AI ภายนอกขัดข้องชั่วคราว โปรดลองใหม่อีกครั้งในภายหลัง 🙇‍♂️")
            return
        if isinstance(e, LLMMalformedResponseError):
            logger.error(f"Malformed LLM response: {e}")
            await _send_response(chat_id, "ขออภัย ระบบไม่สามารถประมวลผลคำตอบจาก AI ได้ 🙇‍♂️")
            return
        
        # Avoid mock related errors
        if "not inherit from BaseException" in str(e):
            raise e

        if isinstance(e, (httpx.TimeoutException, httpx.HTTPError)):
            logger.error(f"API Error: {e}")
            await _send_response(chat_id, "ขออภัย ระบบขัดข้องชั่วคราวในการตอบสนอง 🙇‍♂️")
        elif isinstance(e, (ValueError, KeyError, TypeError)):
            logger.error(f"Malformed LLM response: {e}")
            await _send_response(chat_id, "ขออภัย ระบบไม่สามารถประมวลผลคำตอบได้ 🙇‍♂️")
        else:
            logger.exception("Error in standard message")
            await _send_response(chat_id, "ขออภัย เกิดข้อผิดพลาดที่ไม่คาดคิด โปรดลองอีกครั้งในภายหลัง")


async def _handle_callback_query(callback: CallbackQuery) -> None:
    """จัดการการกดปุ่ม Inline Keyboard สำหรับการยืนยัน Action"""
    data = callback.data or ""
    if not data.startswith("confirm:"):
        return

    # format: confirm:<request_id>:<decision>
    parts = data.split(":")
    if len(parts) < 3:
        return

    request_id = parts[1]
    decision = parts[2]  # allow | session | deny
    
    # 1. ดึงสถานะปัจจุบันจาก Redis
    state = await redis_service.get_action_request(request_id)
    if not state or state.status != "pending":
        # ถ้าไม่มีใน Redis หรือตัดสินไปแล้ว
        return

    # 2. อัปเดตสถานะ
    user_name = callback.from_user.username or callback.from_user.first_name
    state.decided_by = user_name
    state.decided_at = datetime.now(timezone.utc)
    
    status_text = ""
    if decision == "allow":
        state.status = "allowed"
        status_text = "✅ Allowed"
    elif decision == "session":
        state.status = "allowed"
        status_text = "🛡️ Allowed for Session"
        # บันทึกสิทธิ์ session (1 ชม.)
        if state.session_id:
            await redis_service.set_session_permission(state.session_id)
    elif decision == "deny":
        state.status = "denied"
        status_text = "❌ Denied"

    # 3. บันทึกกลับลง Redis
    await redis_service.set_action_request(request_id, state)
    
    # 4. อัปเดตข้อความใน Telegram (Edit Message เพื่อเอาปุ่มออก)
    if callback.message:
        chat_id = callback.message.chat.id
        msg_id = callback.message.message_id

        # IMPORTANT:
        # - callback.message.text may contain unescaped characters (or already-escaped text).
        # - To avoid MarkdownV2 parse failures, rebuild the message from the stored state
        #   and escape only dynamic content.
        safe_cwd = escape_markdown_v2_content(state.cwd)
        safe_command = escape_markdown_v2_content(state.command)
        safe_user = escape_markdown_v2_content(user_name)
        safe_status = escape_markdown_v2_content(status_text)

        lines = [
            "🤖 *Action Confirmation*",
            "",
            f"📂 `{safe_cwd}`",
            f"💻 `{safe_command}`",
        ]
        if state.description:
            safe_desc = escape_markdown_v2_content(state.description)
            lines += ["", f"📝 {safe_desc}"]

        lines += ["", f"{safe_status} by {safe_user}"]
        new_text = "\n".join(lines)

        await tg_service.edit_message_text(
            chat_id=chat_id,
            message_id=msg_id,
            text=new_text,
            reply_markup=None  # เอาปุ่มออก
        )
