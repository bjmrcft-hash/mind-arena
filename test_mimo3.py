import asyncio, sys, io, json, subprocess
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import os
from engine.llm.llm_service import LLMService
from engine.model_health import check_model_health

async def test():
    # Get auth profiles
    auth_path = os.path.expanduser("~/.openclaw/agents/main/agent/auth-profiles.json")
    if os.path.exists(auth_path):
        with open(auth_path) as f:
            auth = json.load(f)
        
        # Find xiaomi-coding key
        for profile_id, profile in auth.items():
            if "xiaomi" in profile_id.lower():
                print(f"Profile: {profile_id}")
                key = profile.get("apiKey", "")
                print(f"Key prefix: {key[:20]}...")
                
                if key:
                    llm = LLMService(
                        base_url="https://token-plan-cn.xiaomimimo.com/v1",
                        api_key=key
                    )
                    for model in ["mimo-v2.5-pro", "mimo-v2.5"]:
                        s = await check_model_health(llm, model, timeout=20)
                        status = "OK" if s.available else "FAIL"
                        err = s.error[:80] if s.error else ""
                        print(f"  {model}: {status} {s.latency_ms:.0f}ms {err}")
    else:
        print(f"Auth file not found: {auth_path}")

asyncio.run(test())
