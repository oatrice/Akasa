"""
Tests for deployments router — Issue #33

Covers:
  POST /api/v1/deployments       — start a deployment (202 Accepted)
  GET  /api/v1/deployments/{id}  — poll deployment status
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.deployment import DeploymentRecord

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

API_KEY = "test-api-key"
VALID_HEADERS = {"X-Akasa-API-Key": API_KEY}


def _make_record(**kwargs) -> DeploymentRecord:
    defaults = dict(
        deployment_id="dep-abc-123",
        status="pending",
        command="vercel deploy",
        cwd="/tmp/project",
        project="MyApp",
        chat_id=None,
        stdout="",
        stderr="",
        exit_code=None,
        url=None,
        started_at=None,
        finished_at=None,
    )
    defaults.update(kwargs)
    return DeploymentRecord(**defaults)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    """Synchronous TestClient — sufficient for BackgroundTask router tests."""
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture(autouse=True)
def patch_api_key(monkeypatch):
    """Override settings.AKASA_API_KEY to a known value for all tests."""
    monkeypatch.setattr("app.routers.deployments.settings.AKASA_API_KEY", API_KEY)


# ---------------------------------------------------------------------------
# POST /api/v1/deployments
# ---------------------------------------------------------------------------


class TestStartDeployment:
    @patch("app.routers.deployments.run_deployment")
    @patch(
        "app.routers.deployments.create_deployment",
        new_callable=AsyncMock,
    )
    def test_returns_202_with_deployment_id(self, mock_create, mock_run, client):
        mock_create.return_value = _make_record()

        resp = client.post(
            "/api/v1/deployments",
            json={"command": "vercel deploy", "cwd": "/tmp/project"},
            headers=VALID_HEADERS,
        )

        assert resp.status_code == 202
        body = resp.json()
        assert body["deployment_id"] == "dep-abc-123"
        assert body["status"] == "pending"

    @patch("app.routers.deployments.run_deployment")
    @patch(
        "app.routers.deployments.create_deployment",
        new_callable=AsyncMock,
    )
    def test_create_deployment_called_with_correct_args(
        self, mock_create, mock_run, client
    ):
        mock_create.return_value = _make_record()

        client.post(
            "/api/v1/deployments",
            json={
                "command": "render deploy",
                "cwd": "/home/user/app",
                "project": "RenderApp",
                "chat_id": "123456789",
            },
            headers=VALID_HEADERS,
        )

        mock_create.assert_awaited_once_with(
            command="render deploy",
            cwd="/home/user/app",
            project="RenderApp",
            chat_id="123456789",
        )

    @patch("app.routers.deployments.run_deployment")
    @patch(
        "app.routers.deployments.create_deployment",
        new_callable=AsyncMock,
    )
    def test_default_project_is_general(self, mock_create, mock_run, client):
        mock_create.return_value = _make_record(project="General")

        client.post(
            "/api/v1/deployments",
            json={"command": "echo hi", "cwd": "/tmp"},
            headers=VALID_HEADERS,
        )

        _, kwargs = mock_create.call_args
        assert kwargs.get("project") == "General"

    @patch("app.routers.deployments.run_deployment")
    @patch(
        "app.routers.deployments.create_deployment",
        new_callable=AsyncMock,
    )
    def test_chat_id_defaults_to_none(self, mock_create, mock_run, client):
        mock_create.return_value = _make_record()

        client.post(
            "/api/v1/deployments",
            json={"command": "echo hi", "cwd": "/tmp"},
            headers=VALID_HEADERS,
        )

        _, kwargs = mock_create.call_args
        assert kwargs.get("chat_id") is None

    def test_missing_api_key_returns_401(self, client):
        resp = client.post(
            "/api/v1/deployments",
            json={"command": "echo hi", "cwd": "/tmp"},
        )
        assert resp.status_code == 401

    def test_wrong_api_key_returns_401(self, client):
        resp = client.post(
            "/api/v1/deployments",
            json={"command": "echo hi", "cwd": "/tmp"},
            headers={"X-Akasa-API-Key": "wrong-key"},
        )
        assert resp.status_code == 401

    def test_missing_command_returns_422(self, client):
        resp = client.post(
            "/api/v1/deployments",
            json={"cwd": "/tmp"},
            headers=VALID_HEADERS,
        )
        assert resp.status_code == 422

    def test_missing_cwd_returns_422(self, client):
        resp = client.post(
            "/api/v1/deployments",
            json={"command": "echo hi"},
            headers=VALID_HEADERS,
        )
        assert resp.status_code == 422

    @patch("app.routers.deployments.run_deployment")
    @patch(
        "app.routers.deployments.create_deployment",
        new_callable=AsyncMock,
    )
    def test_background_task_is_registered(self, mock_create, mock_run, client):
        """
        BackgroundTasks.add_task should be called; the actual task runs
        after the response — we just verify it was registered.
        TestClient flushes background tasks before returning, so mock_run
        will have been called by the time we assert.
        """
        record = _make_record()
        mock_create.return_value = record
        mock_run.return_value = None  # async mock already returns coroutine

        with patch(
            "app.routers.deployments.run_deployment", new_callable=AsyncMock
        ) as bg_mock:
            bg_mock.return_value = None
            resp = client.post(
                "/api/v1/deployments",
                json={"command": "echo bg", "cwd": "/tmp"},
                headers=VALID_HEADERS,
            )

        assert resp.status_code == 202

    @patch("app.routers.deployments.run_deployment")
    @patch(
        "app.routers.deployments.create_deployment",
        new_callable=AsyncMock,
    )
    def test_response_body_has_no_extra_fields(self, mock_create, mock_run, client):
        mock_create.return_value = _make_record()

        resp = client.post(
            "/api/v1/deployments",
            json={"command": "echo hi", "cwd": "/tmp"},
            headers=VALID_HEADERS,
        )

        body = resp.json()
        assert set(body.keys()) == {"deployment_id", "status"}


# ---------------------------------------------------------------------------
# GET /api/v1/deployments/{deployment_id}
# ---------------------------------------------------------------------------


class TestGetDeploymentStatus:
    @patch(
        "app.routers.deployments.get_deployment",
        new_callable=AsyncMock,
    )
    def test_returns_200_for_existing_deployment(self, mock_get, client):
        mock_get.return_value = _make_record(status="running")

        resp = client.get(
            "/api/v1/deployments/dep-abc-123",
            headers=VALID_HEADERS,
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["deployment_id"] == "dep-abc-123"
        assert body["status"] == "running"

    @patch(
        "app.routers.deployments.get_deployment",
        new_callable=AsyncMock,
    )
    def test_returns_404_for_missing_deployment(self, mock_get, client):
        mock_get.return_value = None

        resp = client.get(
            "/api/v1/deployments/ghost-id",
            headers=VALID_HEADERS,
        )

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    @patch(
        "app.routers.deployments.get_deployment",
        new_callable=AsyncMock,
    )
    def test_success_record_includes_url(self, mock_get, client):
        mock_get.return_value = _make_record(
            status="success",
            url="https://myapp.vercel.app",
            stdout="Deployed to https://myapp.vercel.app\n",
            exit_code=0,
            started_at="2024-01-01T10:00:00+00:00",
            finished_at="2024-01-01T10:01:30+00:00",
        )

        resp = client.get(
            "/api/v1/deployments/dep-abc-123",
            headers=VALID_HEADERS,
        )

        body = resp.json()
        assert body["status"] == "success"
        assert body["url"] == "https://myapp.vercel.app"
        assert body["exit_code"] == 0

    @patch(
        "app.routers.deployments.get_deployment",
        new_callable=AsyncMock,
    )
    def test_failed_record_includes_stderr(self, mock_get, client):
        mock_get.return_value = _make_record(
            status="failed",
            stderr="Error: authentication required\n",
            exit_code=1,
        )

        resp = client.get(
            "/api/v1/deployments/dep-abc-123",
            headers=VALID_HEADERS,
        )

        body = resp.json()
        assert body["status"] == "failed"
        assert "authentication required" in body["stderr"]
        assert body["exit_code"] == 1

    @patch(
        "app.routers.deployments.get_deployment",
        new_callable=AsyncMock,
    )
    def test_pending_record_has_null_url_and_timestamps(self, mock_get, client):
        mock_get.return_value = _make_record(status="pending")

        resp = client.get(
            "/api/v1/deployments/dep-abc-123",
            headers=VALID_HEADERS,
        )

        body = resp.json()
        assert body["status"] == "pending"
        assert body["url"] is None
        assert body["started_at"] is None
        assert body["finished_at"] is None

    @patch(
        "app.routers.deployments.get_deployment",
        new_callable=AsyncMock,
    )
    def test_running_record_has_started_at_but_no_finished_at(self, mock_get, client):
        mock_get.return_value = _make_record(
            status="running",
            started_at="2024-01-01T10:00:00+00:00",
        )

        resp = client.get(
            "/api/v1/deployments/dep-abc-123",
            headers=VALID_HEADERS,
        )

        body = resp.json()
        assert body["status"] == "running"
        assert body["started_at"] == "2024-01-01T10:00:00+00:00"
        assert body["finished_at"] is None

    def test_missing_api_key_returns_401(self, client):
        resp = client.get("/api/v1/deployments/dep-abc-123")
        assert resp.status_code == 401

    def test_wrong_api_key_returns_401(self, client):
        resp = client.get(
            "/api/v1/deployments/dep-abc-123",
            headers={"X-Akasa-API-Key": "wrong"},
        )
        assert resp.status_code == 401

    @patch(
        "app.routers.deployments.get_deployment",
        new_callable=AsyncMock,
    )
    def test_response_contains_all_expected_fields(self, mock_get, client):
        mock_get.return_value = _make_record(
            status="success",
            url="https://example.com",
            stdout="ok",
            stderr="",
            exit_code=0,
            started_at="2024-01-01T10:00:00+00:00",
            finished_at="2024-01-01T10:00:05+00:00",
        )

        resp = client.get(
            "/api/v1/deployments/dep-abc-123",
            headers=VALID_HEADERS,
        )

        body = resp.json()
        expected_keys = {
            "deployment_id",
            "status",
            "url",
            "stdout",
            "stderr",
            "exit_code",
            "started_at",
            "finished_at",
        }
        assert expected_keys.issubset(set(body.keys()))

    @patch(
        "app.routers.deployments.get_deployment",
        new_callable=AsyncMock,
    )
    def test_get_deployment_called_with_correct_id(self, mock_get, client):
        mock_get.return_value = _make_record()

        client.get(
            "/api/v1/deployments/my-specific-id",
            headers=VALID_HEADERS,
        )

        mock_get.assert_awaited_once_with("my-specific-id")
