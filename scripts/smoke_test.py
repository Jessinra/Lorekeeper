#!/usr/bin/env python
"""
Smoke test: spawns the lorekeeper MCP server as a subprocess and sends
3 tool calls over stdio. Exits 0 on success, 1 on any failure.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).parent.parent

REQUESTS = [
    # 1. search for something that should be in the migrated store
    {
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {
            "name": "lore_search",
            "arguments": {"query": "checkout payment flow", "limit": 3},
        },
    },
    # 2. insert a test memory
    {
        "jsonrpc": "2.0", "id": 2, "method": "tools/call",
        "params": {
            "name": "lore_insert",
            "arguments": {
                "memories": [
                    {"title": "smoke test memory", "description": "test", "content": "smoke test"}
                ]
            },
        },
    },
    # 3. search again to confirm insert
    {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
     "params": {"name": "lore_search", "arguments": {"query": "smoke test memory", "limit": 3}}},
]

INIT = {"jsonrpc": "2.0", "id": 0, "method": "initialize",
        "params": {"protocolVersion": "2024-11-05",
                   "capabilities": {},
                   "clientInfo": {"name": "smoke_test", "version": "1.0"}}}


def send(proc: subprocess.Popen, msg: dict) -> dict:
    line = json.dumps(msg) + "\n"
    proc.stdin.write(line.encode())
    proc.stdin.flush()
    # Read until we get a non-notification response matching our id
    while True:
        raw = proc.stdout.readline()
        if not raw:
            raise RuntimeError("Server closed stdout")
        try:
            resp = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if resp.get("id") == msg.get("id"):
            return resp


def main() -> None:
    proc = subprocess.Popen(
        ["uv", "run", "lorekeeper"],
        cwd=str(REPO),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    try:
        # Handshake
        resp = send(proc, INIT)
        if "error" in resp:
            print(f"FAIL init: {resp['error']}")
            sys.exit(1)
        # Send initialized notification
        proc.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
        proc.stdin.flush()

        for req in REQUESTS:
            resp = send(proc, req)
            if "error" in resp:
                print(f"FAIL [{req['params']['name']}]: {resp['error']}")
                sys.exit(1)
            content = resp.get("result", {}).get("content", [{}])
            text = content[0].get("text", "") if content else ""
            try:
                data = json.loads(text)
                print(f"OK  [{req['params']['name']}]: {json.dumps(data)[:120]}...")
            except Exception:
                print(f"OK  [{req['params']['name']}]: {text[:120]}")

        print("\nSmoke test PASSED")
    finally:
        proc.terminate()
        proc.wait()


if __name__ == "__main__":
    main()
