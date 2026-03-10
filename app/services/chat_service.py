"""
Chat Service — ประสานงานระหว่าง Telegram, Redis, และ LLM

Flow: Telegram → ดึง history จาก Redis → สร้าง messages context → LLM → บันทึก history → ส่งกลับ Telegram
Graceful degradation: ถ้า Redis ล่ม ยังทำงานได้เป็น stateless
"""

from app.models.telegram import Update, Message
from app.models.agent_state import AgentState
from app.services import llm_service, redis_service
from app.services.telegram_service import tg_service
from app.services.github_service import GitHubService, GitHubServiceError, GitHubAuthError
import httpx
import logging
import os
import subprocess
import json
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

    version = "Unknown"
    version_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "VERSION")
    if os.path.exists(version_file):
        with open(version_file, "r") as f:
            version = f.read().strip()

    built_at = datetime.now().astimezone().isoformat()
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
    
    try:
        await tg_service.send_message(chat_id, final_text)
    except Exception as e:
        logger.error(f"Unexpected error sending to Telegram for {chat_id}: {e}")


async def handle_chat_message(update: Update) -> None:
    if not update.message or not update.message.text:
        return

    if update.message.from_user:
        try:
            await redis_service.set_user_chat_id_mapping(
                user_id=update.message.from_user.id,
                chat_id=update.message.chat.id
            )
        except Exception as e:
            logger.warning(f"Failed to set user_chat_id mapping for user {update.message.from_user.id}: {e}")

    if update.message.text.startswith("/"):
        await _handle_command(update.message)
    else:
        await _handle_standard_message(update.message)


async def _handle_command(message: "Message") -> None:
    chat_id = message.chat.id
    parts = message.text.split()
    cmd = parts[0].lower()
    args = parts[1:] if len(parts) > 1 else []
    
    if cmd == "/model":
        await _handle_model_command(chat_id, args)
    elif cmd == "/project":
        await _handle_project_command(chat_id, args)
    elif cmd == "/note" and len(parts) > 1:
        await _handle_note_command(chat_id, args)
    elif cmd == "/github":
        await _handle_github_command(chat_id, args)
    else:
        await _send_response(chat_id, f"❌ Unknown command: {cmd}")


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
            await _send_response(chat_id, f"❌ Invalid GitHub command.")
    except Exception as e:
        await _send_response(chat_id, f"❌ Error: {str(e)}")


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
        model_name = current_pref or f"{settings.LLM_MODEL} (default)"
        message = f"❇️ Current model: `{model_name}`\n\nTo switch, use `/model <alias>`:\n"
        for alias, info in available_models.items():
            message += f"- `{alias}`: {info['name']}\n"
        await _send_response(chat_id, message)
        return
    alias = args[0].lower()
    if alias in available_models:
        await redis_service.set_user_model_preference(chat_id, available_models[alias]["identifier"])
        await _send_response(chat_id, f"✅ Model updated to: {available_models[alias]['name']}")
    else:
        await _send_response(chat_id, f"❌ Invalid model '{alias}'.")


async def _handle_project_command(chat_id: int, args: list[str]) -> None:
    if not args:
        current = await redis_service.get_current_project(chat_id)
        projects = await redis_service.get_project_list(chat_id)
        msg = f"📁 Current Project: `{current}`\n\nAvailable Projects:\n"
        for p in projects:
            msg += f"{'✅' if p == current else '-'} `{p}`\n"
        await _send_response(chat_id, msg + "\nUsage: `/project select <name>`, `/project new <name>`")
        return
    sub_cmd = args[0].lower()
    if sub_cmd == "select" and len(args) > 1:
        await redis_service.set_current_project(chat_id, args[1].lower())
        await _send_response(chat_id, f"✅ Switched to project: `{args[1].lower()}`")
    elif sub_cmd == "new" and len(args) > 1:
        await redis_service.set_current_project(chat_id, args[1].lower())
        await _send_response(chat_id, f"🆕 Created project: `{args[1].lower()}`")
    else:
        await _send_response(chat_id, "❌ Invalid usage.")


async def _execute_tool_call(function_name: str, arguments_str: str) -> str:
    """ประมวลผลการเรียกใช้ Tool ตามที่ LLM ร้องขอ"""
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
            return f"Issue #{issue.number}: {getattr(issue, 'title', 'No Title')}\nStatus: {getattr(issue, 'state', 'Unknown')}\nBody: {getattr(issue, 'body', '')}"
        elif function_name == "search_github_issues":
            issues = github_service.search_issues(repo=args.get("repo"), query=args.get("query"))
            return "\n".join([f"#{i.number}: {i.title}" for i in issues]) if issues else "No issues found."
        elif function_name == "create_github_pr":
            return github_service.pr_create(repo=args.get("repo"), title=args.get("title"), body=args.get("body"), head=args.get("head"), base=args.get("base", "main"))
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
    current_project = await redis_service.get_current_project(chat_id)
    model_pref = await redis_service.get_user_model_preference(chat_id)

    # 0. Action Confirmation Handler
    if prompt.lower() in ["ยืนยัน", "ตกลง", "confirm", "yes", "จัดไป"]:
        pending_message = await redis_service.get_pending_tool_call(chat_id)
        if pending_message:
            await _send_response(chat_id, "👌 กำลังดำเนินการรันคำสั่งที่รอยืนยัน...")
            await redis_service.clear_pending_tool_call(chat_id)
            
            # รันทุก Tool Call ที่ค้างอยู่
            history = await redis_service.get_chat_history(chat_id, project_name=current_project)
            messages = [{"role": "system", "content": f"{settings.SYSTEM_PROMPT}\nYou are continuing a confirmed action."}] + history
            
            # วนลูปจัดการ Tool Calls จนกว่าจะหมด (เหมือน logic ปกติ)
            response = pending_message
            while isinstance(response, dict) and "tool_calls" in response:
                tool_calls = response["tool_calls"]
                # บันทึก Assistant Message ที่มี Tool Calls (ถ้ายังไม่มีในประวัติ)
                if not any(msg.get("tool_calls") == tool_calls for msg in messages):
                    messages.append(response)
                
                for tool_call in tool_calls:
                    call_id = tool_call["id"] if hasattr(tool_call, "__getitem__") else tool_call.id
                    func_name = tool_call["function"]["name"] if hasattr(tool_call, "__getitem__") else tool_call.function.name
                    args_str = tool_call["function"]["arguments"] if hasattr(tool_call, "__getitem__") else tool_call.function.arguments
                    
                    result = await _execute_tool_call(func_name, args_str)
                    messages.append({"role": "tool", "tool_call_id": call_id, "name": func_name, "content": str(result)})
                    await redis_service.add_message_to_history(chat_id, "tool", messages[-1], project_name=current_project)
                
                response = await llm_service.get_llm_reply(messages, model=model_pref, tools=GITHUB_TOOLS)
            
            reply = response
            await _send_response(chat_id, reply)
            await redis_service.add_message_to_history(chat_id, "assistant", reply, project_name=current_project)
            return

    # 1. Normal Message Handling
    history = await redis_service.get_chat_history(chat_id, project_name=current_project)
    workflow_instruction = "\n\n[GIT WORKFLOW]\nIf user wants a PR, call 'git_status' first. If dirty, ASK to add/commit/push first."
    messages = [{"role": "system", "content": f"{settings.SYSTEM_PROMPT}\nProject: {current_project}{workflow_instruction}"}] + history + [{"role": "user", "content": prompt}]

    try:
        response = await llm_service.get_llm_reply(messages, model=model_pref, tools=GITHUB_TOOLS)
        
        while isinstance(response, dict) and "tool_calls" in response:
            tool_calls = response["tool_calls"]
            # เช็คว่ามีคำสั่งต้องยืนยันไหม
            for tc in tool_calls:
                fname = tc["function"]["name"] if hasattr(tc, "__getitem__") else tc.function.name
                if fname in TOOLS_REQUIRING_CONFIRMATION:
                    await redis_service.set_pending_tool_call(chat_id, response)
                    args = json.loads(tc["function"]["arguments"] if hasattr(tc, "__getitem__") else tc.function.arguments)
                    await _send_response(chat_id, f"⚠️ *Akasa ต้องการการยืนยัน*\n\nรันคำสั่ง: `{fname}`\nรายละเอียด: `{args}`\n\nพิมพ์ **'ยืนยัน'** เพื่อดำเนินการ")
                    await redis_service.add_message_to_history(chat_id, "user", prompt, project_name=current_project)
                    await redis_service.add_message_to_history(chat_id, "assistant", response, project_name=current_project)
                    return

            messages.append(response)
            for tc in tool_calls:
                call_id = tc["id"] if hasattr(tc, "__getitem__") else tc.id
                fname = tc["function"]["name"] if hasattr(tc, "__getitem__") else tc.function.name
                args_str = tc["function"]["arguments"] if hasattr(tc, "__getitem__") else tc.function.arguments
                result = await _execute_tool_call(fname, args_str)
                messages.append({"role": "tool", "tool_call_id": call_id, "name": fname, "content": str(result)})
            
            response = await llm_service.get_llm_reply(messages, model=model_pref, tools=GITHUB_TOOLS)

        reply = response
        await _send_response(chat_id, reply)
        await redis_service.add_message_to_history(chat_id, "user", prompt, project_name=current_project)
        await redis_service.add_message_to_history(chat_id, "assistant", reply, project_name=current_project)

    except llm_service.OpenRouterInsufficientCreditsError:
        await _send_response(chat_id, "🔴 ยอดเงิน OpenRouter หมดครับ กรุณาเติมเงินหรือใช้ `/model` สลับรุ่น")
    except Exception as e:
        logger.exception("Error in standard message")
        await _send_response(chat_id, "ขออภัย เกิดข้อผิดพลาดในการประมวลผลครับ")
