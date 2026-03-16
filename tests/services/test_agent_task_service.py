"""
Unit tests for Agent Task Service — AI Agent Timeout Observer Feature
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from app.models.agent_task import AgentTaskLog, AgentTaskStatus
from app.services import agent_task_service


class TestAgentTaskLog:
    """Tests for AgentTaskLog model."""

    def test_create_task_log_defaults(self):
        """Test creating a task log with default values."""
        task_log = AgentTaskLog(
            task_id="task_123",
            task="Test task",
        )

        assert task_log.task_id == "task_123"
        assert task_log.project == "General"
        assert task_log.status == "starting"
        assert task_log.started_at is not None
        assert task_log.completed_at is None

    def test_create_task_log_with_all_fields(self):
        """Test creating a task log with all fields."""
        task_log = AgentTaskLog(
            task_id="task_456",
            project="Akasa",
            task="Implement timeout feature",
            status="starting",
            source="Antigravity IDE",
            chat_id="123456",
        )

        assert task_log.task_id == "task_456"
        assert task_log.project == "Akasa"
        assert task_log.source == "Antigravity IDE"
        assert task_log.chat_id == "123456"

    def test_is_timed_out_starting_status(self):
        """Test timeout detection for starting status."""
        # Task that just started - should NOT be timed out
        task_log = AgentTaskLog(
            task_id="task_new",
            task="New task",
            status="starting",
        )
        assert task_log.is_timed_out(15) is False

    def test_is_timed_out_exceeded_threshold(self):
        """Test timeout detection when threshold is exceeded."""
        # Task that started 20 minutes ago
        old_time = (
            (datetime.now(timezone.utc) - timedelta(minutes=20))
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
        task_log = AgentTaskLog(
            task_id="task_old",
            task="Old task",
            status="starting",
            started_at=old_time,
        )
        assert task_log.is_timed_out(15) is True

    def test_is_timed_out_completed_status(self):
        """Test that completed tasks are never timed out."""
        old_time = (
            (datetime.now(timezone.utc) - timedelta(minutes=30))
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
        task_log = AgentTaskLog(
            task_id="task_done",
            task="Done task",
            status="success",
            started_at=old_time,
        )
        assert task_log.is_timed_out(15) is False

    def test_mark_timeout(self):
        """Test marking a task as timed out."""
        task_log = AgentTaskLog(
            task_id="task_timeout",
            task="Timeout task",
            status="starting",
        )

        result = task_log.mark_timeout()

        assert result.status == "timeout"
        assert result.completed_at is not None

    def test_mark_completed(self):
        """Test marking a task as completed."""
        task_log = AgentTaskLog(
            task_id="task_complete",
            task="Complete task",
            status="starting",
        )

        result = task_log.mark_completed("success")

        assert result.status == "success"
        assert result.completed_at is not None


class TestAgentTaskService:
    """Tests for agent_task_service functions."""

    @pytest.mark.asyncio
    async def test_create_task(self):
        """Test creating a task in Redis."""
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock()
        mock_redis.sadd = AsyncMock()

        with patch.object(agent_task_service, 'redis_pool', mock_redis):
            task_log = await agent_task_service.create_task(
                project="TestProject",
                task="Test task description",
                source="TestAgent",
                chat_id="123456",
            )

            assert task_log.project == "TestProject"
            assert task_log.task == "Test task description"
            assert task_log.status == "starting"
            assert task_log.task_id.startswith("task_")

            # Verify Redis calls
            mock_redis.set.assert_called_once()
            mock_redis.sadd.assert_called()

    @pytest.mark.asyncio
    async def test_create_task_with_custom_id(self):
        """Test creating a task with a custom task ID."""
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock()
        mock_redis.sadd = AsyncMock()

        with patch.object(agent_task_service, 'redis_pool', mock_redis):
            task_log = await agent_task_service.create_task(
                project="TestProject",
                task="Test task",
                task_id="custom_task_123",
            )

            assert task_log.task_id == "custom_task_123"

    @pytest.mark.asyncio
    async def test_update_task_success(self):
        """Test updating a task status."""
        existing_task = AgentTaskLog(
            task_id="task_update",
            project="TestProject",
            task="Task to update",
            status="starting",
        )

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=existing_task.model_dump_json())
        mock_redis.set = AsyncMock()
        mock_redis.ttl = AsyncMock(return_value=3600)
        mock_redis.srem = AsyncMock()

        with patch.object(agent_task_service, 'redis_pool', mock_redis):
            result = await agent_task_service.update_task(
                task_id="task_update",
                status="success",
                duration="5m 30s",
                message="Task completed successfully",
            )

            assert result is not None
            assert result.status == "success"
            assert result.duration == "5m 30s"
            assert result.completed_at is not None

            # Verify task removed from active index
            mock_redis.srem.assert_called()

    @pytest.mark.asyncio
    async def test_update_task_not_found(self):
        """Test updating a task that doesn't exist."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        with patch.object(agent_task_service, 'redis_pool', mock_redis):
            result = await agent_task_service.update_task(
                task_id="nonexistent",
                status="success",
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_get_task(self):
        """Test retrieving a task."""
        task_log = AgentTaskLog(
            task_id="task_get",
            project="TestProject",
            task="Task to get",
            status="starting",
        )

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=task_log.model_dump_json())

        with patch.object(agent_task_service, 'redis_pool', mock_redis):
            result = await agent_task_service.get_task("task_get")

            assert result is not None
            assert result.task_id == "task_get"

    @pytest.mark.asyncio
    async def test_get_task_not_found(self):
        """Test retrieving a task that doesn't exist."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        with patch.object(agent_task_service, 'redis_pool', mock_redis):
            result = await agent_task_service.get_task("nonexistent")

            assert result is None

    @pytest.mark.asyncio
    async def test_get_active_tasks(self):
        """Test getting all active tasks."""
        task1 = AgentTaskLog(
            task_id="task_active_1",
            task="Active task 1",
            status="starting",
        )
        task2 = AgentTaskLog(
            task_id="task_active_2",
            task="Active task 2",
            status="starting",
        )

        mock_redis = AsyncMock()
        mock_redis.smembers = AsyncMock(
            return_value={"task_active_1", "task_active_2"}
        )
        mock_redis.get = AsyncMock(
            side_effect=[
                task1.model_dump_json(),
                task2.model_dump_json(),
            ]
        )

        with patch.object(agent_task_service, 'redis_pool', mock_redis):
            result = await agent_task_service.get_active_tasks()

            assert len(result) == 2
            assert all(t.status == "starting" for t in result)

    @pytest.mark.asyncio
    async def test_find_timed_out_tasks(self):
        """Test finding timed out tasks."""
        # Create a task that started 20 minutes ago
        old_time = (
            (datetime.now(timezone.utc) - timedelta(minutes=20))
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
        old_task = AgentTaskLog(
            task_id="task_timed_out",
            task="Timed out task",
            status="starting",
            started_at=old_time,
        )
        new_task = AgentTaskLog(
            task_id="task_active",
            task="Active task",
            status="starting",
        )

        mock_redis = AsyncMock()
        mock_redis.smembers = AsyncMock(
            return_value={"task_timed_out", "task_active"}
        )
        mock_redis.get = AsyncMock(
            side_effect=[
                old_task.model_dump_json(),
                new_task.model_dump_json(),
            ]
        )

        with patch.object(agent_task_service, 'redis_pool', mock_redis):
            with patch('app.services.agent_task_service.settings') as mock_settings:
                mock_settings.AGENT_TIMEOUT_THRESHOLD_MINUTES = 15
                result = await agent_task_service.find_timed_out_tasks()

                assert len(result) == 1
                assert result[0].task_id == "task_timed_out"

    @pytest.mark.asyncio
    async def test_cleanup_expired_task_indices(self):
        """Test cleaning up expired task IDs from indices."""
        mock_redis = AsyncMock()
        mock_redis.smembers = AsyncMock(
            return_value={"expired_task_1", "expired_task_2"}
        )
        mock_redis.exists = AsyncMock(side_effect=[0, 0])  # Both expired
        mock_redis.srem = AsyncMock()

        with patch.object(agent_task_service, 'redis_pool', mock_redis):
            removed = await agent_task_service.cleanup_expired_task_indices()

            assert removed == 2
            assert mock_redis.srem.call_count == 2
