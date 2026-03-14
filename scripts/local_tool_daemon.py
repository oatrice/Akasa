import asyncio
import json
import logging
import time
import httpx
from redis.asyncio import Redis

from app.config import settings
from app.services.command_queue_service import is_command_whitelisted

logger = logging.getLogger(__name__)

def get_redis() -> Redis:
    return Redis.from_url(settings.REDIS_URL, decode_responses=False)

async def execute_command(command_id: str, tool: str, command: str, args: dict) -> tuple[int, str]:
    if not is_command_whitelisted(tool, command):
        msg = f"Command '{command}' is not allowed for tool '{tool}'"
        logger.error(msg)
        return -1, msg

    cmd_args = [command]
    
    # Flatten args dict into a list. Just taking values here for simplicity of the test.
    # In a real shell/tool, we might map to specific keys.
    for val in args.values():
        cmd_args.append(str(val))
        
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd_args,
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
    except Exception as e:
        logger.error(f"Error executing command: {e}")
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
    await poll_queue("gemini", timeout=0)

if __name__ == "__main__":
    asyncio.run(main())
