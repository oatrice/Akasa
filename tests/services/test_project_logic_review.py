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


# --- Test Project Rename with History Migration ---

@pytest.mark.asyncio
async def test_rename_project_migrates_history(patch_redis):
    """ทดสอบว่าเมื่อ Rename โปรเจ็กต์ ประวัติแชทต้องถูกย้ายตามไปด้วย (Fixing bug from code_review.md)"""
    from app.services.redis_service import add_message_to_history, get_chat_history, rename_project
    
    chat_id = 100
    old_name = "old-project"
    new_name = "new-project"
    
    # 1. บันทึกข้อมูลในโปรเจ็กต์เก่า
    await add_message_to_history(chat_id, "user", "History message", project_name=old_name)
    
    # 2. ทำการ Rename
    # หมายเหตุ: ปัจจุบัน rename_project ยังไม่มี ต้อง Implement ใน Green step
    await rename_project(chat_id, old_name, new_name)
    
    # 3. ตรวจสอบผลลัพธ์
    old_history = await get_chat_history(chat_id, project_name=old_name)
    new_history = await get_chat_history(chat_id, project_name=new_name)
    
    assert len(old_history) == 0  # ข้อมูลเก่าต้องหายไป
    assert len(new_history) == 1  # ข้อมูลต้องมาอยู่ที่ใหม่
    assert new_history[0]["content"] == "History message"


# --- Test Usage Message (Part 1 of Test Suggestion) ---

@pytest.mark.asyncio
async def test_project_usage_message(patch_redis):
    """ทดสอบว่าคำสั่ง /project เฉยๆ ต้องแสดงวิธีใช้ที่มี select, new, rename"""
    # งานนี้ต้องรันผ่าน ChatService
    from app.services.chat_service import _handle_project_command
    from unittest.mock import AsyncMock
    import app.services.chat_service as cs
    
    mock_send = AsyncMock()
    cs._send_response = mock_send
    
    await _handle_project_command(chat_id=200, args=[])
    
    # ดึงข้อความที่ส่ง
    sent_msg = mock_send.call_args[0][1]
    assert "select" in sent_msg
    assert "new" in sent_msg
    assert "rename" in sent_msg


# --- Test Error Handling (Part 4 of Test Suggestion) ---

@pytest.mark.asyncio
async def test_project_invalid_subcommand(patch_redis):
    """ทดสอบกรณีใส่ Subcommand ผิด (เช่น /project switch ...)"""
    from app.services.chat_service import _handle_project_command
    from unittest.mock import AsyncMock
    import app.services.chat_service as cs
    
    mock_send = AsyncMock()
    cs._send_response = mock_send
    
    # ลองใช้ 'switch' แทน 'select'
    await _handle_project_command(chat_id=300, args=["switch", "project-a"])
    
    sent_msg = mock_send.call_args[0][1]
    assert "❌ Invalid usage" in sent_msg
