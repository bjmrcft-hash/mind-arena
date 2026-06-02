import httpx
r = httpx.get('http://localhost:8000/api/debates/3fb5d3ac-e441-4dd4-a20f-80384c58ec40', timeout=10)
msgs = r.json()['messages']
for m in msgs:
    print(f"role={m['role']} | type={m['message_type']} | round={m['round_number']} | exchange={m['exchange_number']} | len={len(m['content'])}")
