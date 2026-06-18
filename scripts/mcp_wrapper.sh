#!/bin/bash
export AKASA_API_URL="https://akasa-backend-6a8v.onrender.com"
export AKASA_API_KEY="Jril2v4cbZ9nla57jwXtALvtEd502TDP/EyRD7t02rI="
export AKASA_CHAT_ID="6346467495"

SCRIPT_DIR="/Users/oatrice/Software Project/Akasa/scripts"
PYTHON="/Users/oatrice/Software Project/Akasa/venv/bin/python"
SERVER="/Users/oatrice/Software Project/Akasa/scripts/akasa_mcp_server.py"

echo "$(date): wrapper started" >> "$SCRIPT_DIR/mcp_debug.log"

tee -a "$SCRIPT_DIR/mcp_input.log" | "$PYTHON" "$SERVER" 2>>"$SCRIPT_DIR/mcp_stderr.log" | tee -a "$SCRIPT_DIR/mcp_output.log"
