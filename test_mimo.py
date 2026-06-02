import asyncio, sys, io
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import os
from engine.llm.llm_service import LLMService
from engine.model_health import check_model_health

async def test():
    key = os.environ.get("XIAOMI_CODING_API_KEY", "")
    print(f"Key prefix: {key[:15]}...")
    
    endpoints = [
        ("token-plan-sgp.xiaomimimo.com", "https://token-plan-sgp.xiaomimimo.com/v1"),
        ("api.xiaomimimo.com", "https://api.xiaomimimo.com/v1"),
        ("mimo.xiaomi.com", "https://mimo.xiaomi.com/v1"),
    ]
    
    models = ["MiniMax-M2.7", "mimo-v2.5-pro", "mimo-v2-flash"]
    
    for name, base_url in endpoints:
        print(f"\n=== {name} ===")
        llm = LLMService(base_url=base_url, api_key=key)
        for model in models[:1]:  # Just test one model per endpoint
            s = await check_model_health(llm, model, timeout=15)
            status = "OK" if s.available else "FAIL"
            err = s.error[:80] if s.error else ""
            print(f"  {model}: {status} {s.latency_ms:.0f}ms {err}")

asyncio.run(test())
