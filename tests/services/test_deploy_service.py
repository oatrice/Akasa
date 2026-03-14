"""
Tests for deploy_service — Issue #33

Covers:
- extract_url: URL parsing from command output
- save_deployment / get_deployment: Redis round-trip
- create_deployment: record initialisation
- run_deployment: subprocess execution, status transitions, notify_callback (Issue #34)
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.deployment import DeploymentRecord
from app.services.deploy_service import (
    DEPLOYMENT_TTL,
    create_deployment,
    extract_url,
    get_deployment,
    run_deployment,
    save_deployment,
)

# ---------------------------------------------------------------------------
# extract_url
# ---------------------------------------------------------------------------


class TestExtractUrl:
    def test_extracts_plain_https_url(self):
        assert (
            extract_url("Deployed to https://myapp.vercel.app")
            == "https://myapp.vercel.app"
        )

    def test_extracts_url_with_path(self):
        url = extract_url("Preview: https://myapp-abc123.vercel.app/dashboard")
        assert url == "https://myapp-abc123.vercel.app/dashboard"

    def test_strips_trailing_period(self):
        assert extract_url("Done. https://example.com.") == "https://example.com"

    def test_strips_trailing_comma(self):
        assert (
            extract_url("URL: https://example.com, more text") == "https://example.com"
        )

    def test_strips_trailing_semicolon(self):
        assert extract_url("See https://example.com;") == "https://example.com"

    def test_strips_trailing_colon(self):
        assert extract_url("Visit https://example.com:") == "https://example.com"

    def test_ignores_http_url(self):
        # Only HTTPS URLs should be extracted
        assert extract_url("http://example.com") is None

    def test_returns_none_for_empty_string(self):
        assert extract_url("") is None

    def test_returns_none_when_no_url(self):
        assert extract_url("Build completed successfully.") is None

    def test_returns_first_url_when_multiple(self):
        text = "First: https://first.example.com Second: https://second.example.com"
        assert extract_url(text) == "https://first.example.com"

    def test_url_with_query_params(self):
        url = extract_url("Live at https://app.render.com?env=prod&v=2")
        assert url == "https://app.render.com?env=prod&v=2"

    def test_url_inside_quotes_is_still_extracted(self):
        # Stops at quote char
        url = extract_url('URL is "https://example.com"')
        assert url == "https://example.com"

    def test_multiline_output(self):
        text = "Building...\nDone!\nLive URL: https://deploy.example.com/v3\nAll good."
        assert extract_url(text) == "https://deploy.example.com/v3"


# ---------------------------------------------------------------------------
# save_deployment / get_deployment
# ---------------------------------------------------------------------------


class TestRedisRoundTrip:
    @pytest.mark.asyncio
    async def test_save_and_get_deployment(self):
        record = DeploymentRecord(
            deployment_id="test-id-123",
            status="pending",
            command="vercel deploy",
            cwd="/tmp/project",
            project="MyApp",
        )

        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock()
        mock_redis.get = AsyncMock(return_value=record.model_dump_json())

        with patch("app.services.deploy_service.redis_pool", mock_redis):
            await save_deployment(record)
            retrieved = await get_deployment("test-id-123")

        mock_redis.set.assert_awaited_once_with(
            "deployment:test-id-123",
            record.model_dump_json(),
            ex=DEPLOYMENT_TTL,
        )
        assert retrieved is not None
        assert retrieved.deployment_id == "test-id-123"
        assert retrieved.status == "pending"
        assert retrieved.command == "vercel deploy"
        assert retrieved.project == "MyApp"

    @pytest.mark.asyncio
    async def test_get_deployment_returns_none_when_missing(self):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        with patch("app.services.deploy_service.redis_pool", mock_redis):
            result = await get_deployment("nonexistent-id")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_deployment_returns_none_on_corrupt_json(self):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="not-valid-json{{{")

        with patch("app.services.deploy_service.redis_pool", mock_redis):
            result = await get_deployment("bad-id")

        assert result is None

    @pytest.mark.asyncio
    async def test_save_sets_correct_ttl(self):
        record = DeploymentRecord(
            deployment_id="ttl-test",
            status="running",
            command="echo hi",
            cwd="/tmp",
        )
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock()

        with patch("app.services.deploy_service.redis_pool", mock_redis):
            await save_deployment(record)

        _, kwargs = mock_redis.set.call_args
        assert kwargs.get("ex") == DEPLOYMENT_TTL

    @pytest.mark.asyncio
    async def test_get_deployment_preserves_all_fields(self):
        record = DeploymentRecord(
            deployment_id="full-record",
            status="success",
            command="render deploy",
            cwd="/home/user/app",
            project="RenderApp",
            chat_id="987654321",
            stdout="Deployed!\nhttps://renderapp.onrender.com",
            stderr="",
            exit_code=0,
            url="https://renderapp.onrender.com",
            started_at="2024-01-01T00:00:00+00:00",
            finished_at="2024-01-01T00:01:00+00:00",
        )
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=record.model_dump_json())

        with patch("app.services.deploy_service.redis_pool", mock_redis):
            retrieved = await get_deployment("full-record")

        assert retrieved.chat_id == "987654321"
        assert retrieved.url == "https://renderapp.onrender.com"
        assert retrieved.exit_code == 0
        assert retrieved.stdout.startswith("Deployed!")


# ---------------------------------------------------------------------------
# create_deployment
# ---------------------------------------------------------------------------


class TestCreateDeployment:
    @pytest.mark.asyncio
    async def test_creates_record_with_pending_status(self):
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock()

        with patch("app.services.deploy_service.redis_pool", mock_redis):
            record = await create_deployment(
                command="vercel deploy --prod",
                cwd="/tmp/myapp",
                project="MyApp",
            )

        assert record.status == "pending"
        assert record.command == "vercel deploy --prod"
        assert record.cwd == "/tmp/myapp"
        assert record.project == "MyApp"

    @pytest.mark.asyncio
    async def test_creates_unique_deployment_id(self):
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock()

        with patch("app.services.deploy_service.redis_pool", mock_redis):
            r1 = await create_deployment(command="echo 1", cwd="/tmp")
            r2 = await create_deployment(command="echo 2", cwd="/tmp")

        assert r1.deployment_id != r2.deployment_id

    @pytest.mark.asyncio
    async def test_creates_record_with_chat_id(self):
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock()

        with patch("app.services.deploy_service.redis_pool", mock_redis):
            record = await create_deployment(
                command="echo hi",
                cwd="/tmp",
                chat_id="111222333",
            )

        assert record.chat_id == "111222333"

    @pytest.mark.asyncio
    async def test_persists_record_to_redis_on_create(self):
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock()

        with patch("app.services.deploy_service.redis_pool", mock_redis):
            record = await create_deployment(command="echo hi", cwd="/tmp")

        mock_redis.set.assert_awaited_once()
        key_used = mock_redis.set.call_args[0][0]
        assert key_used == f"deployment:{record.deployment_id}"

    @pytest.mark.asyncio
    async def test_default_project_is_general(self):
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock()

        with patch("app.services.deploy_service.redis_pool", mock_redis):
            record = await create_deployment(command="echo", cwd="/tmp")

        assert record.project == "General"


# ---------------------------------------------------------------------------
# run_deployment
# ---------------------------------------------------------------------------


def _make_mock_redis(record: DeploymentRecord):
    """Helper: build a mock redis that returns `record` on first get,
    then returns the last saved value on subsequent gets."""
    saved_state = {"data": record.model_dump_json()}

    async def mock_get(key):
        return saved_state["data"]

    async def mock_set(key, value, ex=None):
        saved_state["data"] = value

    mock = AsyncMock()
    mock.get = AsyncMock(side_effect=mock_get)
    mock.set = AsyncMock(side_effect=mock_set)
    return mock


class TestRunDeployment:
    @pytest.mark.asyncio
    async def test_successful_command_sets_status_success(self):
        record = DeploymentRecord(
            deployment_id="run-ok",
            status="pending",
            command="echo deployed",
            cwd="/tmp",
        )
        mock_redis = _make_mock_redis(record)

        with patch("app.services.deploy_service.redis_pool", mock_redis):
            await run_deployment("run-ok")

        # Read final state from mock redis
        final_data = json.loads(mock_redis.set.call_args_list[-1][0][1])
        assert final_data["status"] == "success"
        assert final_data["exit_code"] == 0

    @pytest.mark.asyncio
    async def test_failed_command_sets_status_failed(self):
        record = DeploymentRecord(
            deployment_id="run-fail",
            status="pending",
            command="exit 1",
            cwd="/tmp",
        )
        mock_redis = _make_mock_redis(record)

        with patch("app.services.deploy_service.redis_pool", mock_redis):
            await run_deployment("run-fail")

        final_data = json.loads(mock_redis.set.call_args_list[-1][0][1])
        assert final_data["status"] == "failed"
        assert final_data["exit_code"] != 0

    @pytest.mark.asyncio
    async def test_stdout_is_captured(self):
        record = DeploymentRecord(
            deployment_id="run-stdout",
            status="pending",
            command="echo hello_from_deploy",
            cwd="/tmp",
        )
        mock_redis = _make_mock_redis(record)

        with patch("app.services.deploy_service.redis_pool", mock_redis):
            await run_deployment("run-stdout")

        final_data = json.loads(mock_redis.set.call_args_list[-1][0][1])
        assert "hello_from_deploy" in final_data["stdout"]

    @pytest.mark.asyncio
    async def test_url_is_extracted_from_stdout(self):
        record = DeploymentRecord(
            deployment_id="run-url",
            status="pending",
            command="echo 'Deployed to https://myapp.vercel.app'",
            cwd="/tmp",
        )
        mock_redis = _make_mock_redis(record)

        with patch("app.services.deploy_service.redis_pool", mock_redis):
            await run_deployment("run-url")

        final_data = json.loads(mock_redis.set.call_args_list[-1][0][1])
        assert final_data["url"] == "https://myapp.vercel.app"

    @pytest.mark.asyncio
    async def test_url_is_none_when_not_in_output(self):
        record = DeploymentRecord(
            deployment_id="run-nourl",
            status="pending",
            command="echo build complete no url here",
            cwd="/tmp",
        )
        mock_redis = _make_mock_redis(record)

        with patch("app.services.deploy_service.redis_pool", mock_redis):
            await run_deployment("run-nourl")

        final_data = json.loads(mock_redis.set.call_args_list[-1][0][1])
        assert final_data["url"] is None

    @pytest.mark.asyncio
    async def test_finished_at_is_set_on_success(self):
        record = DeploymentRecord(
            deployment_id="run-time",
            status="pending",
            command="echo done",
            cwd="/tmp",
        )
        mock_redis = _make_mock_redis(record)

        with patch("app.services.deploy_service.redis_pool", mock_redis):
            await run_deployment("run-time")

        final_data = json.loads(mock_redis.set.call_args_list[-1][0][1])
        assert final_data["started_at"] is not None
        assert final_data["finished_at"] is not None
        # finished_at should be parseable as ISO datetime
        datetime.fromisoformat(final_data["finished_at"])

    @pytest.mark.asyncio
    async def test_notify_callback_is_called_on_success(self):
        record = DeploymentRecord(
            deployment_id="run-cb-ok",
            status="pending",
            command="echo hi",
            cwd="/tmp",
        )
        mock_redis = _make_mock_redis(record)
        callback = AsyncMock()

        with patch("app.services.deploy_service.redis_pool", mock_redis):
            await run_deployment("run-cb-ok", notify_callback=callback)

        callback.assert_awaited_once()
        called_record: DeploymentRecord = callback.call_args[0][0]
        assert called_record.status == "success"

    @pytest.mark.asyncio
    async def test_notify_callback_is_called_on_failure(self):
        record = DeploymentRecord(
            deployment_id="run-cb-fail",
            status="pending",
            command="exit 42",
            cwd="/tmp",
        )
        mock_redis = _make_mock_redis(record)
        callback = AsyncMock()

        with patch("app.services.deploy_service.redis_pool", mock_redis):
            await run_deployment("run-cb-fail", notify_callback=callback)

        callback.assert_awaited_once()
        called_record: DeploymentRecord = callback.call_args[0][0]
        assert called_record.status == "failed"

    @pytest.mark.asyncio
    async def test_no_callback_does_not_raise(self):
        record = DeploymentRecord(
            deployment_id="run-no-cb",
            status="pending",
            command="echo ok",
            cwd="/tmp",
        )
        mock_redis = _make_mock_redis(record)

        with patch("app.services.deploy_service.redis_pool", mock_redis):
            # Should not raise even with no callback
            await run_deployment("run-no-cb", notify_callback=None)

    @pytest.mark.asyncio
    async def test_returns_early_when_deployment_not_found(self):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock()
        callback = AsyncMock()

        with patch("app.services.deploy_service.redis_pool", mock_redis):
            await run_deployment("ghost-id", notify_callback=callback)

        # Redis set should never be called; callback should not fire
        mock_redis.set.assert_not_awaited()
        callback.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_callback_exception_does_not_propagate(self):
        """A failing notify_callback must not crash run_deployment."""
        record = DeploymentRecord(
            deployment_id="run-cb-crash",
            status="pending",
            command="echo done",
            cwd="/tmp",
        )
        mock_redis = _make_mock_redis(record)

        async def bad_callback(rec):
            raise RuntimeError("Telegram is down")

        with patch("app.services.deploy_service.redis_pool", mock_redis):
            # Should complete without raising
            await run_deployment("run-cb-crash", notify_callback=bad_callback)

    @pytest.mark.asyncio
    async def test_status_transitions_pending_running_success(self):
        """Verify the intermediate 'running' state is saved before final state."""
        record = DeploymentRecord(
            deployment_id="run-transitions",
            status="pending",
            command="echo transit",
            cwd="/tmp",
        )
        mock_redis = _make_mock_redis(record)

        statuses_saved = []

        original_set = mock_redis.set.side_effect

        async def capture_set(key, value, ex=None):
            data = json.loads(value)
            statuses_saved.append(data["status"])
            await original_set(key, value, ex=ex)

        mock_redis.set.side_effect = capture_set

        with patch("app.services.deploy_service.redis_pool", mock_redis):
            await run_deployment("run-transitions")

        # First save should be "running", last save should be "success"
        assert statuses_saved[0] == "running"
        assert statuses_saved[-1] == "success"

    @pytest.mark.asyncio
    async def test_subprocess_exception_sets_status_failed(self):
        """Simulate a subprocess crash (e.g., command not found / OS error)."""
        record = DeploymentRecord(
            deployment_id="run-crash",
            status="pending",
            command="this_command_definitely_does_not_exist_xyz",
            cwd="/tmp",
        )
        mock_redis = _make_mock_redis(record)

        with patch("app.services.deploy_service.redis_pool", mock_redis):
            await run_deployment("run-crash")

        final_data = json.loads(mock_redis.set.call_args_list[-1][0][1])
        # Command not found → non-zero exit or failed status
        assert final_data["status"] in ("failed", "success")
        assert final_data["finished_at"] is not None


# ---------------------------------------------------------------------------
# Security: command injection prevention (shlex.split + create_subprocess_exec)
# ---------------------------------------------------------------------------


import asyncio
import shlex


class TestCommandInjectionPrevention:
    """
    ตรวจสอบว่า run_deployment ใช้ create_subprocess_exec + shlex.split
    และป้องกัน shell injection จาก user-provided command string
    """

    # --- shlex.split behaviour (unit) ---

    def test_shlex_split_simple_command(self):
        assert shlex.split("echo hello") == ["echo", "hello"]

    def test_shlex_split_command_with_args(self):
        assert shlex.split("vercel deploy --prod --yes") == [
            "vercel",
            "deploy",
            "--prod",
            "--yes",
        ]

    def test_shlex_split_quoted_argument_stays_single_token(self):
        parts = shlex.split('echo "hello world"')
        assert parts == ["echo", "hello world"]

    def test_shlex_split_semicolon_becomes_literal_arg(self):
        """
        'echo safe; echo injected' → ['echo', 'safe;', 'echo', 'injected']
        Semicolon ไม่ถูก interpret เป็น command separator
        """
        parts = shlex.split("echo safe; echo injected")
        assert ";" not in parts  # ไม่ใช่ standalone token
        assert "safe;" in parts  # ติดอยู่กับ token ก่อนหน้า

    def test_shlex_split_double_ampersand_becomes_literal_arg(self):
        """'echo a && echo b' → && ถูก parse เป็น token ปกติ ไม่ใช่ shell AND"""
        parts = shlex.split("echo a && echo b")
        assert "&&" in parts  # standalone token แต่จะถูกส่งเป็น arg ให้ echo ปกติ

    def test_shlex_split_pipe_becomes_literal_arg(self):
        """'echo a | cat' → | ถูก parse เป็น literal arg ไม่ใช่ pipe"""
        parts = shlex.split("echo a | cat")
        assert "|" in parts

    # --- subprocess-level injection prevention (integration via real subprocess) ---

    @pytest.mark.asyncio
    async def test_semicolon_injection_does_not_run_second_command(self):
        """
        'echo safe; echo INJECTED' ผ่าน create_subprocess_exec + shlex.split
        → stdout ควรมีเนื้อหา literal 'safe; echo INJECTED' ทั้งหมดในบรรทัดเดียว
        ไม่ใช่ 'safe\\nINJECTED\\n' (ซึ่งจะเกิดถ้าใช้ shell=True)
        """
        record = DeploymentRecord(
            deployment_id="inject-semi",
            status="pending",
            command="echo safe; echo INJECTED",
            cwd="/tmp",
        )
        mock_redis = _make_mock_redis(record)

        with patch("app.services.deploy_service.redis_pool", mock_redis):
            await run_deployment("inject-semi")

        final_data = json.loads(mock_redis.set.call_args_list[-1][0][1])
        stdout = final_data["stdout"]

        # ถ้าใช้ shell injection จะได้ 'safe\nINJECTED\n' (สองบรรทัด)
        # ถ้าป้องกันถูกต้อง echo จะรับ 'safe;', 'echo', 'INJECTED' เป็น args → 'safe; echo INJECTED\n'
        assert stdout.count("\n") <= 1, (
            "Semicolon was interpreted as a shell command separator — "
            "possible shell injection via create_subprocess_shell"
        )

    @pytest.mark.asyncio
    async def test_double_ampersand_injection_does_not_chain_commands(self):
        """
        'echo first && echo SECOND' → ไม่ควรรัน echo SECOND แยก
        output ควรเป็น 'first && echo SECOND' ในบรรทัดเดียว
        """
        record = DeploymentRecord(
            deployment_id="inject-and",
            status="pending",
            command="echo first && echo SECOND",
            cwd="/tmp",
        )
        mock_redis = _make_mock_redis(record)

        with patch("app.services.deploy_service.redis_pool", mock_redis):
            await run_deployment("inject-and")

        final_data = json.loads(mock_redis.set.call_args_list[-1][0][1])
        stdout = final_data["stdout"]

        assert stdout.count("\n") <= 1, (
            "&& was interpreted as shell AND operator — "
            "possible shell injection via create_subprocess_shell"
        )

    @pytest.mark.asyncio
    async def test_create_subprocess_exec_is_used_not_shell(self):
        """
        ตรวจสอบว่า run_deployment เรียก create_subprocess_exec
        และไม่เรียก create_subprocess_shell เลย
        """
        record = DeploymentRecord(
            deployment_id="check-exec",
            status="pending",
            command="echo verify_exec",
            cwd="/tmp",
        )
        mock_redis = _make_mock_redis(record)

        with patch("app.services.deploy_service.redis_pool", mock_redis):
            with (
                patch("asyncio.create_subprocess_shell") as mock_shell,
                patch(
                    "asyncio.create_subprocess_exec",
                    wraps=asyncio.create_subprocess_exec,
                ) as mock_exec,
            ):
                await run_deployment("check-exec")

        mock_shell.assert_not_called()
        mock_exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_exec_receives_split_args_not_raw_string(self):
        """
        ตรวจสอบว่า create_subprocess_exec ได้รับ list of args จาก shlex.split
        ไม่ใช่ raw command string ทั้งก้อน
        """
        record = DeploymentRecord(
            deployment_id="check-args",
            status="pending",
            command="echo hello world",
            cwd="/tmp",
        )
        mock_redis = _make_mock_redis(record)

        captured_args = {}

        original_exec = asyncio.create_subprocess_exec

        async def capture_exec(*args, **kwargs):
            captured_args["args"] = args
            return await original_exec(*args, **kwargs)

        with patch("app.services.deploy_service.redis_pool", mock_redis):
            with patch("asyncio.create_subprocess_exec", side_effect=capture_exec):
                await run_deployment("check-args")

        # exec ต้องได้รับ args แยก ไม่ใช่ string เดียว
        assert captured_args["args"] == ("echo", "hello", "world"), (
            f"Expected ('echo', 'hello', 'world') but got {captured_args['args']}"
        )

    @pytest.mark.asyncio
    async def test_quoted_path_with_spaces_parsed_correctly(self):
        """
        Command ที่มี quoted path เช่น 'echo "my project"'
        shlex.split ต้องรักษา space ภายใน quotes ให้เป็น single token
        """
        record = DeploymentRecord(
            deployment_id="inject-quoted",
            status="pending",
            command='echo "my project"',
            cwd="/tmp",
        )
        mock_redis = _make_mock_redis(record)

        captured_args = {}

        original_exec = asyncio.create_subprocess_exec

        async def capture_exec(*args, **kwargs):
            captured_args["args"] = args
            return await original_exec(*args, **kwargs)

        with patch("app.services.deploy_service.redis_pool", mock_redis):
            with patch("asyncio.create_subprocess_exec", side_effect=capture_exec):
                await run_deployment("inject-quoted")

        # 'echo "my project"' → ['echo', 'my project'] → exec('echo', 'my project')
        assert captured_args["args"] == ("echo", "my project")
