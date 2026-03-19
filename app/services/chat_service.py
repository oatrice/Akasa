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
    cmd = parts[0].lower()
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
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else 0
    
    if len(args) < 2:
        await _send_response(chat_id, "❌ Usage: `/queue <tool> <command> [args_json]`")
        return
        
    tool = args[0]
    command = args[1]
    payload_str = " ".join(args[2:]) if len(args) > 2 else "{}"
    
    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError:
        await _send_response(chat_id, "❌ Invalid JSON payload.")
        return
        
    request = CommandQueueRequest(
        tool=tool,
        command=command,
        args=payload
    )
    
    # Check rate limit
    allowed, retry_after = await command_queue_service.check_rate_limit(user_id)
    if not allowed:
        await _send_response(chat_id, f"❌ Rate limit exceeded. Retry after {retry_after}s.")
        return
        
    try:
        result = await command_queue_service.enqueue_command(
            request, 
            user_id=user_id, 
            chat_id=chat_id
        )
        safe_tool = escape_markdown_v2_content(tool)
        safe_command = escape_markdown_v2_content(command)
        msg = f"⏳ *Command Enqueued*\nID: `{result.command_id}`\nTool: {safe_tool}\nCommand: {safe_command}"
        await _send_response(chat_id, msg)
    except ValueError as e:
        await _send_escaped_response(chat_id, f"❌ {e}")
    except ConnectionError:
        await _send_response(chat_id, "❌ Queue service unavailable.")
    except Exception as e:
        logger.error(f"Error enqueuing command from Telegram: {e}")
        await _send_response(chat_id, "❌ Internal error.")

async def _handle_github_command(chat_id: int, args: list[str]) -> None:
    if not args:
        msg = "🐙 *GitHub Commands:*\n"
        msg += "• `/github repo <owner/repo>` - View repo info\n"
        msg += "• `/github issues [owner/repo]` - List issues\n"
        msg += "• `/github issue new <repo> <title> [body]` - Create issue\n"
        msg += "• `/github pr [owner/repo]` - View PR status\n"
        msg += "• `/github pr new <repo> <title> [body]` - Create PR\n\n"
        msg += "💡 *Tip:* If repo is omitted, it uses the current project name."
        await _send_response(chat_id, msg)
        return

    sub_cmd = args[0].lower()
    try:
        if sub_cmd == "repo" and len(args) > 1:
            repo = github_service.get_repo_info(args[1])
            msg = f"📦 *{repo.full_name}*\n📝 {repo.description or 'No description'}\n⭐ Stars: {repo.stargazers_count}\n🔗 [View on GitHub]({repo.html_url})"
            await _send_response(chat_id, msg)
        elif sub_cmd == "issues":
            repo_name = args[1] if len(args) > 1 else await redis_service.get_current_project(chat_id)
            if not repo_name or "/" not in repo_name:
                await _send_response(chat_id, "⚠️ Please specify repository in format `owner/repo` or select a project that matches a repo name.")
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
                repo_name = args[1] if len(args) > 1 else await redis_service.get_current_project(chat_id)
                if not repo_name or "/" not in repo_name:
                    await _send_response(chat_id, "⚠️ Please specify repository in format `owner/repo`.")
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


async def _handle_project_command(chat_id: int, args: list[str]) -> None:
    if not args:
        current = await redis_service.get_current_project(chat_id)
        projects = await redis_service.get_project_list(chat_id)
        msg = f"📁 Current Project: `{current}`\n\nAvailable Projects:\n"
        for p in projects:
            msg += f"{'✅' if p == current else '-'} `{p}`\n"
        msg += "\nUsage:\n• `/project select <name>`\n• `/project status [name]`\n• `/project new <name>`\n• `/project rename <old> <new>`"
        await _send_response(chat_id, msg)
        return
    sub_cmd = args[0].lower()
    if sub_cmd == "status":
        current = await redis_service.get_current_project(chat_id)
        target = args[1].lower() if len(args) > 1 else current
        await _handle_project_status_command(chat_id, target, current)
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
        await _send_response(chat_id, "❌ Invalid usage. Try `/project` for help.")


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

    try:
        agent_state = await redis_service.get_agent_state(chat_id, project_name)
    except Exception as e:
        logger.warning(f"Failed to load AgentState for project {project_name}: {e}")

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
    recent_command_statuses = snapshot["recent_command_statuses"]
    recent_deployments = snapshot["recent_deployments"]
    filtered_tasks = snapshot["recent_tasks"]
    last_updated = snapshot["last_updated"]

    lines = [f"📊 Project Status: `{project_name}`"]
    if project_name == current_project:
        lines.append("✅ This is the active project.")
    else:
        lines.append(f"Current active project: `{current_project}`")

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
            lines.append(
                f"• `{status.command_id}` — `{status.tool} {status.command}` → `{status.status}`"
            )
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


async def _execute_tool_call(function_name: str, arguments_str: str) -> str:
    try:
        args = json.loads(arguments_str)
        print(f"--- [DEBUG] Executing tool: {function_name} ---")
        if function_name == "create_github_issue":
            return github_service.create_issue(repo=args.get("repo"), title=args.get("title"), body=args.get("body"))
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
                    result = await _execute_tool_call(fname, args_str)
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

    # 1. Normal Message Handling
    try:
        history = await redis_service.get_chat_history(chat_id, project_name=current_project)
    except Exception:
        history = []

    workflow_instruction = "\n\n[GIT WORKFLOW]\nIf user wants a PR, call 'git_status' first. If dirty, ASK to add/commit/push first."
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
                result = await _execute_tool_call(fname, args_str)
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
