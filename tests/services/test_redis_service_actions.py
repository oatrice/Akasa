import pytest
import json
from unittest.mock import AsyncMock, patch
from app.services.redis_service import (
    set_action_request,
    get_action_request,
    set_session_permission,
    has_session_permission
)
from app.models.notification import ActionRequestState

@pytest.mark.asyncio
async def test_action_request_lifecycle():
    """ทดสอบการเก็บและดึงสถานะ Action Request ใน Redis"""
    request_id = "test-req-123"
    state = ActionRequestState(
        command="rm -rf /tmp",
        cwd="/tmp",
        session_id="session-456"
    )
    
    # Mock redis_pool.set and redis_pool.get
    with patch("app.services.redis_service.redis_pool", new_callable=AsyncMock) as mock_redis:
        # 1. ทดสอบการบันทึก
        await set_action_request(request_id, state)
        mock_redis.set.assert_called_once()
        args, kwargs = mock_redis.set.call_args
        assert f"action_request:{request_id}" in args
        
        # 2. ทดสอบการดึงข้อมูล (จำลอง Redis คืนค่า JSON)
        mock_redis.get.return_value = state.model_dump_json()
        fetched_state = await get_action_request(request_id)
        
        assert fetched_state is not None
        assert fetched_state.command == "rm -rf /tmp"
        assert fetched_state.status == "pending"

@pytest.mark.asyncio
async def test_session_permission_lifecycle():
    """ทดสอบการจัดการ Session Permission ใน Redis"""
    session_id = "session-789"
    
    with patch("app.services.redis_service.redis_pool", new_callable=AsyncMock) as mock_redis:
        # 1. ทดสอบการตั้งค่าสิทธิ์ (Session Permission)
        await set_session_permission(session_id, ttl=3600)
        mock_redis.set.assert_called_once()
        args, kwargs = mock_redis.set.call_args
        assert f"session_permission:{session_id}" in args
        assert kwargs["ex"] == 3600
        
        # 2. ทดสอบการเช็คสิทธิ์ (กรณีมีสิทธิ์)
        mock_redis.exists.return_value = 1
        assert await has_session_permission(session_id) is True
        
        # 3. ทดสอบการเช็คสิทธิ์ (กรณีไม่มีสิทธิ์)
        mock_redis.exists.return_value = 0
        assert await has_session_permission("unknown-session") is False
