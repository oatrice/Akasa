import asyncio
import json
import logging
import shlex
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
from redis.asyncio import Redis

# Add project root to path for imports when running script directly
_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from app.config import settings
from app.services.command_queue_service import (
    _load_whitelist,
    get_command_whitelist_entry,
    mark_command_expired,
    update_command_status,
)

logger = logging.getLogger(__name__)

# Backward-compatibility fallback when legacy config has no executable metadata.
TOOL_EXECUTABLES = {
    "gemini": "gemini",
}

RETRYABLE_HTTP_STATUSES = {429, 500, 502, 503, 504}
SAFE_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def get_redis() -> Redis:
    return Redis.from_url(settings.REDIS_URL, decode_responses=False)


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _extract_path_without_location(raw_path: str) -> str:
    """Strip optional :line[:column] suffix while preserving regular paths."""
    parts = raw_path.rsplit(":", 2)
    if len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
        return parts[0]
    if len(parts) >= 2 and parts[-1].isdigit():
        return ":".join(parts[:-1])
    return raw_path


def _is_path_allowed(raw_path: str, allowed_paths: List[str]) -> bool:
    if not raw_path:
        return False

    path_part = _extract_path_without_location(raw_path)
    candidate = Path(path_part).expanduser()
    if not candidate.is_absolute():
        candidate = (_PROJECT_ROOT / candidate).resolve(strict=False)
    else:
        candidate = candidate.resolve(strict=False)

    for allowed_root in allowed_paths:
        root = Path(allowed_root).expanduser().resolve(strict=False)
        if candidate == root or root in candidate.parents:
            return True
    return False


def _validate_args(whitelist_entry: Dict[str, Any], args: Dict[str, Any]) -> Optional[str]:
    allowed_args = whitelist_entry.get("allowed_args", [])
    if not isinstance(allowed_args, list):
        allowed_args = []

    unknown_args = [arg for arg in args.keys() if arg not in allowed_args]
    if unknown_args:
        return (
            f"Arguments {unknown_args} are not allowed for "
            f"{whitelist_entry.get('tool')}:{whitelist_entry.get('command')}"
        )

    execution_cfg = whitelist_entry.get("execution", {})
    if not isinstance(execution_cfg, dict):
        return None

    allowed_paths = execution_cfg.get("allowed_paths", [])
    if not isinstance(allowed_paths, list) or not allowed_paths:
        return None

    path_arg_keys = execution_cfg.get("path_arg_keys", [])
    if not isinstance(path_arg_keys, list):
        path_arg_keys = []

    for key in path_arg_keys:
        value = args.get(key)
        if not isinstance(value, str):
            return f"Argument '{key}' must be a string path"
        if not _is_path_allowed(value, allowed_paths):
            return f"Path '{value}' is outside allowed paths"

    return None


def _build_cli_command(
    executable: str,
    command: str,
    args: Dict[str, Any],
    execution_cfg: Dict[str, Any],
) -> List[str]:
    cmd_parts: List[str] = [executable]

    base_args = execution_cfg.get("base_args", [])
    if isinstance(base_args, list):
        cmd_parts.extend(str(value) for value in base_args)

    include_command_name = execution_cfg.get("include_command_name", True)
    if include_command_name:
        cmd_parts.append(command)

    argument_style = execution_cfg.get("argument_style", "flags")
    if argument_style == "positional":
        positional_args = execution_cfg.get("positional_args", [])
        if not isinstance(positional_args, list):
            positional_args = []

        consumed = set()
        for key in positional_args:
            if key in args:
                cmd_parts.append(str(args[key]))
                consumed.add(key)

        for arg_name, arg_value in args.items():
            if arg_name in consumed:
                continue
            arg_flag = f"--{arg_name.replace('_', '-')}"
            cmd_parts.extend([arg_flag, str(arg_value)])
    else:
        for arg_name, arg_value in args.items():
            arg_flag = f"--{arg_name.replace('_', '-')}"
            cmd_parts.extend([arg_flag, str(arg_value)])

    return cmd_parts


async def _execute_cli(
    executable: str,
    command: str,
    args: Dict[str, Any],
    execution_cfg: Dict[str, Any],
) -> tuple[int, str]:
    cmd_parts = _build_cli_command(executable, command, args, execution_cfg)
    timeout_seconds = _to_float(execution_cfg.get("timeout_seconds"), 60.0)

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd_parts,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return -1, (
                f"CLI command timed out after {timeout_seconds:.1f}s: "
                f"{' '.join(cmd_parts)}"
            )

        output = ""
        if stdout:
            output += stdout.decode("utf-8", errors="replace")
        if stderr:
            output += stderr.decode("utf-8", errors="replace")
        return process.returncode, output
    except FileNotFoundError:
        return -1, (
            f"Tool '{executable}' not found. Is '{executable}' installed and in PATH?"
        )
    except Exception as exc:
        logger.error(f"CLI execution failed for {' '.join(cmd_parts)}: {exc}")
        return -1, str(exc)


def _validate_http_endpoint(endpoint: str, execution_cfg: Dict[str, Any]) -> Optional[str]:
    parsed = urlparse(endpoint)
    if parsed.scheme not in {"http", "https"}:
        return f"Unsupported endpoint scheme '{parsed.scheme}'"

    allowed_hosts = execution_cfg.get("allowed_hosts", list(SAFE_LOCAL_HOSTS))
    if not isinstance(allowed_hosts, list) or not allowed_hosts:
        allowed_hosts = list(SAFE_LOCAL_HOSTS)
    allowed_hosts = [str(host).lower() for host in allowed_hosts]

    host = (parsed.hostname or "").lower()
    if host not in allowed_hosts:
        return f"Endpoint host '{host}' is not in allowed_hosts {allowed_hosts}"

    return None


def _build_http_payload(
    command_id: str,
    tool: str,
    command: str,
    args: Dict[str, Any],
    execution_cfg: Dict[str, Any],
) -> Dict[str, Any]:
    payload_mode = execution_cfg.get("payload_mode", "envelope")
    if payload_mode == "args":
        return args
    return {
        "command_id": command_id,
        "tool": tool,
        "command": command,
        "args": args,
    }


async def _execute_http(
    command_id: str,
    tool: str,
    command: str,
    args: Dict[str, Any],
    execution_cfg: Dict[str, Any],
) -> tuple[int, str]:
    endpoint = execution_cfg.get("endpoint")
    if not endpoint:
        return -1, f"HTTP execution missing endpoint for tool '{tool}'"

    endpoint = str(endpoint)
    endpoint_error = _validate_http_endpoint(endpoint, execution_cfg)
    if endpoint_error:
        return -1, endpoint_error

    method = str(execution_cfg.get("method", "POST")).upper()
    headers = execution_cfg.get("headers", {})
    if not isinstance(headers, dict):
        headers = {}

    timeout_seconds = _to_float(execution_cfg.get("timeout_seconds"), 10.0)
    retries = max(_to_int(execution_cfg.get("retries"), 0), 0)
    backoff_seconds = max(_to_float(execution_cfg.get("backoff_seconds"), 0.5), 0.0)

    retry_statuses = execution_cfg.get("retry_statuses", list(RETRYABLE_HTTP_STATUSES))
    if not isinstance(retry_statuses, list):
        retry_statuses = list(RETRYABLE_HTTP_STATUSES)
    retry_statuses = set(_to_int(value, 0) for value in retry_statuses)

    payload = _build_http_payload(command_id, tool, command, args, execution_cfg)

    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.request(
                    method=method,
                    url=endpoint,
                    json=payload,
                    headers=headers,
                )

            text = response.text
            if response.status_code >= 400:
                if response.status_code in retry_statuses and attempt < retries:
                    await asyncio.sleep(backoff_seconds * (2**attempt))
                    continue
                return response.status_code, f"HTTP {response.status_code}: {text}"

            if not text:
                text = f"HTTP {response.status_code}"
            return 0, text

        except (httpx.TimeoutException, httpx.NetworkError, httpx.TransportError) as exc:
            if attempt < retries:
                await asyncio.sleep(backoff_seconds * (2**attempt))
                continue
            return -1, f"HTTP request failed after {attempt + 1} attempt(s): {exc}"
        except Exception as exc:
            return -1, f"HTTP execution error: {exc}"

    return -1, "HTTP request failed after retries"


def _get_mcp_server_command(execution_cfg: Dict[str, Any]) -> Optional[List[str]]:
    command = execution_cfg.get("server_command")
    if isinstance(command, list) and command:
        return [str(part) for part in command]
    if isinstance(command, str) and command.strip():
        return shlex.split(command)
    return None


def _extract_mcp_result(call_response: Dict[str, Any]) -> tuple[int, str]:
    if "error" in call_response:
        error = call_response.get("error", {})
        if isinstance(error, dict):
            return -1, (
                f"MCP protocol error: code={error.get('code')} "
                f"message={error.get('message')}"
            )
        return -1, f"MCP protocol error: {error}"

    result = call_response.get("result", {})
    if not isinstance(result, dict):
        return -1, f"Unexpected MCP result format: {result!r}"

    content = result.get("content", [])
    messages: List[str] = []
    if isinstance(content, list):
        for entry in content:
            if isinstance(entry, dict) and "text" in entry:
                messages.append(str(entry.get("text", "")))

    rendered = "\n".join(msg for msg in messages if msg).strip()
    if not rendered:
        rendered = json.dumps(result, ensure_ascii=False)

    if result.get("isError") is True:
        return 1, rendered

    return 0, rendered


async def _execute_mcp_stdio_once(
    command: str,
    args: Dict[str, Any],
    execution_cfg: Dict[str, Any],
) -> tuple[int, str]:
    server_cmd = _get_mcp_server_command(execution_cfg)
    if not server_cmd:
        return -1, "MCP execution requires 'server_command' in whitelist config"

    timeout_seconds = _to_float(execution_cfg.get("timeout_seconds"), 30.0)
    tool_name = str(execution_cfg.get("tool_name") or command)
    if execution_cfg.get("tool_name_from_command", False):
        tool_name = command

    initialize_id = "init-1"
    call_id = "call-1"
    requests = [
        {
            "jsonrpc": "2.0",
            "id": initialize_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "akasa-local-daemon", "version": "1.0.0"},
            },
        },
        {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        },
        {
            "jsonrpc": "2.0",
            "id": call_id,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": args},
        },
    ]
    stdin_payload = "\n".join(json.dumps(req) for req in requests) + "\n"

    try:
        process = await asyncio.create_subprocess_exec(
            *server_cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=stdin_payload.encode("utf-8")),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return -1, f"MCP execution timed out after {timeout_seconds:.1f}s"

        call_response: Optional[Dict[str, Any]] = None
        for line in stdout.decode("utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                continue
            if parsed.get("id") == call_id:
                call_response = parsed
                break

        if call_response is None:
            stderr_text = stderr.decode("utf-8", errors="replace").strip()
            if stderr_text:
                return -1, f"MCP call response missing. stderr: {stderr_text}"
            return -1, "MCP call response missing from server output"

        status, output = _extract_mcp_result(call_response)
        if status != 0:
            stderr_text = stderr.decode("utf-8", errors="replace").strip()
            if stderr_text:
                output = f"{output}\n\nstderr:\n{stderr_text}"
        return status, output
    except FileNotFoundError:
        return -1, f"MCP server command not found: {server_cmd[0]}"
    except Exception as exc:
        return -1, f"MCP execution error: {exc}"


async def _execute_mcp(
    command: str,
    args: Dict[str, Any],
    execution_cfg: Dict[str, Any],
) -> tuple[int, str]:
    retries = max(_to_int(execution_cfg.get("retries"), 0), 0)
    backoff_seconds = max(_to_float(execution_cfg.get("backoff_seconds"), 1.0), 0.0)

    last_result = (-1, "MCP execution failed")
    for attempt in range(retries + 1):
        status, output = await _execute_mcp_stdio_once(command, args, execution_cfg)
        last_result = (status, output)
        if status == 0:
            return status, output
        if attempt < retries and status < 0:
            await asyncio.sleep(backoff_seconds * (2**attempt))

    return last_result


async def execute_command(
    command_id: str, tool: str, command: str, args: Dict[str, Any]
) -> tuple[int, str]:
    whitelist_entry = get_command_whitelist_entry(tool, command)
    if not whitelist_entry:
        msg = f"Command '{command}' is not allowed for tool '{tool}'"
        logger.error(msg)
        return -1, msg

    if not isinstance(args, dict):
        return -1, "Command args must be an object/dict"

    args_validation_error = _validate_args(whitelist_entry, args)
    if args_validation_error:
        logger.warning(
            f"Rejected command {command_id} ({tool}:{command}) - {args_validation_error}"
        )
        return -1, args_validation_error

    execution_cfg = whitelist_entry.get("execution", {})
    if not isinstance(execution_cfg, dict):
        execution_cfg = {}

    execution_type = str(execution_cfg.get("type", "cli")).lower()

    if execution_type == "http":
        return await _execute_http(command_id, tool, command, args, execution_cfg)

    if execution_type == "mcp":
        return await _execute_mcp(command, args, execution_cfg)

    executable = execution_cfg.get("executable")
    if not executable:
        executable = TOOL_EXECUTABLES.get(tool)
    if not executable:
        msg = f"Tool '{tool}' does not have an executable configured"
        logger.warning(msg)
        return -1, msg

    return await _execute_cli(str(executable), command, args, execution_cfg)


async def report_result(
    command_id: str,
    status: str,
    output: str,
    exit_code: Optional[int] = None,
    duration_seconds: Optional[float] = None,
) -> bool:
    api_url = f"http://localhost:8000/api/v1/commands/{command_id}/result"
    payload: Dict[str, Any] = {
        "status": status,
        "output": output,
    }
    if exit_code is not None:
        payload["exit_code"] = exit_code
    if duration_seconds is not None:
        payload["duration_seconds"] = duration_seconds

    headers = {
        "X-Daemon-Secret": settings.AKASA_DAEMON_SECRET,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(api_url, json=payload, headers=headers)
            response.raise_for_status()
            return True
        except httpx.HTTPError as exc:
            logger.error(f"Failed to report result for {command_id}: {exc}")
            return False


async def poll_queue(tool: str, timeout: int = 1) -> None:
    redis = get_redis()
    queue_name = f"akasa:commands:{tool}"
    logger.info(f"Starting to poll queue {queue_name}")

    while True:
        try:
            result = await redis.brpop(queue_name, timeout=timeout)
            if not result:
                continue

            _, item = result
            payload = json.loads(item.decode("utf-8"))

            command_id = payload["command_id"]
            command = payload["command"]
            args = payload.get("args", {})
            meta_key = f"akasa:cmd_meta:{command_id}"

            logger.info(
                f"DEQUEUED {command_id} — tool={tool}, command={command}, queue={queue_name}"
            )

            if not await redis.exists(meta_key):
                logger.warning(f"Command {command_id} has expired before execution")
                await mark_command_expired(command_id)
                continue

            await update_command_status(command_id, "picked_up")
            await update_command_status(command_id, "running")

            start_time = time.time()
            exit_code, output = await execute_command(command_id, tool, command, args)
            duration_seconds = time.time() - start_time

            status = "success" if exit_code == 0 else "failed"
            reported = await report_result(
                command_id=command_id,
                status=status,
                output=output,
                exit_code=exit_code,
                duration_seconds=duration_seconds,
            )

            if not reported:
                await update_command_status(
                    command_id=command_id,
                    status=status,  # type: ignore[arg-type]
                    result=output if status == "success" else None,
                    error=output if status == "failed" else None,
                )

        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error(f"Error in poll loop for {tool}: {exc}", exc_info=True)
            await asyncio.sleep(1)


async def main():
    logging.basicConfig(level=logging.INFO)

    whitelist = _load_whitelist()
    tools_to_poll = list(whitelist.keys())

    if not tools_to_poll:
        logger.warning("No tools configured in whitelist. Daemon will not poll any queues.")
        return

    logger.info(f"Daemon configured to poll queues for tools: {', '.join(tools_to_poll)}")

    polling_tasks = [poll_queue(tool, timeout=1) for tool in tools_to_poll]
    await asyncio.gather(*polling_tasks)


if __name__ == "__main__":
    asyncio.run(main())
