# Code Review: Antigravity IDE Action Confirmation via Akasa Bot (Issue #58)

> 📅 Review Date: 2026-03-13
> 📁 Source: `luma_failed_prompt_1773390600.md` + direct code inspection

---

## 📋 Files Reviewed

| File | Type | Verdict |
|------|------|---------|
| [akasa_mcp_server.py](file:///Users/oatrice/Software-projects/Akasa/scripts/akasa_mcp_server.py) | New — MCP Server | ⚠️ Issues Found |
| [actions.py](file:///Users/oatrice/Software-projects/Akasa/app/routers/actions.py) | Modified — Backend Router | ⚠️ Minor Issues |
| [notification.py](file:///Users/oatrice/Software-projects/Akasa/app/models/notification.py) | Modified — Data Model | ✅ OK |
| [test_akasa_mcp_server.py](file:///Users/oatrice/Software-projects/Akasa/tests/scripts/test_akasa_mcp_server.py) | New — MCP Tests | ⚠️ Missing Coverage |
| [test_actions_router.py](file:///Users/oatrice/Software-projects/Akasa/tests/routers/test_actions_router.py) | Modified — Router Tests | ✅ Good |

---

## 🔴 Critical Issues

### 1. Inconsistent Error Handling in `handle_rpc` (akasa_mcp_server.py:201-205)

**ปัญหา:** เมื่อ tool call เกิด `Exception` จะใช้ `make_response` กับ `isError: True` แต่กรณีอื่น (unknown method/tool) จะใช้ `make_error` ตาม JSON-RPC standard

```python
# ❌ ปัจจุบัน: ใช้ make_response + isError (custom format)
except Exception as e:
    return make_response(req_id, {
        "content": [{"type": "text", "text": f"Error: {str(e)}"}],
        "isError": True
    })
```

**แนะนำ:** เปลี่ยนเป็น `make_error` เพื่อให้ error handling เป็นมาตรฐาน JSON-RPC เดียวกัน หรือถ้าต้องการให้ IDE เห็นเป็น tool result error ตาม MCP spec จริง ก็ให้ใส่ comment อธิบายเหตุผลว่าทำไมถึงใช้ `isError` pattern

> [!IMPORTANT]
> ตาม [MCP Spec](https://spec.modelcontextprotocol.io), เมื่อ tool execution ล้มเหลว ควรใช้ `isError: true` ใน tool result — **ไม่ใช่** JSON-RPC error เพราะ JSON-RPC error หมายถึง protocol-level error ส่วน `isError` หมายถึง tool execution ล้มเหลว ดังนั้นโค้ดปัจจุบัน**ถูกต้องแล้ว**ตาม MCP spec แต่ขาด comment อธิบาย

### 2. `main()` ใช้ Synchronous `sys.stdin` Loop กับ `async` (akasa_mcp_server.py:217)

**ปัญหา:** `for line in sys.stdin` เป็น blocking I/O — ไม่สามารถรัน concurrent requests ได้ เมื่อ `handle_rpc` ทำ network call (ยาวนานกว่า 30 วินาที) event loop จะถูก block

```python
# ❌ ปัจจุบัน: blocking stdin read
async def main():
    for line in sys.stdin:  # ⚠️ blocking!
        ...
        response = await handle_rpc(request)
```

**แนะนำ:** ใช้ `asyncio.StreamReader` หรือ `loop.run_in_executor` กับ `sys.stdin.readline`

```python
# ✅ แนะนำ: non-blocking stdin
async def main():
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    
    while True:
        line = await reader.readline()
        if not line:
            break
        ...
```

---

## 🟡 Medium Issues

### 3. ขาด Validation ใน `create_action_request` (actions.py:50-52)

**ปัญหา:** `request_id`, `command`, `cwd` ถูกดึงจาก `metadata` dict โดยไม่มี validation — ถ้า field เหล่านี้หายไป จะเป็น `None` แล้วอาจ crash ตอนสร้าง `ActionRequestState`

```python
# ❌ ปัจจุบัน: ไม่ validate
request_id = metadata.get("request_id")  # อาจเป็น None
command = metadata.get("command")        # อาจเป็น None
```

**แนะนำ:** เพิ่ม validation:
```python
request_id = metadata.get("request_id")
command = metadata.get("command")
cwd = metadata.get("cwd")
if not all([request_id, command, cwd]):
    raise HTTPException(status_code=400, detail="Missing required metadata fields: request_id, command, cwd")
```

### 4. `chat_id` ใช้ `hasattr` แทนที่จะเช็คค่า (actions.py:43)

**ปัญหา:** `hasattr(payload, "chat_id")` จะ return `True` เสมอ เพราะ `chat_id` เป็น field ที่ define ไว้ใน `NotificationPayload` (แม้ค่าจะเป็น `None`)

```python
# ❌ ปัจจุบัน: จะ return True เสมอ
chat_id = payload.chat_id if hasattr(payload, "chat_id") else payload.user_id
```

**แนะนำ:**
```python
# ✅ เช็คค่าแทน
chat_id = payload.chat_id or payload.user_id
if not chat_id:
    raise HTTPException(status_code=400, detail="Either chat_id or user_id is required")
```

### 5. ไม่มี `AKASA_CHAT_ID` Validation (akasa_mcp_server.py:29)

**ปัญหา:** ถ้า `AKASA_CHAT_ID` env var ไม่ได้ตั้ง จะเป็น empty string `""` — request จะถูกส่งไป backend ด้วย `chat_id = ""` ซึ่งจะ fail แบบไม่ clear

**แนะนำ:** เพิ่ม early validation ใน `request_remote_approval`:
```python
if not AKASA_CHAT_ID:
    raise ValueError("AKASA_CHAT_ID environment variable is not set")
```

---

## 🟢 Minor Issues / Suggestions

### 6. Type Hint ควร explicit มากกว่านี้ (akasa_mcp_server.py:42)

```python
# ❌ ปัจจุบัน
description: str = None  # type mismatch: None ≠ str

# ✅ ควรเป็น
description: Optional[str] = None
```

### 7. `datetime.utcnow` ถูก deprecate ใน Python 3.12+ (notification.py:37)

```python
# ⚠️ deprecated ใน Python 3.12+
requested_at: datetime = Field(default_factory=datetime.utcnow)

# ✅ ควรเป็น
from datetime import timezone
requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

### 8. Test coverage ไม่ครอบคลุม (`handle_rpc` ยังไม่มี test)

File `test_akasa_mcp_server.py` ทดสอบแค่ `request_remote_approval` function แต่ยังขาด:
- ทดสอบ `handle_rpc` สำหรับ `initialize`, `tools/list`, `tools/call`
- ทดสอบ error case เมื่อ `request_remote_approval` throw exception
- ทดสอบ `make_response` / `make_error` format

---

## 🧪 Test Suggestions (TDD)

### Test 1: handle_rpc — initialize method
```python
@pytest.mark.asyncio
async def test_handle_rpc_initialize():
    from scripts.akasa_mcp_server import handle_rpc
    result = await handle_rpc({"id": 1, "method": "initialize", "params": {}})
    data = json.loads(result)
    assert data["result"]["protocolVersion"] == "2024-11-05"
    assert data["result"]["serverInfo"]["name"] == "akasa-remote-approval"
```

### Test 2: handle_rpc — tool call error
```python
@pytest.mark.asyncio
async def test_handle_rpc_tool_call_error():
    from scripts.akasa_mcp_server import handle_rpc
    with patch("scripts.akasa_mcp_server.request_remote_approval", side_effect=Exception("Connection failed")):
        result = await handle_rpc({
            "id": 1, "method": "tools/call",
            "params": {"name": "request_remote_approval", "arguments": {"command": "ls", "cwd": "."}}
        })
    data = json.loads(result)
    assert data["result"]["isError"] is True
    assert "Connection failed" in data["result"]["content"][0]["text"]
```

### Test 3: AKASA_CHAT_ID empty validation
```python
@pytest.mark.asyncio
async def test_request_remote_approval_no_chat_id():
    from scripts.akasa_mcp_server import request_remote_approval
    with patch("scripts.akasa_mcp_server.AKASA_CHAT_ID", ""):
        with pytest.raises(ValueError, match="AKASA_CHAT_ID"):
            await request_remote_approval(command="ls", cwd=".")
```

### Test 4: metadata missing required fields
```python
@pytest.mark.asyncio
async def test_create_action_request_missing_metadata_fields(valid_headers):
    payload = {
        "chat_id": "12345",
        "message": "test",
        "metadata": {"request_id": "r1"}  # missing command, cwd
    }
    with patch("app.routers.actions.settings.ALLOWED_TELEGRAM_CHAT_IDS", "12345"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/v1/actions/request", json=payload, headers=valid_headers)
        assert response.status_code == 400
```

---

## ✅ สรุป

| Category | Count |
|----------|-------|
| 🔴 Critical | 2 (stdin blocking, error handling inconsistency ← อันนี้ actually ถูกต้องตาม MCP spec แต่ขาด comment) |
| 🟡 Medium | 3 (validation gaps) |
| 🟢 Minor | 3 (type hints, deprecation, test coverage) |

**ข้อเสนอสำคัญที่ควรทำ:**
1. แก้ `sys.stdin` blocking issue ใน `main()`
2. เพิ่ม validation สำหรับ `chat_id`, `request_id`, `command`, `cwd`
3. เพิ่ม test coverage สำหรับ `handle_rpc` function
4. เพิ่ม `Optional[str]` type hint ให้ `description` parameter
