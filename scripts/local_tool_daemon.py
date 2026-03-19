import asyncio
import json
import logging
import shlex
import sys
import time
from datetime import datetime, timezone
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
GEMINI_MODEL_ALIASES = {
    "auto": "auto-gemini-2.5",
    "pro": "gemini-2.5-pro",
    "flash": "gemini-2.5-flash",
    "flash-lite": "gemini-2.5-flash-lite",
    "flash_lite": "gemini-2.5-flash-lite",
    "gemini-pro": "gemini-2.5-pro",
    "gemini-flash": "gemini-2.5-flash",
    "gemini-flash-lite": "gemini-2.5-flash-lite",
}
GEMINI_QUOTA_MARKERS = (
    "terminalquotaerror",
    "exhausted your capacity on this model",
    "quota will reset after",
)


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


def _parse_iso_timestamp(value: Any) -> Optional[float]:
    if not isinstance(value, str) or not value:
        return None

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _format_utc_timestamp(epoch_seconds: float) -> str:
    return (
        datetime.fromtimestamp(epoch_seconds, tz=timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _resolve_gemini_model_alias(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        return value
    return GEMINI_MODEL_ALIASES.get(normalized.lower(), normalized)


def _prepare_command_args(tool: str, args: Dict[str, Any]) -> Dict[str, Any]:
    prepared = dict(args)
    if tool.lower() != "gemini":
        return prepared

    for key in ("model", "fallback_model"):
        raw_value = prepared.get(key)
        if isinstance(raw_value, str):
            prepared[key] = _resolve_gemini_model_alias(raw_value)

    return prepared


def _is_gemini_quota_error(output: str) -> bool:
    normalized = output.lower()
    return any(marker in normalized for marker in GEMINI_QUOTA_MARKERS)


def _flag_for_arg(arg_name: str, flag_aliases: Dict[str, Any]) -> str:
    alias = flag_aliases.get(arg_name)
    if isinstance(alias, str) and alias.strip():
        return alias.strip()
    return f"--{arg_name.replace('_', '-')}"


class _PromptFormatDict(dict):
    def __missing__(self, key: str) -> str:
        return ""


def _humanize_arg_name(arg_name: str) -> str:
    words = arg_name.replace("_", " ").strip().split()
    normalized_words: List[str] = []
    for word in words:
        lower = word.lower()
        if lower == "pr":
            normalized_words.append("PR")
        elif lower == "id":
            normalized_words.append("ID")
        else:
            normalized_words.append(word.title())
    return " ".join(normalized_words)


def _build_prompt_text(command: str, args: Dict[str, Any], execution_cfg: Dict[str, Any]) -> Optional[str]:
    prompt_parts: List[str] = []

    prompt_arg_key = execution_cfg.get("prompt_arg_key")
    if isinstance(prompt_arg_key, str) and prompt_arg_key:
        prompt_value = args.get(prompt_arg_key)
        if not isinstance(prompt_value, str) or not prompt_value.strip():
            return None
        prompt_parts.append(prompt_value.strip())

    prompt_template = execution_cfg.get("prompt_template")
    if isinstance(prompt_template, str) and prompt_template.strip():
        formatted = prompt_template.format_map(
            _PromptFormatDict(
                {
                    key: value if isinstance(value, str) else str(value)
                    for key, value in args.items()
                    if value is not None
                }
            )
        ).strip()
        if formatted:
            prompt_parts.append(formatted)

    prompt_context_keys = execution_cfg.get("prompt_context_keys", [])
    if isinstance(prompt_context_keys, list) and prompt_context_keys:
        context_lines: List[str] = []
        for key in prompt_context_keys:
            key_str = str(key)
            value = args.get(key_str)
            if value in (None, ""):
                continue
            context_lines.append(f"- {_humanize_arg_name(key_str)}: {value}")
        if context_lines:
            prompt_parts.append("Context:\n" + "\n".join(context_lines))

    rendered = "\n\n".join(part for part in prompt_parts if part).strip()
    if rendered:
        return rendered

    if command == "check_status":
        return "Status check for Gemini CLI. Reply briefly with readiness, current model, and blockers."

    return None


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
    consumed_args: set[str] = set()

    base_args = execution_cfg.get("base_args", [])
    if isinstance(base_args, list):
        cmd_parts.extend(str(value) for value in base_args)

    flag_aliases = execution_cfg.get("flag_aliases", {})
    if not isinstance(flag_aliases, dict):
        flag_aliases = {}

    internal_args = execution_cfg.get("internal_args", [])
    if isinstance(internal_args, list):
        consumed_args.update(str(value) for value in internal_args)

    global_flag_args = execution_cfg.get("global_flag_args", [])
    if isinstance(global_flag_args, list):
        for key in global_flag_args:
            key_str = str(key)
            if key_str not in args:
                continue
            cmd_parts.extend([_flag_for_arg(key_str, flag_aliases), str(args[key_str])])
            consumed_args.add(key_str)

    prompt_text = _build_prompt_text(command, args, execution_cfg)
    if prompt_text is not None:
        output_format = execution_cfg.get("output_format")
        if isinstance(output_format, str) and output_format.strip():
            cmd_parts.extend(["--output-format", output_format.strip()])
        cmd_parts.extend(["-p", prompt_text])
        return cmd_parts

    include_command_name = execution_cfg.get("include_command_name", True)
    if include_command_name:
        cmd_parts.append(command)

    argument_style = execution_cfg.get("argument_style", "flags")
    if argument_style == "positional":
        positional_args = execution_cfg.get("positional_args", [])
        if not isinstance(positional_args, list):
            positional_args = []

        for key in positional_args:
            if key in args:
                cmd_parts.append(str(args[key]))
                consumed_args.add(key)

        for arg_name, arg_value in args.items():
            if arg_name in consumed_args:
                continue
            arg_flag = _flag_for_arg(arg_name, flag_aliases)
            cmd_parts.extend([arg_flag, str(arg_value)])
    else:
        for arg_name, arg_value in args.items():
            if arg_name in consumed_args:
                continue
            arg_flag = _flag_for_arg(arg_name, flag_aliases)
            cmd_parts.extend([arg_flag, str(arg_value)])

    return cmd_parts


async def _maybe_retry_gemini_with_fallback(
    executable: str,
    command: str,
    args: Dict[str, Any],
    execution_cfg: Dict[str, Any],
    exit_code: int,
    output: str,
) -> tuple[int, str]:
    if exit_code == 0 or not _is_gemini_quota_error(output):
        return exit_code, output

    fallback_model = args.get("fallback_model")
    if not isinstance(fallback_model, str) or not fallback_model.strip():
        return exit_code, output

    primary_model = str(args.get("model") or "default").strip()
    fallback_model = fallback_model.strip()
    if primary_model.lower() == fallback_model.lower():
        return exit_code, output

    retry_args = dict(args)
    retry_args["model"] = fallback_model
    retry_args.pop("fallback_model", None)

    logger.warning(
        "GEMINI QUOTA FALLBACK %s — primary_model=%s, fallback_model=%s",
        command,
        primary_model,
        fallback_model,
    )

    retry_exit_code, retry_output = await _execute_cli(
        executable, command, retry_args, execution_cfg
    )

    notice_lines = [
        "Gemini quota reached on the primary model.",
        f"Primary model: {primary_model}",
        f"Retried with fallback model: {fallback_model}",
    ]
    if retry_exit_code == 0:
        combined_output = "\n".join(notice_lines + ["", retry_output])
        return retry_exit_code, combined_output

    combined_output = "\n".join(
        notice_lines + ["", "Fallback attempt failed.", "", retry_output]
    )
    return retry_exit_code, combined_output


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

    prepared_args = _prepare_command_args(tool, args)

    args_validation_error = _validate_args(whitelist_entry, prepared_args)
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
        return await _execute_http(command_id, tool, command, prepared_args, execution_cfg)

    if execution_type == "mcp":
        return await _execute_mcp(command, prepared_args, execution_cfg)

    executable = execution_cfg.get("executable")
    if not executable:
        executable = TOOL_EXECUTABLES.get(tool)
    if not executable:
        msg = f"Tool '{tool}' does not have an executable configured"
        logger.warning(msg)
        return -1, msg

    exit_code, output = await _execute_cli(
        str(executable), command, prepared_args, execution_cfg
    )

    if tool.lower() == "gemini":
        return await _maybe_retry_gemini_with_fallback(
            str(executable),
            command,
            prepared_args,
            execution_cfg,
            exit_code,
            output,
        )

    return exit_code, output


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
            queued_at = payload.get("queued_at")
            dequeued_at_ts = time.time()
            dequeued_at = _format_utc_timestamp(dequeued_at_ts)
            queued_at_ts = _parse_iso_timestamp(queued_at)
            queue_wait_ms: Optional[int] = None
            if queued_at_ts is not None:
                queue_wait_ms = max(int((dequeued_at_ts - queued_at_ts) * 1000), 0)

            logger.info(
                "DEQUEUED %s — tool=%s, command=%s, queue=%s, queued_at=%s, "
                "dequeued_at=%s, queue_wait_ms=%s",
                command_id,
                tool,
                command,
                queue_name,
                queued_at or "unknown",
                dequeued_at,
                queue_wait_ms if queue_wait_ms is not None else "unknown",
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
            run_duration_ms = max(int(duration_seconds * 1000), 0)
            total_latency_ms = (
                queue_wait_ms + run_duration_ms if queue_wait_ms is not None else None
            )

            status = "success" if exit_code == 0 else "failed"
            logger.info(
                "COMPLETED %s — tool=%s, command=%s, status=%s, exit_code=%s, "
                "queue_wait_ms=%s, run_duration_ms=%s, total_latency_ms=%s",
                command_id,
                tool,
                command,
                status,
                exit_code,
                queue_wait_ms if queue_wait_ms is not None else "unknown",
                run_duration_ms,
                total_latency_ms if total_latency_ms is not None else "unknown",
            )
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
