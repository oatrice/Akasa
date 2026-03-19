"""
Redis Service — จัดการประวัติการสนทนาใน Redis (รองรับ Multi-Project)

ใช้ Redis LIST เก็บ messages แบบ LIFO (LPUSH) แยกตามชื่อโปรเจ็กต์
เพื่อให้ได้ลำดับเวลาถูกต้อง (เก่าสุด → ใหม่สุด)
"""

import redis.asyncio as redis
import json
import logging
from typing import Optional, List
from app.config import settings
from app.models.agent_state import AgentState
from app.models.notification import ActionRequestState

logger = logging.getLogger(__name__)

# Connection pool — reuse connection ตลอด application lifetime
redis_pool = redis.from_url(settings.REDIS_URL, decode_responses=True)


def _get_owner_chat_id() -> int:
    """Resolve the canonical owner chat ID used for local context sync."""
    chat_id = (settings.AKASA_CHAT_ID or "").strip()
    if not chat_id:
        raise ValueError("Owner chat is not configured on the server.")
    if not chat_id.lstrip("-").isdigit():
        raise ValueError("Owner chat is not configured correctly on the server.")
    return int(chat_id)


async def get_chat_history(chat_id: int, project_name: str = "default") -> list[dict]:
    """ดึงประวัติการสนทนาล่าสุดสำหรับ chat_id ในโปรเจ็กต์ที่กำหนด"""
    if settings.REDIS_HISTORY_LIMIT <= 0:
        return []

    # โครงสร้าง Key ใหม่: chat_history:{chat_id}:{project_name}
    history_key = f"chat_history:{chat_id}:{project_name}"
    
    # --- Migration Logic ---
    # ถ้าดึงจาก 'default' และไม่มีข้อมูล ให้ลองเช็ค Key แบบเก่า (v0.7.0 ลงไป)
    if project_name == "default":
        exists = await redis_pool.exists(history_key)
        if not exists:
            old_key = f"chat_history:{chat_id}"
            old_exists = await redis_pool.exists(old_key)
            if old_exists:
                # ย้ายข้อมูลจาก Key เก่ามาที่ 'default' ใหม่
                logger.info(f"Migrating history for {chat_id} from old key to 'default' project.")
                # ใช้ RENAME (atomic) เพื่อย้ายข้อมูล
                await redis_pool.rename(old_key, history_key)
    # -----------------------

    raw_history = await redis_pool.lrange(history_key, 0, settings.REDIS_HISTORY_LIMIT - 1)
    
    # LPUSH เก็บแบบ LIFO → reverse เพื่อให้ได้ chronological order
    history = []
    for msg in reversed(raw_history):
        try:
            history.append(json.loads(msg))
        except json.JSONDecodeError as e:
            logger.warning(f"Skipping corrupted JSON in Redis for {chat_id} (Project: {project_name}): {msg} - Error: {e}")
            continue
            
    return history


async def add_message_to_history(chat_id: int, role: str, content: any, project_name: str = "default"):
    """เพิ่มข้อความลงในประวัติการสนทนาของ chat_id ในโปรเจ็กต์ที่กำหนด"""
    if settings.REDIS_HISTORY_LIMIT <= 0:
        return

    # เพิ่มชื่อโปรเจ็กต์ลงใน List ของ User เพื่อให้แสดงผลได้
    await _add_project_to_list(chat_id, project_name)

    history_key = f"chat_history:{chat_id}:{project_name}"
    
    # สร้าง message dict
    msg_dict = {"role": role}
    
    # ถ้าเป็นบทบาท assistant และมี tool_calls ให้เก็บโครงสร้างนั้นไว้
    if role == "assistant" and isinstance(content, dict) and "tool_calls" in content:
        msg_dict.update(content)
    elif role == "tool":
        msg_dict["tool_call_id"] = content.get("tool_call_id") if isinstance(content, dict) else None
        msg_dict["name"] = content.get("name") if isinstance(content, dict) else None
        msg_dict["content"] = content.get("content") if isinstance(content, dict) else str(content)
    else:
        msg_dict["content"] = str(content)

    message_json = json.dumps(msg_dict)
    
    # Push ข้อความใหม่ไปที่หัว list
    await redis_pool.lpush(history_key, message_json)
    # ตัด list ให้เหลือไม่เกิน limit
    await redis_pool.ltrim(history_key, 0, settings.REDIS_HISTORY_LIMIT - 1)
    # ตั้ง TTL เพื่อให้ key หมดอายุอัตโนมัติ
    await redis_pool.expire(history_key, settings.REDIS_TTL_SECONDS)


async def get_user_model_preference(chat_id: int) -> Optional[str]:
    """ดึงค่าโมเดลที่ผู้ใช้เลือกไว้จาก Redis"""
    pref_key = f"user_model_pref:{chat_id}"
    return await redis_pool.get(pref_key)


async def set_user_model_preference(chat_id: int, model_identifier: str):
    """บันทึกค่าโมเดลที่ผู้ใช้เลือกไว้ลงใน Redis"""
    pref_key = f"user_model_pref:{chat_id}"
    await redis_pool.set(pref_key, model_identifier, ex=settings.REDIS_TTL_SECONDS)


# --- Multi-Project Management ---

async def get_current_project(chat_id: int) -> str:
    """ดึงชื่อโปรเจ็กต์ที่ Active อยู่ในปัจจุบัน"""
    current_key = f"user_current_project:{chat_id}"
    project = await redis_pool.get(current_key)
    return project if project else "default"


async def set_current_project(chat_id: int, project_name: str):
    """ตั้งค่าโปรเจ็กต์ที่ Active อยู่ในปัจจุบัน"""
    current_key = f"user_current_project:{chat_id}"
    await redis_pool.set(current_key, project_name, ex=settings.REDIS_TTL_SECONDS)
    # เพิ่มเข้า list ด้วยถ้ายังไม่มี
    await _add_project_to_list(chat_id, project_name)


async def get_owner_current_project() -> str:
    """ดึงโปรเจ็กต์ปัจจุบันของ owner chat สำหรับ local context sync."""
    return await get_current_project(_get_owner_chat_id())


async def set_owner_current_project(project_name: str) -> str:
    """ตั้งค่าโปรเจ็กต์ปัจจุบันของ owner chat สำหรับ local context sync."""
    normalized = project_name.strip().lower()
    if not normalized:
        raise ValueError("active_project must not be empty")

    chat_id = _get_owner_chat_id()
    await set_current_project(chat_id, normalized)
    return normalized


async def rename_project(chat_id: int, old_name: str, new_name: str):
    """เปลี่ยนชื่อโปรเจ็กต์และย้ายประวัติแชท (Atomic Migration)"""
    if old_name == new_name:
        return

    old_history_key = f"chat_history:{chat_id}:{old_name}"
    new_history_key = f"chat_history:{chat_id}:{new_name}"
    list_key = f"user_projects:{chat_id}"
    current_key = f"user_current_project:{chat_id}"

    # 1. ย้ายประวัติแชท (ถ้ามี)
    exists = await redis_pool.exists(old_history_key)
    if exists:
        await redis_pool.rename(old_history_key, new_history_key)

    # 2. อัปเดตรายชื่อโปรเจ็กต์ (ลบชื่อเก่า เพิ่มชื่อใหม่)
    await redis_pool.srem(list_key, old_name)
    await redis_pool.sadd(list_key, new_name)

    # 3. ถ้าเป็นโปรเจ็กต์ปัจจุบัน ให้เปลี่ยนชื่อด้วย
    current = await redis_pool.get(current_key)
    if current == old_name:
        await redis_pool.set(current_key, new_name, ex=settings.REDIS_TTL_SECONDS)


async def get_project_list(chat_id: int) -> List[str]:
    """ดึงรายชื่อโปรเจ็กต์ทั้งหมดของ User"""
    list_key = f"user_projects:{chat_id}"
    projects = await redis_pool.smembers(list_key)
    # ต้องมี default เสมอ
    if not projects:
        return ["default"]
    
    # แปลงจาก set เป็น list และตรวจสอบว่ามี default หรือไม่
    project_list = list(projects)
    if "default" not in project_list:
        project_list.append("default")
        
    return project_list


async def _add_project_to_list(chat_id: int, project_name: str):
    """Helper สำหรับเพิ่มโปรเจ็กต์เข้า List (Internal use)"""
    list_key = f"user_projects:{chat_id}"
    await redis_pool.sadd(list_key, project_name)
    await redis_pool.expire(list_key, settings.REDIS_TTL_SECONDS)


# --- Project Activity Indexes ---

def _normalize_project_name(project_name: str) -> str:
    normalized = (project_name or "").strip().lower()
    return normalized or "default"


def _get_project_commands_key(chat_id: int, project_name: str) -> str:
    return f"project_commands:{chat_id}:{_normalize_project_name(project_name)}"


def _get_project_deployments_key(chat_id: int, project_name: str) -> str:
    return f"project_deployments:{chat_id}:{_normalize_project_name(project_name)}"


async def _push_project_activity_id(key: str, value: str, limit: int = 5):
    await redis_pool.lpush(key, value)
    await redis_pool.ltrim(key, 0, max(limit - 1, 0))
    await redis_pool.expire(key, settings.REDIS_TTL_SECONDS)


async def add_recent_command_id(chat_id: int, project_name: str, command_id: str):
    """Track the most recent command IDs for a project."""
    await _push_project_activity_id(
        _get_project_commands_key(chat_id, project_name),
        command_id,
    )


async def get_recent_command_ids(
    chat_id: int,
    project_name: str,
    limit: int = 3,
) -> List[str]:
    """Return recent command IDs for a project, newest first."""
    key = _get_project_commands_key(chat_id, project_name)
    return await redis_pool.lrange(key, 0, max(limit - 1, 0))


async def add_recent_deployment_id(chat_id: int, project_name: str, deployment_id: str):
    """Track the most recent deployment IDs for a project."""
    await _push_project_activity_id(
        _get_project_deployments_key(chat_id, project_name),
        deployment_id,
    )


async def get_recent_deployment_ids(
    chat_id: int,
    project_name: str,
    limit: int = 3,
) -> List[str]:
    """Return recent deployment IDs for a project, newest first."""
    key = _get_project_deployments_key(chat_id, project_name)
    return await redis_pool.lrange(key, 0, max(limit - 1, 0))


# --- Agent State (Project-Specific Memory) ---

def _get_agent_state_key(chat_id: int, project_name: str) -> str:
    """Helper to generate the Redis key for agent state."""
    return f"agent_state:{chat_id}:{project_name}"


async def get_agent_state(chat_id: int, project_name: str) -> Optional[AgentState]:
    """
    ดึง AgentState ล่าสุดของโปรเจ็กต์.
    คืนค่า AgentState object หรือ None ถ้าไม่มีข้อมูล.
    """
    state_key = _get_agent_state_key(chat_id, project_name)
    json_str = await redis_pool.get(state_key)
    if not json_str:
        return None
    
    try:
        return AgentState.from_json(json_str)
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Failed to decode AgentState for {chat_id} (Project: {project_name}): {e}")
        return None


async def set_agent_state(chat_id: int, project_name: str, state: AgentState):
    """
    บันทึก AgentState ของโปรเจ็กต์ลง Redis.
    """
    state_key = _get_agent_state_key(chat_id, project_name)
    json_str = state.to_json()
    await redis_pool.set(state_key, json_str, ex=settings.REDIS_TTL_SECONDS)


# --- User ID to Chat ID Mapping (for Proactive Messaging) ---

async def set_user_chat_id_mapping(user_id: int, chat_id: int):
    """
    เก็บ mapping ระหว่าง user_id ของ Telegram กับ chat_id ล่าสุด.
    """
    key = f"user_chat_id:{user_id}"
    # Chat ID ควรจะเป็น str เสมอตาม convention ของ Redis
    await redis_pool.set(key, str(chat_id), ex=settings.REDIS_TTL_SECONDS)


async def get_chat_id_for_user(user_id: int) -> Optional[str]:
    """
    ดึง chat_id ล่าสุดที่ผูกกับ user_id.
    """
    key = f"user_chat_id:{user_id}"
    return await redis_pool.get(key)


# --- Pending Tool Calls (Action Confirmation) ---

async def set_pending_tool_call(chat_id: int, tool_call: dict):
    """เก็บคำสั่งที่รอยืนยันลง Redis (หมดอายุใน 10 นาที)"""
    key = f"pending_tool:{chat_id}"
    await redis_pool.set(key, json.dumps(tool_call), ex=600)


async def get_pending_tool_call(chat_id: int) -> Optional[dict]:
    """ดึงคำสั่งที่รอยืนยันออกมา"""
    key = f"pending_tool:{chat_id}"
    data = await redis_pool.get(key)
    if data:
        return json.loads(data)
    return None


async def clear_pending_tool_call(chat_id: int):
    """ลบคำสั่งที่รอยืนยัน"""
    key = f"pending_tool:{chat_id}"
    await redis_pool.delete(key)


# --- Remote Action Confirmation (Issue #49) ---

async def set_action_request(request_id: str, state: ActionRequestState):
    """บันทึกสถานะ Action Request ลง Redis (หมดอายุใน 1 ชั่วโมง)"""
    key = f"action_request:{request_id}"
    # ใช้ model_dump_json() สำหรับ Pydantic v2
    await redis_pool.set(key, state.model_dump_json(), ex=3600)


async def get_action_request(request_id: str) -> Optional[ActionRequestState]:
    """ดึงสถานะ Action Request จาก Redis"""
    key = f"action_request:{request_id}"
    data = await redis_pool.get(key)
    if not data:
        return None
    try:
        return ActionRequestState.model_validate_json(data)
    except Exception as e:
        logger.error(f"Failed to decode ActionRequestState for {request_id}: {e}")
        return None


async def set_session_permission(session_id: str, ttl: int = 3600):
    """บันทึกว่า Session นี้ได้รับอนุญาตให้รัน Sensitive Tool ได้ (TTL เป็นวินาที)"""
    key = f"session_permission:{session_id}"
    await redis_pool.set(key, "allowed", ex=ttl)


async def has_session_permission(session_id: str) -> bool:
    """ตรวจสอบว่า Session นี้ได้รับอนุญาตอยู่หรือไม่"""
    if not session_id:
        return False
    key = f"session_permission:{session_id}"
    return await redis_pool.exists(key) > 0
