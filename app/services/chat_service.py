"""
Chat Service — ประสานงานระหว่าง Telegram, Redis, และ LLM

Flow: Telegram → ดึง history จาก Redis → สร้าง messages context → LLM → บันทึก history → ส่งกลับ Telegram
Graceful degradation: ถ้า Redis ล่ม ยังทำงานได้เป็น stateless
"""

from app.models.telegram import Update, Message
from app.models.agent_state import AgentState
from app.services import llm_service, redis_service
from app.services.telegram_service import tg_service # Import the renamed instance
from app.services.github_service import GitHubService, GitHubServiceError, GitHubAuthError
import httpx
import logging
import os
import subprocess
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
            "description": "Creates a new Pull Request in a GitHub repository.",
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
]
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
    
    try:
        await tg_service.send_message(chat_id, final_text)
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to send message to Telegram for {chat_id}. HTTP Status Error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error sending to Telegram for {chat_id}: {e}")


async def handle_chat_message(update: Update) -> None:
    """
    Processes an incoming Telegram update.
    แยกแยะระหว่างคำสั่ง (Command) และข้อความปกติ
    """
    if not update.message or not update.message.text:
        return

    # --- Issue #30: Proactive Messaging Support ---
    if update.message and update.message.from_user:
        try:
            await redis_service.set_user_chat_id_mapping(
                user_id=update.message.from_user.id,
                chat_id=update.message.chat.id
            )
        except Exception as e:
            logger.warning(f"Failed to set user_chat_id mapping for user {update.message.from_user.id}: {e}")
    # ---------------------------------------------

    if update.message.text.startswith("/"):
        await _handle_command(update.message)
    else:
        await _handle_standard_message(update.message)


async def _handle_command(message: "Message") -> None:
    """จัดการคำสั่งต่างๆ (เช่น /model, /project, /github)"""
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
    """จัดการคำสั่ง /github (repo, issues, pr)"""
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
            repo_name = args[1]
            repo = github_service.get_repo_info(repo_name)
            msg = f"📦 *{repo.full_name}*\n"
            msg += f"📝 {repo.description or 'No description'}\n"
            msg += f"⭐ Stars: {repo.stargazers_count}\n"
            msg += f"🔗 [View on GitHub]({repo.html_url})"
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
            repo_name = args[2]
            title = args[3]
            body = " ".join(args[4:]) if len(args) > 4 else "Created via Akasa Bot"
            url = github_service.create_issue(repo_name, title, body)
            await _send_response(chat_id, f"✅ Issue created: {url}")

        elif sub_cmd == "pr":
            if len(args) > 1 and args[1] == "new" and len(args) > 3:
                repo_name = args[2]
                title = args[3]
                body = " ".join(args[4:]) if len(args) > 4 else "Created via Akasa Bot"
                url = github_service.pr_create(repo_name, title, body)
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

    except GitHubAuthError as e:
        await _send_response(chat_id, f"🔐 *Auth Error:* {str(e)}\nPlease check your `GITHUB_TOKEN`.")
    except GitHubServiceError as e:
        await _send_response(chat_id, f"❌ *GitHub Error:* {str(e)}")
    except Exception as e:
        logger.exception("GitHub command failed")
        await _send_response(chat_id, f"⚠️ Unexpected error: {str(e)}")


async def _handle_note_command(chat_id: int, args: list[str]) -> None:
    """จัดการคำสั่ง /note เพื่อบันทึก state การทำงานปัจจุบัน"""
    note_text = " ".join(args)
    current_project = await redis_service.get_current_project(chat_id)
    
    # ดึง state เก่ามา update หรือสร้างใหม่
    agent_state = await redis_service.get_agent_state(chat_id, current_project)
    if not agent_state:
        agent_state = AgentState()
        
    agent_state.current_task = note_text
    agent_state.last_activity_timestamp = datetime.now(timezone.utc)
    
    await redis_service.set_agent_state(chat_id, current_project, agent_state)
    
    await _send_response(chat_id, f"✅ Note saved for project: `{current_project}`")




async def _handle_model_command(chat_id: int, args: list[str]) -> None:
    """จัดการคำสั่ง /model"""
    available_models = settings.AVAILABLE_MODELS
    
    if not args:
        # กรณี /model เฉยๆ -> แสดงสถานะปัจจุบันและรายการที่เลือกได้
        try:
            current_pref = await redis_service.get_user_model_preference(chat_id)
        except Exception:
            current_pref = None
            
        if current_pref:
            # ค้นหาชื่อโมเดลจากการตั้งค่าส่วนตัว
            model_name = current_pref
            for alias, info in available_models.items():
                if info["identifier"] == current_pref:
                    model_name = info["name"]
                    break
        else:
            # ค้นหาชื่อโมเดลเริ่มต้นจาก settings.LLM_MODEL
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

    # กรณี /model <alias> -> อัปเดตการตั้งค่า
    alias = args[0].lower()
    if alias in available_models:
        model_info = available_models[alias]
        try:
            await redis_service.set_user_model_preference(chat_id, model_info["identifier"])
            await _send_response(chat_id, f"✅ Model selection updated to: {model_info['name']}")
        except Exception as e:
            logger.error(f"Failed to save model preference for {chat_id}: {e}")
            await _send_response(chat_id, "❌ Failed to save model preference. Please try again.")
    else:
        # Alias ไม่ถูกต้อง
        message = f"❌ Invalid model '{alias}'.\nAvailable models:\n"
        for a in available_models.keys():
            message += f"- `{a}`\n"
        await _send_response(chat_id, message)


async def _handle_project_command(chat_id: int, args: list[str]) -> None:
    """จัดการคำสั่ง /project (list, select, new, rename)"""
    if not args:
        # แสดงสถานะปัจจุบัน
        current = await redis_service.get_current_project(chat_id)
        projects = await redis_service.get_project_list(chat_id)
        
        msg = f"📁 Current Project: `{current}`\n\n"
        msg += "Available Projects:\n"
        for p in projects:
            marker = "✅" if p == current else "-"
            msg += f"{marker} `{p}`\n"
        
        msg += "\nUsage:\n"
        msg += "• `/project select <name>`\n"
        msg += "• `/project new <name>`\n"
        msg += "• `/project rename <old> <new>`"
        await _send_response(chat_id, msg)
        return

    sub_cmd = args[0].lower()
    
    if sub_cmd == "list":
        projects = await redis_service.get_project_list(chat_id)
        msg = "📁 Your Projects:\n" + "\n".join([f"- `{p}`" for p in projects])
        await _send_response(chat_id, msg)
        
    elif sub_cmd == "select" and len(args) > 1:
        target = args[1].lower()
        projects = await redis_service.get_project_list(chat_id)
        if target in projects:
            await redis_service.set_current_project(chat_id, target)
            
            # Issue #38: Context Restoration
            agent_state = await redis_service.get_agent_state(chat_id, target)
            if agent_state and agent_state.current_task:
                summary_msg = (
                    f"✅ Switched to project: `{target}`\n\n"
                    f"👋 Welcome back! Last known task:\n"
                    f"```{agent_state.current_task}```"
                )
                await _send_response(chat_id, summary_msg)
            else:
                await _send_response(chat_id, f"✅ Switched to project: `{target}`")
        else:
            await _send_response(chat_id, f"❌ Project `{target}` not found. Use `/project new {target}` to create it.")

    elif sub_cmd == "new" and len(args) > 1:
        target = args[1].lower()
        await redis_service.set_current_project(chat_id, target)
        await _send_response(chat_id, f"🆕 Created and switched to project: `{target}`")

    elif sub_cmd == "rename" and len(args) > 2:
        old_name = args[1].lower()
        new_name = args[2].lower()
        
        projects = await redis_service.get_project_list(chat_id)
        if old_name in projects:
            await redis_service.rename_project(chat_id, old_name, new_name)
            await _send_response(chat_id, f"✅ Project renamed from `{old_name}` to `{new_name}`.\n(Current project updated if needed)")
        else:
            await _send_response(chat_id, f"❌ Project `{old_name}` not found.")
    
    else:
        await _send_response(chat_id, "❌ Invalid usage. Try `/project` for help.")


async def _execute_tool_call(function_name: str, arguments_str: str) -> str:
    """ประมวลผลการเรียกใช้ Tool ตามที่ LLM ร้องขอ"""
    import json
    try:
        args = json.loads(arguments_str)
        print(f"--- [DEBUG] Executing tool: {function_name} with args: {args} ---")
        
        if function_name == "create_github_issue":
            return github_service.create_issue(
                repo=args.get("repo"),
                title=args.get("title"),
                body=args.get("body")
            )
        elif function_name == "list_github_open_prs":
            prs = github_service.get_pr_status(repo=args.get("repo"))
            if not prs:
                return "No open pull requests found."
            else:
                formatted_prs = []
                for pr in prs:
                    author_name = pr.author.get("login") if pr.author else "unknown"
                    formatted_prs.append(f"#{pr.number}: {pr.title} by @{author_name} ({pr.url})")
                return "\n".join(formatted_prs)
        elif function_name == "create_github_comment":
            return github_service.create_comment(
                repo=args.get("repo"),
                issue_number=args.get("issue_number"),
                body=args.get("body")
            )
        elif function_name == "close_github_issue":
            return github_service.close_issue(
                repo=args.get("repo"),
                issue_number=args.get("issue_number")
            )
        elif function_name == "delete_github_issue":
            return github_service.delete_issue(
                repo=args.get("repo"),
                issue_number=args.get("issue_number")
            )
        elif function_name == "get_github_issue":
            issue = github_service.get_issue(
                repo=args.get("repo"),
                issue_number=args.get("issue_number")
            )
            # Use getattr or dict access to be safe if model is not updated in memory
            title = getattr(issue, 'title', 'No Title')
            state = getattr(issue, 'state', 'Unknown')
            url = getattr(issue, 'url', '')
            body = getattr(issue, 'body', 'No Description')
            author_dict = getattr(issue, 'author', {})
            author_name = author_dict.get('login') if author_dict else 'unknown'
            
            return f"Issue #{issue.number}: {title}\nStatus: {state}\nAuthor: @{author_name}\nURL: {url}\n\nBody:\n{body}"
        elif function_name == "search_github_issues":
            issues = github_service.search_issues(
                repo=args.get("repo"),
                query=args.get("query")
            )
            if not issues:
                return "No issues matching the query found."
            return "\n".join([f"#{i.number}: {i.title} (@{i.author.get('login') if i.author else 'unknown'})" for i in issues])
        elif function_name == "create_github_pr":
            return github_service.pr_create(
                repo=args.get("repo"),
                title=args.get("title"),
                body=args.get("body"),
                head=args.get("head"),
                base=args.get("base", "main")
            )
        else:
            return f"Error: Tool {function_name} not implemented."
            
    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        return f"Error executing {function_name}: {str(e)}"


async def _handle_standard_message(message: "Message") -> None:
    """จัดการข้อความปกติ (ดึง history, เรียก LLM, บันทึก history)"""
    chat_id = message.chat.id
    prompt = message.text.strip()
    print(f"--- [DEBUG] Processing message from {chat_id}: {prompt} ---")
    
    # 1. ดึงโปรเจ็กต์ปัจจุบัน
    current_project = await redis_service.get_current_project(chat_id)

    # 2. ดึง Model Preference จาก Redis
    try:
        model_pref = await redis_service.get_user_model_preference(chat_id)
    except Exception as e:
        logger.warning(f"Redis get_user_model_preference failed for {chat_id}: {e}")
        model_pref = None

    # 3. ดึง history จาก Redis แยกตามโปรเจ็กต์
    try:
        history = await redis_service.get_chat_history(chat_id, project_name=current_project)
    except Exception as e:
        logger.warning(f"Redis get_chat_history failed for {chat_id} (Project: {current_project}): {e}")
        history = []

    # 4. สร้าง messages context: system prompt (พร้อมบริบทโปรเจ็กต์) + history + ข้อความใหม่ของ user
    custom_system_prompt = f"{settings.SYSTEM_PROMPT}\n\n[CONTEXT]\nYou are currently working on project: '{current_project}'."
    messages = [{"role": "system", "content": custom_system_prompt}] + history + [{"role": "user", "content": prompt}]

    try:
        # 5. เรียก LLM พร้อมส่งโมเดลที่ผู้ใช้เลือก และส่ง GITHUB_TOOLS
        response = await llm_service.get_llm_reply(messages, model=model_pref, tools=GITHUB_TOOLS)
        
        # --- Issue #32: Tool Calling Loop ---
        while isinstance(response, dict) and "tool_calls" in response:
            tool_calls = response["tool_calls"]
            # เพิ่ม message ของ assistant ที่มี tool_calls ลงใน messages
            messages.append(response)
            
            for tool_call in tool_calls:
                call_id = tool_call["id"] if hasattr(tool_call, "__getitem__") else tool_call.id
                function_name = tool_call["function"]["name"] if hasattr(tool_call, "__getitem__") else tool_call.function.name
                arguments_str = tool_call["function"]["arguments"] if hasattr(tool_call, "__getitem__") else tool_call.function.arguments
                
                # Use the refactored private method to execute the tool
                result = await _execute_tool_call(function_name, arguments_str)
                
                # เพิ่มผลลัพธ์จาก Tool ลงใน messages
                messages.append({
                    "tool_call_id": call_id,
                    "role": "tool",
                    "name": function_name,
                    "content": str(result),
                })
            
            # เรียก LLM อีกครั้งเพื่อสรุปผล
            response = await llm_service.get_llm_reply(messages, model=model_pref, tools=GITHUB_TOOLS)
        
        # หลังจบลูป response จะเป็น content string
        reply = response
        print(f"--- [DEBUG] Final reply from LLM: {reply} ---")
        # ------------------------------------

    except (httpx.TimeoutException, httpx.HTTPError) as e:
        logger.error(f"API Error getting LLM reply for {chat_id}: {e}")
        await _send_response(chat_id, "ขออภัย ระบบขัดข้องชั่วคราวในการตอบสนอง 🙇‍♂️")
        return
    except llm_service.OpenRouterInsufficientCreditsError as e:
        logger.warning(f"OpenRouter credits exhausted for {chat_id}: {e}")
        error_msg = (
            "🔴 *ยอดเงินใน OpenRouter ไม่เพียงพอ*\n\n"
            "ไม่สามารถใช้โมเดลปัจจุบันได้เนื่องจากยอดเงินคงเหลือหมดครับ\n\n"
            "💡 *คำแนะนำ:*\n"
            "1. เติมเงินใน OpenRouter\n"
            "2. สลับไปใช้โมเดลอื่น (เช่น Gemini ผ่าน Google SDK หรือโมเดลฟรี) โดยใช้คำสั่ง `/model`"
        )
        await _send_response(chat_id, error_msg)
        return
    except (ValueError, KeyError, TypeError) as e:
        logger.error(f"Malformed LLM response for {chat_id}: {e}")
        await _send_response(chat_id, "ขออภัย ระบบไม่สามารถประมวลผลคำตอบได้ 🙇‍♂️")
        return
    except Exception as e:
        logger.exception(f"Unexpected error in _handle_standard_message for {chat_id}")
        await _send_response(chat_id, "ขออภัย เกิดข้อผิดพลาดที่ไม่คาดคิด โปรดลองอีกครั้งในภายหลัง")
        return

    # 6. ส่งคำตอบกลับหาผู้ใช้
    await _send_response(chat_id, reply)

    # 7. บันทึกประวัติการสนทนา (User Prompt + Tool Calls + Tool Results + Final Reply)
    try:
        # เริ่มต้นด้วยข้อความของ User
        messages_to_save = [{"role": "user", "content": prompt}]

        # ถ้ามีการเรียก Tool (response ในตอนแรกจะเป็น dict)
        # เราต้องหาข้อความที่เพิ่มเข้ามาในระหว่าง loop
        # หมายเหตุ: messages ในตอนแรกคือ [system, history, user]
        # เราจะเริ่มบันทึกตั้งแต่ลำดับที่ต่อจาก user prompt
        user_index = -1
        for i, msg in enumerate(messages):
            if msg.get("role") == "user" and msg.get("content") == prompt:
                user_index = i
                break
        
        if user_index != -1:
            # เก็บข้อความทั้งหมดที่เกิดขึ้นหลังจาก User Prompt (เช่น Assistant Tool Call, Tool Result)
            messages_to_save.extend(messages[user_index + 1:])
        
        # สุดท้ายเพิ่ม Assistant Final Reply (ซึ่งคือค่า reply string)
        messages_to_save.append({"role": "assistant", "content": reply})

        # บันทึกลง Redis ทีละข้อความ
        for msg in messages_to_save:
            role = msg.get("role")
            # ถ้าเป็น assistant และมี tool_calls ให้ส่ง msg ทั้งก้อนไปให้ redis_service จัดการ
            if role == "assistant" and "tool_calls" in msg:
                await redis_service.add_message_to_history(chat_id, role, msg, project_name=current_project)
            # ถ้าเป็น tool ให้ส่ง msg ทั้งก้อน (มี tool_call_id, name, content)
            elif role == "tool":
                await redis_service.add_message_to_history(chat_id, role, msg, project_name=current_project)
            else:
                await redis_service.add_message_to_history(chat_id, role, msg.get("content"), project_name=current_project)

    except Exception as e:
        logger.warning(f"Redis add_message_to_history failed for {chat_id} (Project: {current_project}): {e}")
