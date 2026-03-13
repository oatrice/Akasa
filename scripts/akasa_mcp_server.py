"""
Akasa MCP Server — Remote Action Approval via Telegram

MCP Server สำหรับ Antigravity IDE ที่ให้ agent สามารถขออนุมัติ action
จาก user ผ่าน Telegram โดยส่ง request ไปที่ Akasa Backend

Usage:
    python scripts/akasa_mcp_server.py

Environment Variables:
    AKASA_API_URL     — URL ของ Akasa Backend (default: http://localhost:8000) or ngrok
    AKASA_API_KEY     — API Key สำหรับ authentication
    AKASA_CHAT_ID     — Telegram Chat ID ที่ต้องการส่ง notification ไป
"""

import httpx
import json
import sys
import uuid
import asyncio
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# --- Configuration ---
AKASA_API_URL = os.getenv("AKASA_API_URL", "http://localhost:8000")
AKASA_API_KEY = os.getenv("AKASA_API_KEY", "default-dev-key")
AKASA_CHAT_ID = os.getenv("AKASA_CHAT_ID", "")

# Polling config
MAX_POLL_ATTEMPTS = 10  # 10 attempts × 30s long-poll = ~5 minutes
POLL_INTERVAL = 1.0  # Wait between poll attempts (seconds)

# Session config
MCP_SESSION_ID = str(uuid.uuid4())


async def request_remote_approval(
    command: str,
    cwd: str,
    description: Optional[str] = None,
) -> dict:
    """
    ส่ง action confirmation request ไปยัง Akasa Backend
    แล้ว long-poll รอผล จาก Telegram

    Args:
        command: คำสั่งที่ต้องการ approval
        cwd: working directory ที่จะรันคำสั่ง
        description: คำอธิบายเพิ่มเติม (optional)

    Returns:
        dict: {"status": "allowed" | "denied" | "timeout", "request_id": str}
    """
    if not AKASA_CHAT_ID:
        raise ValueError("AKASA_CHAT_ID environment variable is not set")

    request_id = str(uuid.uuid4())

    # 1. Format message สำหรับ Telegram
    message = f"🤖 *Antigravity IDE — Action Confirmation*\n\n"
    message += f"📂 `{cwd}`\n"
    message += f"💻 `{command}`"
    if description:
        message += f"\n\n📝 {description}"

    # 2. ส่ง request ไปที่ Akasa Backend
    payload = {
        "chat_id": AKASA_CHAT_ID,
        "message": message,
        "metadata": {
            "request_id": request_id,
            "command": command,
            "cwd": cwd,
            "source": "antigravity",
            "description": description,
            "session_id": MCP_SESSION_ID,
        }
    }

    headers = {"X-Akasa-API-Key": AKASA_API_KEY}

    async with httpx.AsyncClient() as client:
        # POST request
        response = await client.post(
            f"{AKASA_API_URL}/api/v1/actions/request",
            json=payload,
            headers=headers,
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()
        request_id = data.get("request_id", request_id)

        # ถ้า session permission อนุญาตอัตโนมัติ
        if data.get("status") == "allowed":
            return {"status": "allowed", "request_id": request_id}

        # 3. Long-poll รอผล
        for _ in range(MAX_POLL_ATTEMPTS):
            await asyncio.sleep(POLL_INTERVAL)

            poll_response = await client.get(
                f"{AKASA_API_URL}/api/v1/actions/requests/{request_id}",
                headers=headers,
                timeout=35.0,  # > 30s long-poll ของ server
            )
            poll_response.raise_for_status()
            poll_data = poll_response.json()

            status = poll_data.get("status", "pending")
            if status != "pending":
                return {"status": status, "request_id": request_id}

    # 4. Timeout
    return {"status": "timeout", "request_id": request_id}


# --- MCP JSON-RPC Protocol (stdio) ---

TOOL_DEFINITIONS = [
    {
        "name": "request_remote_approval",
        "description": (
            "Request remote approval for a command via Telegram. "
            "Use this before running potentially unsafe commands. "
            "The user will receive a Telegram notification with Allow/Deny buttons."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The command to request approval for"
                },
                "cwd": {
                    "type": "string",
                    "description": "Current working directory"
                },
                "description": {
                    "type": "string",
                    "description": "Optional description of what the command does"
                }
            },
            "required": ["command", "cwd"]
        }
    }
]


def make_response(req_id, result):
    return json.dumps({"jsonrpc": "2.0", "id": req_id, "result": result})


def make_error(req_id, code, message):
    return json.dumps({
        "jsonrpc": "2.0", "id": req_id,
        "error": {"code": code, "message": message}
    })


async def handle_rpc(request: dict) -> str:
    """Handle a single JSON-RPC request"""
    req_id = request.get("id")
    method = request.get("method", "")
    params = request.get("params", {})

    if method == "initialize":
        return make_response(req_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "akasa-remote-approval", "version": "1.0.0"}
        })

    elif method == "notifications/initialized":
        return None  # No response needed for notifications

    elif method == "tools/list":
        return make_response(req_id, {"tools": TOOL_DEFINITIONS})

    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if tool_name == "request_remote_approval":
            try:
                result = await request_remote_approval(
                    command=arguments.get("command", ""),
                    cwd=arguments.get("cwd", "."),
                    description=arguments.get("description"),
                )
                status = result["status"]
                if status == "allowed":
                    text = f"✅ Action ALLOWED (request: {result['request_id']})"
                elif status == "denied":
                    text = f"❌ Action DENIED (request: {result['request_id']})"
                else:
                    text = f"⏰ Action TIMED OUT (request: {result['request_id']})"

                return make_response(req_id, {
                    "content": [{"type": "text", "text": text}]
                })
            except Exception as e:
                # ใช้ make_response + isError ตาม MCP spec:
                # JSON-RPC error = protocol-level error
                # isError in tool result = tool execution failure
                return make_response(req_id, {
                    "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                    "isError": True
                })
        else:
            return make_error(req_id, -32601, f"Unknown tool: {tool_name}")

    else:
        return make_error(req_id, -32601, f"Unknown method: {method}")


async def main():
    """Main loop: read JSON-RPC from stdin, respond via stdout (non-blocking)"""
    logger.info("Akasa MCP Server started (stdio mode)")

    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    while True:
        line_bytes = await reader.readline()
        if not line_bytes:
            break  # EOF

        line = line_bytes.decode().strip()
        if not line:
            continue

        try:
            request = json.loads(line)
            response = await handle_rpc(request)
            if response:
                print(response, flush=True)
        except json.JSONDecodeError:
            error = make_error(None, -32700, "Parse error")
            print(error, flush=True)
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            error = make_error(None, -32603, str(e))
            print(error, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
