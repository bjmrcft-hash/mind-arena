"""Monitor debate with exchange detail."""
import httpx
import time
import sys
import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SID = "1d32a9c3-3227-46ec-b01b-24449edc5994"
BASE = "http://localhost:8000"

last_count = 0
while True:
    r = httpx.get(f"{BASE}/api/debates/{SID}", timeout=10)
    d = r.json()
    s = d["session"]
    msgs = d["messages"]
    
    print(f"[{s['status']}] round={s['current_round']} exchange={s['current_exchange']} msgs={len(msgs)}")
    
    for m in msgs[last_count:]:
        preview = m["content"][:100].replace("\n", " ")
        print(f"  [{m['role']}] {m['message_type']}: {preview}")
    last_count = len(msgs)
    
    if s["status"] in ("completed", "stopped", "error"):
        break
    time.sleep(15)

print("\n=== DONE ===")
print(f"Status: {s['status']}")
print(f"Total messages: {len(msgs)}")
