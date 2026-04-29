# Manual Verification Guide: Model Field in Task Notifications

## Prerequisites
- Akasa backend running on localhost:8000
- Redis service running
- Telegram bot configured with valid token
- Test chat ID available (e.g., 6346467495)

## Step 1: Test External AI Use Case
Send HTTP POST request to /api/v1/notifications/task-complete with model parameter:
```bash
curl -X POST http://localhost:8000/api/v1/notifications/task-complete \
  -H "X-Akasa-API-Key: default-dev-key" \
  -H "Content-Type: application/json" \
  -d '{
    "project": "Akasa",
    "task": "Test external model",
    "status": "success",
    "source": "Windsurf",
    "model": "SWE-1.6",
    "chat_id": "6346467495"
  }'
```

## Step 2: Verify Notification in Telegram
Check Telegram chat for notification containing:
- *Source:* Windsurf
- *Model:* SWE-1.6

## Step 3: Test Local AI Use Case
Set model preference via Telegram:
```
/model gpt-4o
```

Send notification without model:
```bash
curl -X POST http://localhost:8000/api/v1/notifications/task-complete \
  -H "X-Akasa-API-Key: default-dev-key" \
  -H "Content-Type: application/json" \
  -d '{
    "project": "Akasa",
    "task": "Test local model",
    "status": "success",
    "chat_id": "6346467495"
  }'
```

## Step 4: Verify Local Model Notification
Check Telegram notification shows:
- *Model:* gpt-4o (from Redis preference)

## Step 5: Test No Model Case
Clear preference and send without model.

## Expected Result: 
- External model overrides preference
- Local model uses preference  
- No model when neither available
- Backward compatibility maintained