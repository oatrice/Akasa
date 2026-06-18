import sys
import subprocess
import os

LOG_DIR = "/Users/oatrice/Software Project/Akasa/scripts"

with open(os.path.join(LOG_DIR, "mcp_env.log"), "w") as f:
    for k, v in os.environ.items():
        f.write(f"{k}={v}\n")

proc = subprocess.Popen(
    [
        "/Users/oatrice/Software Project/Akasa/venv/bin/python",
        "/Users/oatrice/Software Project/Akasa/scripts/akasa_mcp_server.py"
    ],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

import threading

def forward_stdin():
    with open(os.path.join(LOG_DIR, "mcp_stdin.log"), "wb") as f:
        while True:
            chunk = sys.stdin.buffer.read(1)
            if not chunk:
                break
            f.write(chunk)
            f.flush()
            proc.stdin.write(chunk)
            proc.stdin.flush()

def forward_stdout():
    with open(os.path.join(LOG_DIR, "mcp_stdout.log"), "wb") as f:
        while True:
            chunk = proc.stdout.read(1)
            if not chunk:
                break
            f.write(chunk)
            f.flush()
            sys.stdout.buffer.write(chunk)
            sys.stdout.buffer.flush()

def forward_stderr():
    with open(os.path.join(LOG_DIR, "mcp_stderr.log"), "wb") as f:
        while True:
            chunk = proc.stderr.read(1)
            if not chunk:
                break
            f.write(chunk)
            f.flush()
            sys.stderr.buffer.write(chunk)
            sys.stderr.buffer.flush()

t1 = threading.Thread(target=forward_stdin)
t2 = threading.Thread(target=forward_stdout)
t3 = threading.Thread(target=forward_stderr)

t1.start()
t2.start()
t3.start()

proc.wait()
sys.exit(proc.returncode)
