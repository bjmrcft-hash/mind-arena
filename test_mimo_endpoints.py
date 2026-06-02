import asyncio, sys, io, json
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import os
from engine.llm.llm_service import LLMService
from engine.model_health import check_model_health

async def test():
    auth_path = os.path.expanduser("~/.openclaw/agents/main/agent/auth-profiles.json")
    with open(auth_path) as f:
        auth = json.load(f)
    
    xiaomi_key = auth["profiles"]["xiaomi:default"]["key"]
    
    endpoints = [
        ("token-plan-cn", "https://token-plan-cn.xiaomimimo.com/v1"),
        ("token-plan-sgp", "https://token-plan-sgp.xiaomimimo.com/v1"),
        ("api", "https://api.xiaomimimo.com/v1"),
    ]
    
    for name, base_url in endpoints:
        print(f"\n=== {name} ===")
        llm = LLMService(base_url=base_url, api_key=xiaomi_key)
        s = await check_model_health(llm, "mimo-v2.5-pro", timeout=15)
        status = "OK" if s.available else "FAIL"
        err = s.error[:100] if s.error else ""
        print(f"  mimo-v2.5-pro: {status} {s.latency_ms:.0f}ms {err}")

asyncio.run(test())
