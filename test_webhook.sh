#!/bin/bash
curl -X POST http://127.0.0.1:8000/api/v1/telegram/webhook \
  -H "Content-Type: application/json" \
  -H "x-telegram-bot-api-secret-token: q5RcWqossAe0FToEHvVCEVo7wP8RS-WQI7nQSrYs_GA" \
  -d '{
    "update_id": 10000,
    "message": {
      "message_id": 1365,
      "date": 1441645532,
      "chat": {
        "id": 1111111,
        "type": "private",
        "username": "TestUser",
        "first_name": "Test",
        "last_name": "User"
      },
      "text": "Hello Akasa, this is a manual test message!"
    }
  }'
