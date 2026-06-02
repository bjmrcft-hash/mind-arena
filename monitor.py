"""Monitor a running debate."""
import httpx
import time
import sys
import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SID = "93da2f71-4638-42b9-85a0-3c6cffffe0f2"
BASE = "http://localhost:8000"

last_count = 0
while True:
    r = httpx.get(f"{BASE}/api/debates/{SID}", timeout=10)
    d = r.json()
    s = d["session"]
    msgs = d["messages"]
    
    print(f"[{s['status']}] round={s['current_round']} exchange={s['current_exchange']} msgs={len(msgs)}")
    
    # Print new messages
    for m in msgs[last_count:]:
        preview = m["content"][:120].replace("\n", " ")
        print(f"  [{m['role']}] {m['message_type']}: {preview}")
    last_count = len(msgs)
    
    if s["status"] in ("completed", "stopped", "error"):
        break
    time.sleep(15)

print("\n=== DEBATE COMPLETE ===")
print(f"Status: {s['status']}")
print(f"Total messages: {len(msgs)}")
