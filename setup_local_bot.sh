#!/bin/bash
# Script to easily test the bot locally using ngrok

# 1. Load variables from .env
if [ -f .env ]; then
  export $(cat .env | xargs)
else
  echo ".env file not found!"
  exit 1
fi

if [[ -z "$TELEGRAM_BOT_TOKEN" || -z "$WEBHOOK_SECRET_TOKEN" ]]; then
  echo "Missing TELEGRAM_BOT_TOKEN or WEBHOOK_SECRET_TOKEN in .env"
  exit 1
fi

echo "✅ Environment variables loaded."

# 2. Start uvicorn (FastAPI backend)
echo "🚀 Starting uvicorn on port 8000..."
# Create a wrapper script to add timestamps to uvicorn logs
cat > /tmp/uvicorn_logger.sh << 'EOF'
#!/bin/bash
while IFS= read -r line; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $line"
done
EOF
chmod +x /tmp/uvicorn_logger.sh

venv/bin/uvicorn app.main:app --port 8000 --reload 2>&1 | /tmp/uvicorn_logger.sh > /tmp/uvicorn.log &
UVICORN_PID=$!
echo "✅ uvicorn started (PID: $UVICORN_PID), logs: /tmp/uvicorn.log (with timestamps)"

# 3. Start local tool daemon
echo "🤖 Starting local_tool_daemon..."
# Create a wrapper script to add timestamps to tool daemon logs
cat > /tmp/tool_daemon_logger.sh << 'EOF'
#!/bin/bash
while IFS= read -r line; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $line"
done
EOF
chmod +x /tmp/tool_daemon_logger.sh

source venv/bin/activate && python3 scripts/local_tool_daemon.py 2>&1 | /tmp/tool_daemon_logger.sh > /tmp/tool_daemon.log &
DAEMON_PID=$!
echo "✅ local_tool_daemon started (PID: $DAEMON_PID), logs: /tmp/tool_daemon.log (with timestamps)"

sleep 2 # Wait for services to initialize

# 4. Check if ngrok is running, if not start it in the background
if ! pgrep -x "ngrok" > /dev/null
then
    echo "🚀 Starting ngrok on port 8000..."
    ngrok http 8000 > /dev/null &
    sleep 3 # Wait for ngrok to initialize
else
    echo "✅ ngrok is already running."
fi

# 5. Retrieve the dynamic ngrok URL
NGROK_URL=$(curl -s localhost:4040/api/tunnels | python3 -c "import sys, json; print(json.load(sys.stdin)['tunnels'][0]['public_url'])")

if [[ -z "$NGROK_URL" ]]; then
  echo "❌ Failed to get ngrok URL. Make sure ngrok is running properly."
  exit 1
fi

echo "🔗 ngrok Public URL: $NGROK_URL"

# 6. Set the webhook on Telegram
WEBHOOK_URL="${NGROK_URL}/api/v1/telegram/webhook"
echo "🛠️ Setting Telegram Webhook to: $WEBHOOK_URL"

RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{
    \"url\": \"${WEBHOOK_URL}\",
    \"secret_token\": \"${WEBHOOK_SECRET_TOKEN}\"
  }")

if echo "$RESPONSE" | grep -q '"ok":true'; then
  echo -e "\n🎉 Webhook set successfully!"
  echo "👉 You can now open your Telegram app and send a message to your bot."
else
  echo -e "\n❌ Failed to set webhook. Telegram API response:"
  echo "$RESPONSE"
fi
