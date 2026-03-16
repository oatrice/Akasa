"""
Unit tests for Timeout Watcher Service — AI Agent Timeout Observer Feature
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.timeout_watcher_service import TimeoutWatcher
from app.models.agent_task import AgentTaskLog


class TestTimeoutWatcher:
    """Tests for TimeoutWatcher class."""

    def test_init(self):
        """Test TimeoutWatcher initialization."""
        watcher = TimeoutWatcher()
        assert watcher._running is False
        assert watcher._task is None

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test starting and stopping the watcher."""
        watcher = TimeoutWatcher()

        # Start the watcher
        await watcher.start()
        assert watcher._running is True
        assert watcher._task is not None

        # Stop the watcher
        await watcher.stop()
        assert watcher._running is False
        assert watcher._task is None

    @pytest.mark.asyncio
    async def test_start_when_already_running(self):
        """Test that starting an already running watcher is a no-op."""
        watcher = TimeoutWatcher()

        await watcher.start()
        first_task = watcher._task

        # Start again - should be ignored
        await watcher.start()
        assert watcher._task == first_task

        await watcher.stop()

    @pytest.mark.asyncio
    async def test_check_timeouts_no_tasks(self):
        """Test _check_timeouts when no tasks are timed out."""
        watcher = TimeoutWatcher()

        with patch('app.services.timeout_watcher_service.find_timed_out_tasks') as mock_find:
            mock_find.return_value = []

            await watcher._check_timeouts()

            mock_find.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_timeouts_with_timed_out_tasks(self):
        """Test _check_timeouts when tasks are timed out."""
        watcher = TimeoutWatcher()

        old_time = (
            (datetime.now(timezone.utc) - timedelta(minutes=20))
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
        timed_out_task = AgentTaskLog(
            task_id="task_timeout",
            project="TestProject",
            task="Timed out task",
            status="starting",
            started_at=old_time,
            chat_id="123456",
        )

        with patch('app.services.timeout_watcher_service.find_timed_out_tasks') as mock_find:
            with patch('app.services.timeout_watcher_service.mark_task_timed_out') as mock_mark:
                with patch.object(watcher, '_send_timeout_alert') as mock_alert:
                    mock_find.return_value = [timed_out_task]
                    mock_mark.return_value = timed_out_task

                    await watcher._check_timeouts()

                    mock_find.assert_called_once()
                    mock_mark.assert_called_once_with("task_timeout")
                    mock_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_timeout_alert_success(self):
        """Test sending a timeout alert via Telegram."""
        watcher = TimeoutWatcher()

        old_time = (
            (datetime.now(timezone.utc) - timedelta(minutes=20))
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
        task_log = AgentTaskLog(
            task_id="task_alert",
            project="AlertProject",
            task="Task that timed out",
            status="starting",
            started_at=old_time,
            source="Antigravity IDE",
            chat_id="123456",
        )

        with patch('app.services.timeout_watcher_service.tg_service') as mock_tg:
            mock_tg.send_message = AsyncMock()
            
            await watcher._send_timeout_alert(task_log)

            mock_tg.send_message.assert_called_once()
            call_kwargs = mock_tg.send_message.call_args.kwargs
            assert call_kwargs["chat_id"] == 123456
            assert r"AI Agent Timeout\!" in call_kwargs.get("text", "")

    @pytest.mark.asyncio
    async def test_send_timeout_alert_no_chat_id(self):
        """Test that alert is skipped when no chat_id is available."""
        watcher = TimeoutWatcher()

        task_log = AgentTaskLog(
            task_id="task_no_chat",
            project="TestProject",
            task="Task without chat_id",
            status="starting",
            chat_id=None,
        )

        with patch('app.services.timeout_watcher_service.settings') as mock_settings:
            mock_settings.AKASA_CHAT_ID = ""

            await watcher._send_timeout_alert(task_log)
            # Should not raise an error, just log a warning

    @pytest.mark.asyncio
    async def test_send_timeout_alert_invalid_chat_id(self):
        """Test handling of invalid chat_id."""
        watcher = TimeoutWatcher()

        task_log = AgentTaskLog(
            task_id="task_invalid_chat",
            project="TestProject",
            task="Task with invalid chat_id",
            status="starting",
            chat_id="not_a_number",
        )

        await watcher._send_timeout_alert(task_log)
        # Should not raise an error, just log an error

    @pytest.mark.asyncio
    async def test_cleanup_indices(self):
        """Test _cleanup_indices calls the cleanup function."""
        watcher = TimeoutWatcher()

        with patch('app.services.timeout_watcher_service.cleanup_expired_task_indices') as mock_cleanup:
            mock_cleanup.return_value = 5

            await watcher._cleanup_indices()

            mock_cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_loop_runs_check_before_waiting(self):
        """Test that the run loop runs check and cleanup before waiting for interval."""
        watcher = TimeoutWatcher()
        watcher._running = True
        watcher._stop_event = asyncio.Event()  # Initialize the stop_event

        # Run one iteration - the loop will run check/cleanup, then wait_for will
        # either timeout or be interrupted by stop_event
        with patch.object(watcher, '_check_timeouts') as mock_check:
            with patch.object(watcher, '_cleanup_indices') as mock_cleanup:
                with patch('app.services.timeout_watcher_service.settings') as mock_settings:
                    mock_settings.AGENT_TIMEOUT_CHECK_INTERVAL_MINUTES = 5

                    # Set stop_event after a short delay to simulate one iteration
                    async def set_stop_after_delay():
                        await asyncio.sleep(0.01)
                        watcher._stop_event.set()

                    asyncio.create_task(set_stop_after_delay())

                    await watcher._run_loop()

                    # Should have called check and cleanup once
                    mock_check.assert_called_once()
                    mock_cleanup.assert_called_once()


class TestTimeoutWatcherIntegration:
    """Integration tests for TimeoutWatcher with settings."""

    @pytest.mark.asyncio
    async def test_uses_settings_for_interval(self):
        """Test that the watcher uses settings for check interval."""
        watcher = TimeoutWatcher()

        with patch('app.services.timeout_watcher_service.settings') as mock_settings:
            mock_settings.AGENT_TIMEOUT_CHECK_INTERVAL_MINUTES = 1
            mock_settings.AGENT_TIMEOUT_THRESHOLD_MINUTES = 5

            await watcher.start()

            assert watcher._running is True

            await watcher.stop()
