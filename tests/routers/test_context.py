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
    ), patch(
        "app.routers.context.redis_service.get_owner_project_path",
        new_callable=AsyncMock,
        return_value=None,
    ), patch(
        "app.routers.context.redis_service.get_owner_project_repo",
        new_callable=AsyncMock,
        return_value=None,
    ):
        response = client.get(CONTEXT_URL, headers={"X-Akasa-API-Key": "valid-key"})

    assert response.status_code == 200
    assert response.json() == {"active_project": "akasa"}


@pytest.mark.asyncio
async def test_get_context_success_includes_project_path():
    app.dependency_overrides[verify_api_key] = lambda: True

    with patch(
        "app.routers.context.redis_service.get_owner_current_project",
        new_callable=AsyncMock,
        return_value="akasa",
    ), patch(
        "app.routers.context.redis_service.get_owner_project_path",
        new_callable=AsyncMock,
        return_value="/Users/oatrice/Software-projects/Akasa",
    ), patch(
        "app.routers.context.redis_service.get_owner_project_repo",
        new_callable=AsyncMock,
        return_value=None,
    ):
        response = client.get(CONTEXT_URL, headers={"X-Akasa-API-Key": "valid-key"})

    assert response.status_code == 200
    assert response.json() == {
        "active_project": "akasa",
        "project_path": "/Users/oatrice/Software-projects/Akasa",
    }


@pytest.mark.asyncio
async def test_get_context_success_includes_project_path_and_repo():
    app.dependency_overrides[verify_api_key] = lambda: True

    with patch(
        "app.routers.context.redis_service.get_owner_current_project",
        new_callable=AsyncMock,
        return_value="akasa",
    ), patch(
        "app.routers.context.redis_service.get_owner_project_path",
        new_callable=AsyncMock,
        return_value="/Users/oatrice/Software-projects/Akasa",
    ), patch(
        "app.routers.context.redis_service.get_owner_project_repo",
        new_callable=AsyncMock,
        return_value="oatrice/Akasa",
    ):
        response = client.get(CONTEXT_URL, headers={"X-Akasa-API-Key": "valid-key"})

    assert response.status_code == 200
    assert response.json() == {
        "active_project": "akasa",
        "project_path": "/Users/oatrice/Software-projects/Akasa",
        "project_repo": "oatrice/Akasa",
    }


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
    ) as mock_set, patch(
        "app.routers.context.redis_service.get_owner_project_path",
        new_callable=AsyncMock,
        return_value=None,
    ), patch(
        "app.routers.context.redis_service.get_owner_project_repo",
        new_callable=AsyncMock,
        return_value=None,
    ):
        response = client.put(
            CONTEXT_URL,
            json={"active_project": "  Docs-Bot  "},
            headers={"X-Akasa-API-Key": "valid-key"},
        )

    assert response.status_code == 200
    assert response.json() == {"active_project": "docs-bot"}
    mock_set.assert_awaited_once_with("docs-bot")


@pytest.mark.asyncio
async def test_put_context_can_bind_project_path():
    app.dependency_overrides[verify_api_key] = lambda: True

    with patch(
        "app.routers.context.redis_service.set_owner_current_project",
        new_callable=AsyncMock,
        return_value="akasa",
    ) as mock_set_project, patch(
        "app.routers.context.redis_service.set_owner_project_path",
        new_callable=AsyncMock,
        return_value="/Users/oatrice/Software-projects/Akasa",
    ) as mock_set_path, patch(
        "app.routers.context.redis_service.get_owner_project_repo",
        new_callable=AsyncMock,
        return_value=None,
    ):
        response = client.put(
            CONTEXT_URL,
            json={
                "active_project": "akasa",
                "project_path": " /Users/oatrice/Software-projects/Akasa ",
            },
            headers={"X-Akasa-API-Key": "valid-key"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "active_project": "akasa",
        "project_path": "/Users/oatrice/Software-projects/Akasa",
    }
    mock_set_project.assert_awaited_once_with("akasa")
    mock_set_path.assert_awaited_once_with(
        "akasa",
        "/Users/oatrice/Software-projects/Akasa",
    )


@pytest.mark.asyncio
async def test_put_context_can_bind_project_path_and_repo():
    app.dependency_overrides[verify_api_key] = lambda: True

    with patch(
        "app.routers.context.redis_service.set_owner_current_project",
        new_callable=AsyncMock,
        return_value="the-middle-way",
    ) as mock_set_project, patch(
        "app.routers.context.redis_service.set_owner_project_path",
        new_callable=AsyncMock,
        return_value="/Users/oatrice/Software-projects/TheMiddleWay",
    ) as mock_set_path, patch(
        "app.routers.context.redis_service.set_owner_project_repo",
        new_callable=AsyncMock,
        return_value="oatrice/TheMiddleWay",
    ) as mock_set_repo:
        response = client.put(
            CONTEXT_URL,
            json={
                "active_project": "the-middle-way",
                "project_path": "/Users/oatrice/Software-projects/TheMiddleWay",
                "project_repo": " oatrice/TheMiddleWay ",
            },
            headers={"X-Akasa-API-Key": "valid-key"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "active_project": "the-middle-way",
        "project_path": "/Users/oatrice/Software-projects/TheMiddleWay",
        "project_repo": "oatrice/TheMiddleWay",
    }
    mock_set_project.assert_awaited_once_with("the-middle-way")
    mock_set_path.assert_awaited_once_with(
        "the-middle-way",
        "/Users/oatrice/Software-projects/TheMiddleWay",
    )
    mock_set_repo.assert_awaited_once_with(
        "the-middle-way",
        "oatrice/TheMiddleWay",
    )


def test_put_context_invalid_empty_project():
    app.dependency_overrides[verify_api_key] = lambda: True

    response = client.put(
        CONTEXT_URL,
        json={"active_project": "   "},
        headers={"X-Akasa-API-Key": "valid-key"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_put_context_invalid_project_path_returns_400():
    app.dependency_overrides[verify_api_key] = lambda: True

    with patch(
        "app.routers.context.redis_service.set_owner_current_project",
        new_callable=AsyncMock,
        return_value="akasa",
    ), patch(
        "app.routers.context.redis_service.set_owner_project_path",
        new_callable=AsyncMock,
        side_effect=ValueError("project_path must be an absolute path"),
    ):
        response = client.put(
            CONTEXT_URL,
            json={"active_project": "akasa", "project_path": "relative/path"},
            headers={"X-Akasa-API-Key": "valid-key"},
        )

    assert response.status_code == 400
    assert "absolute path" in response.json()["detail"]


@pytest.mark.asyncio
async def test_put_context_invalid_project_repo_returns_400():
    app.dependency_overrides[verify_api_key] = lambda: True

    with patch(
        "app.routers.context.redis_service.set_owner_current_project",
        new_callable=AsyncMock,
        return_value="akasa",
    ), patch(
        "app.routers.context.redis_service.get_owner_project_path",
        new_callable=AsyncMock,
        return_value=None,
    ), patch(
        "app.routers.context.redis_service.set_owner_project_repo",
        new_callable=AsyncMock,
        side_effect=ValueError("project_repo must use owner/repo format"),
    ):
        response = client.put(
            CONTEXT_URL,
            json={"active_project": "akasa", "project_repo": "invalid-repo"},
            headers={"X-Akasa-API-Key": "valid-key"},
        )

    assert response.status_code == 400
    assert "owner/repo" in response.json()["detail"]
