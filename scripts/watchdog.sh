#!/usr/bin/env bash
# =============================================================================
# Akasa Agent Watchdog
# Monitors Antigravity IDE + Zed logs and notifies via Telegram (Akasa bot)
# when agent crashes / termination errors are detected.
#
# Usage:
#   ./scripts/watchdog.sh start   — Start watchdog in background
#   ./scripts/watchdog.sh stop    — Stop watchdog
#   ./scripts/watchdog.sh status  — Show if running
#   ./scripts/watchdog.sh test    — Send a test notification
# =============================================================================

set -euo pipefail

# --------------- Config ---------------
PID_FILE="/tmp/akasa_watchdog.pid"
LOG_FILE="/tmp/akasa_watchdog.log"

# Load env from project .env if available
ENV_FILE="$(cd "$(dirname "$0")/.." && pwd)/.env"
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC2046
  export $(grep -v '^#' "$ENV_FILE" | grep -E '^(TELEGRAM_BOT_TOKEN|AKASA_CHAT_ID)=' | xargs)
fi

BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
CHAT_ID="${AKASA_CHAT_ID:-}"

# Log files to monitor
ZED_LOG="$HOME/Library/Logs/Zed/Zed.log"
ANTIGRAVITY_DAEMON_DIR="$HOME/.gemini/antigravity/daemon"

# Patterns that indicate agent crash / termination
# Zed: no direct "Agent terminated" in file — watch Zed.log for relevant errors
ZED_PATTERNS=(
  "panic"
  "agent.*error"
  "crashed"
)

# Antigravity daemon patterns (from ls_*.log files)
AG_PATTERNS=(
  "MCP_SERVER_INIT_ERROR"
  "Got signal terminated"
  "panic"
)

# Cooldown: don't re-notify the same pattern within N seconds
COOLDOWN_SECS=60
LAST_NOTIFY_FILE="/tmp/akasa_watchdog_last_notify"

# --------------------------------------

usage() {
  echo "Usage: $0 {start|stop|status|test}"
  exit 1
}

send_telegram() {
  local message="$1"
  if [[ -z "$BOT_TOKEN" || -z "$CHAT_ID" ]]; then
    echo "[watchdog] WARNING: TELEGRAM_BOT_TOKEN or AKASA_CHAT_ID not set, cannot notify." | tee -a "$LOG_FILE"
    return
  fi

  local json_payload
  json_payload=$(python3 -c '
import json
import sys
payload = {
    "chat_id": sys.argv[1],
    "text": sys.argv[2],
    "parse_mode": "Markdown"
}
print(json.dumps(payload))
' "$CHAT_ID" "$message")

  local response
  response=$(curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
    -H "Content-Type: application/json" \
    -d "$json_payload")
    
  if ! echo "$response" | grep -q '"ok":true'; then
    echo "[watchdog] Telegram API Error: $response" >&2
    echo "[watchdog] Telegram API Error: $response" >> "$LOG_FILE"
  fi
}

check_cooldown() {
  local key="$1"
  local now
  now=$(date +%s)
  local last=0
  if [[ -f "$LAST_NOTIFY_FILE" ]]; then
    last=$(grep -F "$key=" "$LAST_NOTIFY_FILE" 2>/dev/null | tail -1 | cut -d= -f2 || echo 0)
  fi
  if (( now - last < COOLDOWN_SECS )); then
    return 1  # still in cooldown
  fi
  # Update timestamp for this key
  if [[ -f "$LAST_NOTIFY_FILE" ]]; then
    sed -i '' "/^${key}=/d" "$LAST_NOTIFY_FILE" 2>/dev/null || true
  fi
  echo "${key}=${now}" >> "$LAST_NOTIFY_FILE"
  return 0
}

watch_loop() {
  echo "[watchdog] Started at $(date). PID=$$" | tee -a "$LOG_FILE"

  # --- Watch Zed log ---
  if [[ -f "$ZED_LOG" ]]; then
    (
      tail -n 0 -F "$ZED_LOG" 2>/dev/null | while IFS= read -r line; do
        for pattern in "${ZED_PATTERNS[@]}"; do
          if echo "$line" | grep -qi "$pattern"; then
            echo "[watchdog][Zed] Detected: $line" >> "$LOG_FILE"
            if check_cooldown "zed_${pattern}"; then
              local ts
              ts=$(date "+%Y-%m-%d %H:%M:%S")
              send_telegram "🚨 *Akasa Watchdog Alert*

*IDE:* Zed
*Time:* ${ts}
*Pattern:* ${pattern}
*Log:* ${line:0:200}"
            fi
          fi
        done
      done
    ) &
    echo "[watchdog] Monitoring Zed log: $ZED_LOG" | tee -a "$LOG_FILE"
  else
    echo "[watchdog] Zed log not found, skipping: $ZED_LOG" | tee -a "$LOG_FILE"
  fi

  # --- Watch Antigravity daemon logs (watch for new ls_*.log files too) ---
  (
    # Track already-watched files in a temp file (bash 3.2 compatible, no declare -A)
    WATCHED_FILE="/tmp/akasa_watchdog_ag_watched_$$"
    touch "$WATCHED_FILE"

    while true; do
      for log_file in "$ANTIGRAVITY_DAEMON_DIR"/ls_*.log; do
        [[ -f "$log_file" ]] || continue
        if ! grep -qF "$log_file" "$WATCHED_FILE" 2>/dev/null; then
          echo "$log_file" >> "$WATCHED_FILE"
          echo "[watchdog][AG] Now watching: $log_file" >> "$LOG_FILE"
          (
            tail -n 0 -F "$log_file" 2>/dev/null | while IFS= read -r line; do
              for pattern in "${AG_PATTERNS[@]}"; do
                if echo "$line" | grep -qi "$pattern"; then
                  echo "[watchdog][Antigravity] Detected: $line" >> "$LOG_FILE"
                  safe_key=$(echo "${pattern}" | tr -cd '[:alnum:]_')
                  if check_cooldown "ag_${safe_key}"; then
                    ts=$(date "+%Y-%m-%d %H:%M:%S")
                    send_telegram "⚠️ *Akasa Watchdog Alert*

*IDE:* Antigravity
*Time:* ${ts}
*Pattern:* ${pattern}
*Log:* ${line:0:200}"
                  fi
                fi
              done
            done
            rm -f "$WATCHED_FILE"
          ) &
        fi
      done
      sleep 5
    done
  ) &

  echo "[watchdog] Monitoring Antigravity daemon dir: $ANTIGRAVITY_DAEMON_DIR" | tee -a "$LOG_FILE"
  echo "[watchdog] Watching for patterns..." | tee -a "$LOG_FILE"

  # Keep the parent alive while children run
  wait
}

cmd_start() {
  if [[ -f "$PID_FILE" ]]; then
    local old_pid
    old_pid=$(cat "$PID_FILE")
    if kill -0 "$old_pid" 2>/dev/null; then
      echo "Watchdog already running (PID $old_pid). Run '$0 stop' first."
      exit 1
    else
      rm -f "$PID_FILE"
    fi
  fi

  echo "Starting Akasa Agent Watchdog..."
  watch_loop &
  local wdog_pid=$!
  echo "$wdog_pid" > "$PID_FILE"
  echo "✅ Watchdog started (PID $wdog_pid). Log: $LOG_FILE"
}

cmd_stop() {
  if [[ ! -f "$PID_FILE" ]]; then
    echo "Watchdog is not running (no PID file found)."
    exit 0
  fi
  local pid
  pid=$(cat "$PID_FILE")
  if kill -0 "$pid" 2>/dev/null; then
    # Kill the whole process group
    kill -- "-$pid" 2>/dev/null || kill "$pid"
    rm -f "$PID_FILE"
    echo "✅ Watchdog (PID $pid) stopped."
  else
    echo "Watchdog PID $pid not found (already stopped)."
    rm -f "$PID_FILE"
  fi
}

cmd_status() {
  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid=$(cat "$PID_FILE")
    if kill -0 "$pid" 2>/dev/null; then
      echo "🟢 Watchdog is RUNNING (PID $pid)"
      echo "   Log: $LOG_FILE"
    else
      echo "🔴 Watchdog PID $pid is NOT running (stale PID file)"
      rm -f "$PID_FILE"
    fi
  else
    echo "🔴 Watchdog is NOT running"
  fi
}

cmd_test() {
  echo "Sending test notification..."
  send_telegram "🧪 *Akasa Watchdog Test*

Watchdog is running correctly.
*Time:* $(date '+%Y-%m-%d %H:%M:%S')"
  echo "✅ Test notification sent (check Telegram)."
}

# --- Main ---
COMMAND="${1:-}"
case "$COMMAND" in
  start)  cmd_start ;;
  stop)   cmd_stop ;;
  status) cmd_status ;;
  test)   cmd_test ;;
  *)      usage ;;
esac
