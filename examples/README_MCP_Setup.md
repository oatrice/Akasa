# MCP Client Configuration for Akasa

วิธีตั้งค่าให้ project อื่นเชื่อมต่อกับ Akasa MCP Server

## 1. คัดลอก Configuration File

คัดลอก `examples/mcp_client_config.json` ไปยัง project ของคุณ:

```bash
cp /Users/oatrice/Software-projects/Akasa/examples/mcp_client_config.json ~/.config/your-ide/mcp-config.json
```

## 2. ตั้งค่า Environment Variables

แก้ไขค่าใน config file:

- `AKASA_API_URL`: URL ของ Akasa backend (default: `http://localhost:8000`)
- `AKASA_API_KEY`: API key สำหรับ authenticate กับ Akasa
- `AKASA_CHAT_ID`: Telegram chat ID ที่จะรับ notification

## 3. IDE Integration

### Cursor / Windsurf
เพิ่มใน `settings.json`:
```json
{
  "mcpServers": {
    "akasa-remote-approval": {
      "command": "python3",
      "args": [
        "/Users/oatrice/Software-projects/Akasa/scripts/akasa_mcp_server.py"
      ],
      "env": {
        "AKASA_API_URL": "http://localhost:8000",
        "AKASA_API_KEY": "your-api-key",
        "AKASA_CHAT_ID": "your-chat-id"
      }
    }
  }
}
```

### Zed
เพิ่มใน `settings.json`:
```json
{
  "lsp": {
    "mcp": {
      "servers": {
        "akasa-remote-approval": {
          "command": "python3",
          "args": [
            "/Users/oatrice/Software-projects/Akasa/scripts/akasa_mcp_server.py"
          ],
          "env": {
            "AKASA_API_URL": "http://localhost:8000",
            "AKASA_API_KEY": "your-api-key",
            "AKASA_CHAT_ID": "your-chat-id"
          }
        }
      }
    }
  }
}
```

## 4. Available Tools

เมื่อเชื่อมต่อสำเร็จ จะมี tools ต่อไปนี้ให้ใช้:

- `request_remote_approval`: ขออนุมัติคำสั่งผ่าน Telegram
- `notify_pending_review`: แจ้งว่ามีการเปลี่ยนแปลงรอ review
- `notify_task_complete`: ส่งสรุปผลงานเสร็จสิ้น

## 5. ตัวอย่างการใช้งาน

```python
# ขออนุมัติก่อนรันคำสั่ง
await mcp.call_tool("request_remote_approval", {
    "command": "rm -rf node_modules",
    "cwd": "/path/to/project",
    "description": "Clean node modules"
})

# แจ้งว่ามี code รอ review
await mcp.call_tool("notify_pending_review", {
    "project": "MyApp",
    "task": "Implement user authentication",
    "files_changed": ["src/auth.js", "src/login.js"]
})

# ส่งสรุปงานเสร็จ
await mcp.call_tool("notify_task_complete", {
    "project": "MyApp",
    "task": "Setup development environment",
    "status": "success",
    "duration": "5m 30s"
})
```

## 6. การตรวจสอบสถานะ

ตรวจสอบว่า MCP server ทำงาน:
```bash
python3 /Users/oatrice/Software-projects/Akasa/scripts/akasa_mcp_server.py
```

ตรวจสอบ Akasa backend:
```bash
curl -H "X-Akasa-API-Key: your-key" \
     http://localhost:8000/api/v1/health
```
