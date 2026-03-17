"""
Manual verification for Bug 2 (Redis queue TTL interaction).

Bug (old behavior):
  Enqueueing a new command with a shorter TTL used to call EXPIRE on the shared
  queue list key `akasa:commands:{tool}`, potentially expiring the whole queue.

Fix (current behavior):
  The queue list key MUST NOT have its TTL shortened/overwritten by per-command TTL.
  Only per-command meta key `akasa:cmd_meta:{command_id}` should use TTL.

This script:
  1) Enqueues a first command (ttl A)
  2) Manually sets a baseline TTL on the queue key (simulating "queue key has TTL")
  3) Enqueues a second command with a shorter TTL (ttl B)
  4) Verifies the queue key TTL did NOT drop to ttl B
  5) Verifies each command's meta key has an appropriate TTL

Run:
  python3 scripts/manual_verify_bug2_queue_ttl.py

Optional env:
  REDIS_URL (defaults to config/settings)
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

# Ensure `import app...` works when running as a script.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _queue_key(tool: str) -> str:
    return f"akasa:commands:{tool}"


def _meta_key(command_id: str) -> str:
    return f"akasa:cmd_meta:{command_id}"


async def _amain() -> int:
    parser = argparse.ArgumentParser(
        description="Manual verify Bug 2: enqueue TTL must not expire whole queue"
    )
    parser.add_argument(
        "--tool",
        default="gemini",
        help="Tool queue to use (must exist in config/command_whitelist.yaml). Default: gemini",
    )
    parser.add_argument(
        "--command-a",
        default="check_status",
        help="Whitelisted command name for first enqueue. Default: check_status",
    )
    parser.add_argument(
        "--command-b",
        default="check_status",
        help="Whitelisted command name for second enqueue. Default: check_status",
    )
    parser.add_argument(
        "--ttl-a",
        type=int,
        default=600,
        help="TTL seconds for first command's meta key. Default: 600",
    )
    parser.add_argument(
        "--baseline-queue-ttl",
        type=int,
        default=1200,
        help="TTL seconds to set on the QUEUE key (simulating prior state). Default: 1200",
    )
    parser.add_argument(
        "--ttl-b",
        type=int,
        default=30,
        help="TTL seconds for second command's meta key (shorter). Default: 30",
    )
    parser.add_argument(
        "--user-id",
        type=int,
        default=123,
        help="Telegram user_id to stamp in payload. Default: 123",
    )
    parser.add_argument(
        "--chat-id",
        type=int,
        default=456,
        help="Telegram chat_id to stamp in payload. Default: 456",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Delete the queue key first (DANGER: removes pending commands for that tool).",
    )

    args = parser.parse_args()

    from app.models.command import CommandQueueRequest
    from app.services.command_queue_service import enqueue_command
    from app.services.redis_service import redis_pool

    tool = str(args.tool).strip().lower()
    qkey = _queue_key(tool)

    if args.cleanup:
        await redis_pool.delete(qkey)

    # Enqueue first command
    req_a = CommandQueueRequest(
        tool=tool,
        command=args.command_a,
        args={},
        ttl_seconds=int(args.ttl_a),
    )
    resp_a = await enqueue_command(req_a, user_id=int(args.user_id), chat_id=int(args.chat_id))
    meta_a = _meta_key(resp_a.command_id)

    # Manually set a baseline TTL on the QUEUE key (simulates "bad legacy state")
    # Ensure queue exists (it should, after enqueue).
    expire_ok = await redis_pool.expire(qkey, int(args.baseline_queue_ttl))
    ttl_queue_before = await redis_pool.ttl(qkey)
    if not expire_ok or ttl_queue_before <= 0:
        print("=== Bug 2 manual verification (queue TTL) ===")
        print(f"Tool: {tool}")
        print(f"Queue key: {qkey}")
        print(f"Command A: {resp_a.command_id} (meta ttl target={args.ttl_a}s) meta={meta_a}")
        print()
        print(
            "FAIL: Could not apply baseline TTL to the queue key.\n"
            "- This usually means the queue list key disappeared (empty list -> Redis deletes the key),\n"
            "  often because a local daemon is actively BLPOP-ing this tool queue.\n"
            "- To get a deterministic verification, stop the local tool daemon (or use a dedicated Redis instance)\n"
            "  and re-run this script.\n"
            f"Observed TTL(queue)={ttl_queue_before}s (Redis TTL: -2 key missing, -1 no expiry)."
        )
        return 2

    # Small delay so TTL readings are stable/monotonic
    time.sleep(0.25)

    # Enqueue second command (shorter TTL)
    req_b = CommandQueueRequest(
        tool=tool,
        command=args.command_b,
        args={},
        ttl_seconds=int(args.ttl_b),
    )
    resp_b = await enqueue_command(req_b, user_id=int(args.user_id), chat_id=int(args.chat_id))
    meta_b = _meta_key(resp_b.command_id)

    ttl_queue_after = await redis_pool.ttl(qkey)
    ttl_meta_a = await redis_pool.ttl(meta_a)
    ttl_meta_b = await redis_pool.ttl(meta_b)

    print("=== Bug 2 manual verification (queue TTL) ===")
    print(f"Tool: {tool}")
    print(f"Queue key: {qkey}")
    print(f"Command A: {resp_a.command_id} (meta ttl target={args.ttl_a}s) meta={meta_a}")
    print(f"Command B: {resp_b.command_id} (meta ttl target={args.ttl_b}s) meta={meta_b}")
    print()
    print(f"Queue TTL before enqueue B: {ttl_queue_before}s")
    print(f"Queue TTL after  enqueue B: {ttl_queue_after}s")
    print(f"Meta TTL A: {ttl_meta_a}s")
    print(f"Meta TTL B: {ttl_meta_b}s")
    print()

    # Assertions:
    # - Queue TTL should not suddenly drop to ~ttl_b (the regression).
    # - Queue TTL should be roughly the baseline and non-increasing as time passes.
    # - Meta keys should have TTLs close to their requested values (within tolerance).
    if ttl_queue_before <= 0 or ttl_queue_after <= 0:
        print("FAIL: Queue TTL is missing or non-positive; baseline EXPIRE may not have applied.")
        return 2

    # If the bug existed, we'd expect ttl_queue_after ~ ttl_b (or at least far smaller than before).
    # We allow normal passage of time, so after should be <= before but not drastically smaller.
    if ttl_queue_after < min(int(args.ttl_b) + 2, ttl_queue_before - 5):
        print(
            "FAIL: Queue TTL appears to have been shortened drastically "
            f"(after={ttl_queue_after}s, before={ttl_queue_before}s, ttl_b={args.ttl_b}s)."
        )
        return 1

    # Meta TTL sanity checks (allow generous drift because time passes and Redis TTL is integer seconds)
    if ttl_meta_a <= 0:
        print("FAIL: Meta key for command A is missing/expired unexpectedly.")
        return 3
    if ttl_meta_b <= 0:
        print("FAIL: Meta key for command B is missing/expired unexpectedly.")
        return 4

    # Upper bounds: should not exceed requested TTL by a lot
    if ttl_meta_a > int(args.ttl_a) + 5:
        print("FAIL: Meta TTL A is unexpectedly larger than requested.")
        return 5
    if ttl_meta_b > int(args.ttl_b) + 5:
        print("FAIL: Meta TTL B is unexpectedly larger than requested.")
        return 6

    print("PASS: Queue TTL was not overridden by per-command TTL.")
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_amain()))


if __name__ == "__main__":
    main()

