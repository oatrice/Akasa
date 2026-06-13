### Manual Verification Guide

This guide details how to verify the Render.com blueprint deployment, Redis configuration, and the local tool daemon's connection to the remote backend.

#### Prerequisites
- Your backend is deployed on Render at: `https://akasa-backend-6a8v.onrender.com`
- You have configured the environment variables `TELEGRAM_BOT_TOKEN`, `WEBHOOK_SECRET_TOKEN`, `AKASA_API_KEY`, and `AKASA_DAEMON_SECRET` in the Render dashboard.

---

#### Step 1: Register the Telegram Webhook
Run the following curl command in your terminal to point Telegram updates to your Render instance (replace `<TOKEN>` and `<SECRET>` with your actual credentials configured on Render):

```bash
curl -F "url=https://akasa-backend-6a8v.onrender.com/api/v1/telegram/webhook" \
     -F "secret_token=<YOUR_WEBHOOK_SECRET_TOKEN>" \
     https://api.telegram.org/bot<YOUR_TELEGRAM_BOT_TOKEN>/setWebhook
```

**Expected Result:**
```json
{"ok":true,"result":true,"description":"Webhook was set"}
```

---

#### Step 2: Configure and Start the Local Tool Daemon
To allow the local daemon to pull commands from the Render Redis instance and report back to the Render Web Service, launch the daemon in your terminal with the following environment variables:

```bash
# 1. Point the API URL to Render
export AKASA_API_URL="https://akasa-backend-6a8v.onrender.com"

# 2. Set the Daemon Secret key matching the one on Render
export AKASA_DAEMON_SECRET="<YOUR_AKASA_DAEMON_SECRET>"

# 3. Connect to the Render Redis external URL
export REDIS_URL="<YOUR_RENDER_REDIS_EXTERNAL_URL>"

# 4. Launch the daemon in the virtual environment
venv/bin/python scripts/local_tool_daemon.py
```

**Expected Result:**
The daemon starts polling successfully:
```
INFO:__main__:Starting to poll queue akasa:commands:gemini
INFO:__main__:Starting to poll queue akasa:commands:luma
...
```

---

#### Step 3: Trigger a Command from Telegram
Go to your Telegram bot chat and send the following command:

```text
/gemini status
```

**Expected Result:**
1. In the **Telegram Chat**: You will see a `⏳ Command Enqueued` message with a Command ID (e.g. `cmd_xxxxxx`).
2. In the **Daemon Terminal Logs**: You will see the command dequeued, picked up, run, and completed:
   ```
   INFO:__main__:DEQUEUED cmd_xxxxxx — tool=gemini, command=check_status...
   INFO:app.services.command_queue_service:[STATUS] cmd_xxxxxx → picked_up
   INFO:app.services.command_queue_service:[STATUS] cmd_xxxxxx → running
   INFO:__main__:COMPLETED cmd_xxxxxx — tool=gemini, command=check_status...
   ```
3. In the **Telegram Chat**: You will receive a subsequent message containing the **Command Result** showing `check_status` output (e.g., current model name, status) confirming end-to-end connectivity.
