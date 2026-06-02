"""Quick API test script."""
import httpx, json, time

BASE = "http://localhost:8000"

# Health
r = httpx.get(f"{BASE}/api/health")
print(f"Health: {r.json()}")

# List debates
r = httpx.get(f"{BASE}/api/debates")
print(f"List status: {r.status_code}, type: {type(r.json())}, body: {json.dumps(r.json(), ensure_ascii=False)[:200]}")
