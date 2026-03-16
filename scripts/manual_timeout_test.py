import asyncio
import sys
import os

# Ensure the root of the project is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime, timezone, timedelta
from app.config import settings
from app.models.agent_task import AgentTaskLog
from app.services.redis_service import redis_pool
from app.services.agent_task_service import _task_key, _task_index_key, _project_tasks_key
from app.services.timeout_watcher_service import TimeoutWatcher

async def run_timeout_test():
    old_time = (datetime.now(timezone.utc) - timedelta(minutes=20)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    task_id = "test_timeout_task_999"
    
    # 1. Create task log manually with old timestamp
    task_log = AgentTaskLog(
        task_id=task_id,
        project="Manual Verify",
        task="Test timeout alert logic!",
        status="starting",
        source="Manual Test",
        started_at=old_time,
        chat_id=str(settings.AKASA_CHAT_ID) # Use fallback
    )

    # 2. Store in Redis
    key = _task_key(task_id)
    ttl_seconds = 3600
    await redis_pool.set(key, task_log.model_dump_json(), ex=ttl_seconds)
    await redis_pool.sadd(_task_index_key(), task_id)
    await redis_pool.sadd(_project_tasks_key("Manual Verify"), task_id)
    
    print(f"Created mocked timeout task: {task_id}")
    
    # 3. Trigger Watcher
    print("Triggering check_timeouts()...")
    watcher = TimeoutWatcher()
    try:
        import httpx
        from httpx import HTTPStatusError
        # Actually it's hidden inside _check_timeouts which catches and logs exception. Let's patch logger
        pass
    except Exception as e:
        pass
    
    import logging
    logging.getLogger().setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler(sys.stdout)
    logging.getLogger().addHandler(console_handler)

    class CustomHandler(logging.Handler):
        def emit(self, record):
            if "Client error" in record.getMessage() and hasattr(record, "exc_info") and record.exc_info:
                exc = record.exc_info[1]
                if hasattr(exc, "response"):
                    print(f"Telegram API Response: {exc.response.text}")

    logging.getLogger("app.services.timeout_watcher_service").addHandler(CustomHandler())

    await watcher._check_timeouts()
    print("Timeout check finished. Notification should have been sent to Telegram.")

if __name__ == "__main__":
    asyncio.run(run_timeout_test())
