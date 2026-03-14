import os
import sys

import httpx
import pytest

# เพิ่ม project root เข้า sys.path เพื่อให้ pytest หา module 'app' ได้
sys.path.insert(0, os.path.dirname(__file__))


@pytest.fixture(autouse=True)
def ensure_tg_client_open():
    """
    Reopen tg_service.client before each test if it was closed.

    Root cause: FastAPI lifespan (app/main.py) calls tg_service.client.aclose()
    on app shutdown.  Tests that spin up TestClient(app) trigger that shutdown,
    leaving the shared singleton client in a closed state.  Any subsequent test
    that tries to use the real (or respx-mocked) client then fails with:
        RuntimeError: Cannot send a request, as the client has been closed.

    This fixture detects a closed client and replaces it with a fresh instance
    before the test body runs, making test order irrelevant.
    """
    from app.services.telegram_service import tg_service

    if tg_service.client.is_closed:
        tg_service.client = httpx.AsyncClient()

    yield
