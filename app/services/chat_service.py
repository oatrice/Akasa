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

    reply = ""
    try:
        # 5. เรียก LLM พร้อมส่งโมเดลที่ผู้ใช้เลือก (ถ้ามี)
        reply = await llm_service.get_llm_reply(messages, model=model_pref)
        print(f"--- [DEBUG] Received reply from LLM: {reply} ---")
    except (httpx.TimeoutException, httpx.HTTPError) as e:
        logger.error(f"API Error getting LLM reply for {chat_id}: {e}")
        await _send_response(chat_id, "ขออภัย ระบบขัดข้องชั่วคราวในการตอบสนอง 🙇‍♂️")
        return
    except (ValueError, KeyError, TypeError) as e:
        logger.error(f"Malformed LLM response for {chat_id}: {e}")
        await _send_response(chat_id, "ขออภัย ระบบไม่สามารถประมวลผลคำตอบได้ 🙇‍♂️")
        return
    except Exception as e:
        logger.error(f"Unexpected error getting LLM reply for {chat_id}: {e}")
        await _send_response(chat_id, "ขออภัย เกิดข้อผิดพลาดที่ไม่คาดคิด โปรดลองอีกครั้งในภายหลัง")
        return

    # 6. ส่งคำตอบกลับหาผู้ใช้
    await _send_response(chat_id, reply)

    # 7. บันทึก user message + assistant reply ลง Redis ในโปรเจ็กต์ปัจจุบัน
    try:
        await redis_service.add_message_to_history(chat_id, "user", prompt, project_name=current_project)
        await redis_service.add_message_to_history(chat_id, "assistant", reply, project_name=current_project)
    except Exception as e:
        logger.warning(f"Redis add_message_to_history failed for {chat_id} (Project: {current_project}): {e}")
