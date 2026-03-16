# Celery vs FastAPI BackgroundTasks — Trade-off Reference

*Discussed during implementation of Issue #33 (Async Deployment Service)*

---

## Quick Summary

| Concern | FastAPI BackgroundTasks | Celery |
|---|---|---|
| Setup | ✅ Zero — built into FastAPI | ❌ Broker (Redis/RabbitMQ) + worker process |
| Task persistence | ❌ Lost if worker crashes | ✅ Survives crashes (stored in broker) |
| Retry mechanism | ❌ Manual only | ✅ Built-in with exponential backoff |
| Monitoring | ❌ No visibility | ✅ Flower dashboard, `celery inspect` |
| Scale workers independently | ❌ Tied to API process | ✅ Run N API + M worker processes |
| Concurrency control | ❌ No queue depth / rate limit | ✅ Per-task concurrency, priority queues |
| Scheduled tasks | ❌ Not supported | ✅ Celery Beat |
| Debugging | ✅ Same process, same logs | ❌ Separate process, separate logs |
| Serialization constraint | ✅ None — any Python object | ❌ Args must be JSON-serializable |
| Dependencies added | ✅ None | ❌ `celery`, broker client, worker config |

---

## How FastAPI BackgroundTasks Works

```python
@router.post("/deployments", status_code=202)
async def start_deployment(
    payload: DeploymentRequest,
    background_tasks: BackgroundTasks,
):
    record = await create_deployment(...)
    background_tasks.add_task(run_deployment, record.deployment_id, notify_callback)
    return DeploymentResponse(deployment_id=record.deployment_id, status="pending")
```

- Task is added to an internal queue after the HTTP response is sent
- Runs in the **same event loop** as the FastAPI application
- If the uvicorn worker process dies, the task dies with it — no recovery
- No built-in way to list running tasks, cancel them, or retry failures

---

## How Celery Works

```python
# tasks.py
from celery import Celery

app = Celery("akasa", broker="redis://localhost:6379/0", backend="redis://localhost:6379/1")

@app.task(autoretry_for=(Exception,), max_retries=3, countdown=5)
def run_deployment_task(deployment_id: str, chat_id: str):
    ...
```

```python
# router — fire and forget
@router.post("/deployments", status_code=202)
async def start_deployment(payload: DeploymentRequest):
    record = await create_deployment(...)
    run_deployment_task.delay(record.deployment_id, payload.chat_id)
    return DeploymentResponse(...)
```

- Task is serialized and pushed to the broker (Redis/RabbitMQ)
- A separate **worker process** picks it up and executes it
- If the worker crashes mid-task, Celery can re-queue it on restart
- Tasks are visible via Flower (`celery flower`) or `celery inspect active`

---

## The Critical Risk with BackgroundTasks: Orphaned Deployments

This is the most important production concern for the current implementation.

**Scenario:**
1. Client POSTs to `/api/v1/deployments` — deployment starts, status = `"running"` in Redis
2. The `vercel deploy` command takes 3 minutes
3. At minute 2, the uvicorn worker process is killed (OOM, deploy restart, crash)
4. The background task is gone — nothing updates Redis
5. Status stays `"running"` in Redis for 24 hours (TTL) — never becomes `"success"` or `"failed"`
6. No Telegram notification is sent
7. Any client polling `GET /api/v1/deployments/{id}` sees `"running"` forever

**With Celery:** The broker retains the task. When the worker restarts, it re-picks the task and retries from the beginning (or from a checkpoint if implemented).

**Current mitigation:** None. The `started_at` timestamp is stored, so a future sweep job could detect deployments stuck in `"running"` beyond a reasonable timeout and mark them as `"failed"`.

---

## Decision for Akasa (Issue #33)

**Chosen:** FastAPI BackgroundTasks

**Rationale:**
- Current usage: few developers, deployments are infrequent and not automated
- Adding Celery would require running a separate worker process in production (extra Render/Railway service), a Redis instance configured as both a cache and a broker, and more complex local dev setup
- The `plan.md` originally specified Celery, but `analysis.md` explicitly noted "FastAPI BackgroundTasks are sufficient for Normal load"
- Redis-backed `DeploymentRecord` provides task state visibility that partially compensates for the lack of a task queue

**Migration trigger:** Consider migrating to Celery when any of these become true:
- Deployments run concurrently (> 3 at a time)
- Automatic retry on transient failures is required
- Deployment commands routinely take > 5 minutes (orphan risk increases)
- A monitoring dashboard for task history is needed

---

## Migration Path (BackgroundTasks → Celery)

If migration becomes necessary, the changeset is contained:

1. **Add dependencies:** `celery[redis]` to `requirements.txt`
2. **Create `celery_app.py`:** Initialize Celery with Redis broker/backend
3. **Move `run_deployment()`** from `deploy_service.py` into a `@app.task`-decorated function in `tasks/deployment_tasks.py`
4. **Update router:** Replace `background_tasks.add_task(...)` with `run_deployment_task.delay(...)`
5. **Update `docker-compose.yml`:** Add a `celery-worker` service
6. **Remove Redis state management** for task status (use Celery's result backend instead, or keep custom Redis if richer status fields are needed)

The `DeploymentRecord` model, `save_deployment`/`get_deployment` helpers, and the Telegram notification callback can remain unchanged — they are independent of the task execution mechanism.

---

## Further Reading

- [FastAPI BackgroundTasks docs](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [Celery docs — First Steps](https://docs.celeryq.dev/en/stable/getting-started/first-steps-with-celery.html)
- [Celery with FastAPI — integration guide](https://docs.celeryq.dev/en/stable/userguide/routing.html)
- [Flower — Celery monitoring tool](https://flower.readthedocs.io/en/latest/)