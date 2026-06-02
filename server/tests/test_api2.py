"""Test the server API end-to-end."""
import httpx
import time
import json

BASE = "http://localhost:8001"

# Create debate
r = httpx.post(f"{BASE}/api/debates", json={
    "topic": "远程办公是否应该成为常态",
    "mode": "quick",
    "tts_enabled": False
}, timeout=10)
print(f"Create: {r.status_code}")
session = r.json()
sid = session["id"]
print(f"  ID: {sid}")

# Wait for some progress
print("Waiting 45s...")
time.sleep(45)

# Check session
r = httpx.get(f"{BASE}/api/debates/{sid}", timeout=10)
data = r.json()
s = data["session"]
msgs = data["messages"]
print(f"Status: {s['status']}")
print(f"Round: {s['current_round']}")
print(f"Messages: {len(msgs)}")
for m in msgs:
    role = m["role"]
    content = m["content"][:80].replace("\n", " ")
    print(f"  [{role}] {content}")
