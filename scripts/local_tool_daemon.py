import asyncio
import json
import logging
import time
import httpx
import shutil
from pathlib import Path
from redis.asyncio import Redis

from app.config import settings
from app.services.command_queue_service import get_command_whitelist_entry, _load_whitelist

logger = logging.getLogger(__name__)

def get_redis() -> Redis:
    return Redis.from_url(settings.REDIS_URL, decode_responses=False)

# Tool executable mapping - only gemini has CLI for now
# luma and zed are placeholder tools without actual executables
TOOL_EXECUTABLES = {
    "gemini": "gemini",  # gemini CLI exists
    # "luma": None,  # No CLI yet
    # "zed": None,   # No CLI yet
}


def is_tool_executable(tool: str) -> bool:
    """Check if tool has an executable configured."""
    return tool in TOOL_EXECUTABLES and TOOL_EXECUTABLES[tool] is not None


async def execute_command(command_id: str, tool: str, command: str, args: dict) -> tuple[int, str]:
    # Whitelist check and argument validation
    whitelist_entry = get_command_whitelist_entry(tool, command)
    if not whitelist_entry:
        msg = f"Command '{command}' is not allowed for tool '{tool}'"
        logger.error(msg)
        return -1, msg

    # Check if tool has executable
    if not is_tool_executable(tool):
        msg = f"Tool '{tool}' does not have a CLI executable configured yet"
        logger.warning(msg)
        return -1, msg

    executable = TOOL_EXECUTABLES[tool]
    
    # Build command parts: [executable, command, --arg-name value, ...]
    cmd_parts = [executable, command]
    for arg_name, arg_value in args.items():
        # Convert snake_case to kebab-case for CLI args
        arg_flag = f"--{arg_name.replace('_', '-')}"
        cmd_parts.extend([arg_flag, str(arg_value)])

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd_parts,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        output = ""
        if stdout:
            output += stdout.decode('utf-8')
        if stderr:
            output += stderr.decode('utf-8')
        return process.returncode, output
    except FileNotFoundError:
        return -1, f"Tool '{executable}' not found. Is '{executable}' installed and in PATH?"
    except Exception as e:
        logger.error(f"Error executing command '{' '.join(cmd_parts)}': {e}")
        return -1, str(e)

async def report_result(command_id: str, status: str, output: str, exit_code: int = None, duration: float = None) -> None:
    api_url = f"http://localhost:8000/api/v1/commands/{command_id}/result"
    payload = {
        "status": status,
        "output": output,
    }
    if exit_code is not None:
        payload["exit_code"] = exit_code
    if duration is not None:
        payload["duration"] = duration

    headers = {
        "X-Akasa-Daemon-Secret": settings.AKASA_DAEMON_SECRET,
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(api_url, json=payload, headers=headers)
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(f"Failed to report result for {command_id}: {e}")

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
            meta_key = f"akasa:commands:meta:{command_id}"
            
            if not await redis.exists(meta_key):
                logger.warning(f"Command {command_id} has expired. Skipping.")
                continue
            
            start_time = time.time()
            exit_code, output = await execute_command(
                command_id, 
                tool,
                payload["command"], 
                payload.get("args", {})
            )
            duration = time.time() - start_time
            
            status = "success" if exit_code == 0 else "failed"
            
            await report_result(command_id, status, output, exit_code, duration)
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in poll loop: {e}")
            await asyncio.sleep(1)

async def main():
    logging.basicConfig(level=logging.INFO)
    
    # Load whitelist to get all tools that this daemon should poll for
    whitelist = _load_whitelist()
    tools_to_poll = list(whitelist.keys())
    
    if not tools_to_poll:
        logger.warning("No tools configured in whitelist. Daemon will not poll any queues.")
        return

    # Filter to only tools that have executables
    executable_tools = [t for t in tools_to_poll if is_tool_executable(t)]
    if not executable_tools:
        logger.warning("No tools with configured executables. Nothing to poll.")
        return

    logger.info(f"Daemon configured to poll queues for tools: {', '.join(executable_tools)}")
    
    # Create a polling task for each tool and run them concurrently
    polling_tasks = [poll_queue(tool, timeout=1) for tool in executable_tools]
    await asyncio.gather(*polling_tasks)

if __name__ == "__main__":
    asyncio.run(main())
