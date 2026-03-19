from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.notifications import verify_api_key

client = TestClient(app)

CONTEXT_URL = "/api/v1/context/project"


@pytest.fixture(autouse=True)
def cleanup_overrides():
    yield
    app.dependency_overrides = {}


def test_get_context_unauthorized_missing_key():
    response = client.get(CONTEXT_URL)
    assert response.status_code == 401


def test_get_context_unauthorized_wrong_key():
    response = client.get(CONTEXT_URL, headers={"X-Akasa-API-Key": "wrong-key"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_context_success():
    app.dependency_overrides[verify_api_key] = lambda: True

    with patch(
        "app.routers.context.redis_service.get_owner_current_project",
        new_callable=AsyncMock,
        return_value="akasa",
    ):
        response = client.get(CONTEXT_URL, headers={"X-Akasa-API-Key": "valid-key"})

    assert response.status_code == 200
    assert response.json() == {"active_project": "akasa"}


@pytest.mark.asyncio
async def test_get_context_owner_chat_misconfigured():
    app.dependency_overrides[verify_api_key] = lambda: True

    with patch(
        "app.routers.context.redis_service.get_owner_current_project",
        new_callable=AsyncMock,
        side_effect=ValueError("Owner chat is not configured on the server."),
    ):
        response = client.get(CONTEXT_URL, headers={"X-Akasa-API-Key": "valid-key"})

    assert response.status_code == 503
    assert "Owner chat" in response.json()["detail"]


@pytest.mark.asyncio
async def test_put_context_success_and_normalizes_project_name():
    app.dependency_overrides[verify_api_key] = lambda: True

    with patch(
        "app.routers.context.redis_service.set_owner_current_project",
        new_callable=AsyncMock,
        return_value="docs-bot",
    ) as mock_set:
        response = client.put(
            CONTEXT_URL,
            json={"active_project": "  Docs-Bot  "},
            headers={"X-Akasa-API-Key": "valid-key"},
        )

    assert response.status_code == 200
    assert response.json() == {"active_project": "docs-bot"}
    mock_set.assert_awaited_once_with("docs-bot")


def test_put_context_invalid_empty_project():
    app.dependency_overrides[verify_api_key] = lambda: True

    response = client.put(
        CONTEXT_URL,
        json={"active_project": "   "},
        headers={"X-Akasa-API-Key": "valid-key"},
    )

    assert response.status_code == 422

