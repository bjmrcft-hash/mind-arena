import httpx, time, sys, io
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
SID = "844f247d-10db-48d0-804d-67f9b450e0b2"
last = 0
while True:
    d = httpx.get(f"http://localhost:8000/api/debates/{SID}", timeout=10).json()
    s = d["session"]
    msgs = d["messages"]
    for m in msgs[last:]:
        print(f"  [{m['role']}] {m['message_type']}: {m['content'][:60].replace(chr(10),' ')}")
    last = len(msgs)
    print(f"[{s['status']}] msgs={len(msgs)}")
    if s["status"] in ("completed", "stopped", "error"):
        break
    time.sleep(15)
print("DONE")
