import pytest
import pytest_asyncio
import json
import fakeredis.aioredis


@pytest_asyncio.fixture
async def fake_redis():
    """Create a fakeredis instance for testing."""
    server = fakeredis.aioredis.FakeServer()
    client = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
    yield client
    await client.flushall()
    await client.aclose()


@pytest.fixture
def patch_redis(fake_redis, monkeypatch):
    """Patch redis_service to use fakeredis."""
    import app.services.redis_service as rs
    monkeypatch.setattr(rs, "redis_pool", fake_redis)
    return fake_redis


# --- Multi-Project History Support ---

@pytest.mark.asyncio
async def test_get_chat_history_with_project(patch_redis):
    """ทดสอบการดึงประวัติแชทแยกตามโปรเจ็กต์"""
    from app.services.redis_service import add_message_to_history, get_chat_history

    chat_id = 100
    # บันทึกในโปรเจ็กต์ A
    await add_message_to_history(chat_id, "user", "Message in A", project_name="project-a")
    # บันทึกในโปรเจ็กต์ B
    await add_message_to_history(chat_id, "user", "Message in B", project_name="project-b")

    history_a = await get_chat_history(chat_id, project_name="project-a")
    history_b = await get_chat_history(chat_id, project_name="project-b")

    assert len(history_a) == 1
    assert history_a[0]["content"] == "Message in A"
    assert len(history_b) == 1
    assert history_b[0]["content"] == "Message in B"


@pytest.mark.asyncio
async def test_get_chat_history_default_project(patch_redis):
    """หากไม่ระบุชื่อโปรเจ็กต์ ต้องใช้ 'default' อัตโนมัติ"""
    from app.services.redis_service import add_message_to_history, get_chat_history

    chat_id = 200
    # บันทึกแบบไม่ระบุโปรเจ็กต์
    await add_message_to_history(chat_id, "user", "Message in Default")

    # ดึงแบบระบุ 'default' ตรงๆ
    history_explicit_default = await get_chat_history(chat_id, project_name="default")
    # ดึงแบบไม่ระบุโปรเจ็กต์
    history_implicit_default = await get_chat_history(chat_id)

    assert history_explicit_default == history_implicit_default
    assert history_explicit_default[0]["content"] == "Message in Default"


# --- Current Project Management ---

@pytest.mark.asyncio
async def test_get_current_project_none(patch_redis):
    """หากยังไม่เคยตั้งค่าโปรเจ็กต์ปัจจุบัน ต้องคืนค่า 'default'"""
    from app.services.redis_service import get_current_project
    project = await get_current_project(chat_id=300)
    assert project == "default"


@pytest.mark.asyncio
async def test_set_and_get_current_project(patch_redis):
    """ทดสอบการตั้งค่าและดึงโปรเจ็กต์ปัจจุบัน"""
    from app.services.redis_service import set_current_project, get_current_project

    chat_id = 400
    await set_current_project(chat_id, "my-awesome-project")
    
    project = await get_current_project(chat_id)
    assert project == "my-awesome-project"


@pytest.mark.asyncio
async def test_get_owner_current_project_uses_akasa_chat_id(patch_redis, monkeypatch):
    from app.services.redis_service import get_owner_current_project, set_current_project

    monkeypatch.setattr("app.services.redis_service.settings.AKASA_CHAT_ID", "4321")
    await set_current_project(4321, "owner-project")

    project = await get_owner_current_project()
    assert project == "owner-project"


@pytest.mark.asyncio
async def test_set_owner_current_project_normalizes_lowercase(patch_redis, monkeypatch):
    from app.services.redis_service import set_owner_current_project, get_current_project

    monkeypatch.setattr("app.services.redis_service.settings.AKASA_CHAT_ID", "4321")

    stored = await set_owner_current_project("  Docs-Bot  ")
    assert stored == "docs-bot"
    assert await get_current_project(4321) == "docs-bot"


# --- Recent Project Activity Indexes ---

@pytest.mark.asyncio
async def test_recent_command_ids_are_tracked_per_project(patch_redis):
    from app.services.redis_service import add_recent_command_id, get_recent_command_ids

    chat_id = 777
    await add_recent_command_id(chat_id, "akasa", "cmd_1")
    await add_recent_command_id(chat_id, "akasa", "cmd_2")
    await add_recent_command_id(chat_id, "luma", "cmd_other")

    assert await get_recent_command_ids(chat_id, "akasa") == ["cmd_2", "cmd_1"]
    assert await get_recent_command_ids(chat_id, "luma") == ["cmd_other"]


@pytest.mark.asyncio
async def test_recent_deployment_ids_are_tracked_per_project(patch_redis):
    from app.services.redis_service import add_recent_deployment_id, get_recent_deployment_ids

    chat_id = 778
    await add_recent_deployment_id(chat_id, "akasa", "dep_1")
    await add_recent_deployment_id(chat_id, "akasa", "dep_2")
    await add_recent_deployment_id(chat_id, "akasa", "dep_3")

    assert await get_recent_deployment_ids(chat_id, "akasa", limit=2) == [
        "dep_3",
        "dep_2",
    ]


# --- Project List Management ---

@pytest.mark.asyncio
async def test_get_project_list_contains_default(patch_redis):
    """รายชื่อโปรเจ็กต์ต้องมี 'default' เสมอ"""
    from app.services.redis_service import get_project_list
    projects = await get_project_list(chat_id=500)
    assert "default" in projects


@pytest.mark.asyncio
async def test_add_project_to_list(patch_redis):
    """เมื่อใช้โปรเจ็กต์ใหม่ ต้องถูกเพิ่มเข้าไปใน List"""
    from app.services.redis_service import add_message_to_history, get_project_list

    chat_id = 600
    await add_message_to_history(chat_id, "user", "Hello", project_name="new-project")
    
    projects = await get_project_list(chat_id)
    assert "default" in projects
    assert "new-project" in projects


# --- Migration Support ---

@pytest.mark.asyncio
async def test_auto_migration_from_v070(patch_redis):
    """ข้อมูลเดิมใน chat_history:{chat_id} ต้องถูกย้ายไปที่ :default อัตโนมัติ"""
    from app.services.redis_service import get_chat_history
    import json

    chat_id = 700
    old_key = f"chat_history:{chat_id}"
    new_key = f"chat_history:{chat_id}:default"

    # จำลองข้อมูลเก่า (v0.7.0)
    old_data = json.dumps({"role": "user", "content": "Old context"})
    await patch_redis.lpush(old_key, old_data)

    # ก่อนเรียก get_chat_history: new_key ต้องยังไม่มี
    assert await patch_redis.exists(new_key) == 0

    # เรียก get_chat_history (default) -> ควรเกิด Migration
    history = await get_chat_history(chat_id)

    assert len(history) == 1
    assert history[0]["content"] == "Old context"

    # หลังเรียก: old_key ต้องหายไป และ new_key ต้องมีข้อมูล
    assert await patch_redis.exists(old_key) == 0
    assert await patch_redis.exists(new_key) == 1


# --- Test Agent State (Project-Specific Memory - Issue #38) ---

@pytest.mark.asyncio
async def test_set_and_get_agent_state(patch_redis):
    """ทดสอบการบันทึกและดึง AgentState (JSON object)"""
    from app.services.redis_service import set_agent_state, get_agent_state
    from app.models.agent_state import AgentState
    import datetime

    chat_id = 900
    project_name = "odin"
    now = datetime.datetime.now(datetime.timezone.utc)

    # 1. ทดสอบดึง state ที่ยังไม่มีอยู่ ควรได้ None
    initial_state = await get_agent_state(chat_id, project_name)
    assert initial_state is None

    # 2. สร้างและบันทึก state
    state_to_save = AgentState(
        current_task="Refactoring the authentication flow.",
        focus_file="app/services/auth_service.py",
        last_activity_timestamp=now
    )
    await set_agent_state(chat_id, project_name, state_to_save)

    # 3. ดึง state ที่บันทึกไว้กลับมา
    retrieved_state = await get_agent_state(chat_id, project_name)

    # 4. ตรวจสอบว่า state ที่ได้กลับมาเป็น instance ของ AgentState และมีข้อมูลถูกต้อง
    assert isinstance(retrieved_state, AgentState)
    assert retrieved_state.current_task == state_to_save.current_task
    assert retrieved_state.focus_file == state_to_save.focus_file
    # เปรียบเทียบ timestamp โดยแปลงเป็น isoformat
    assert retrieved_state.last_activity_timestamp.isoformat() == now.isoformat()

    # 5. ตรวจสอบว่าโปรเจ็กต์อื่นไม่มี state
    other_project_state = await get_agent_state(chat_id, "another-project")
    assert other_project_state is None
