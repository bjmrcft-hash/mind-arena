import asyncio, sys, io
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import os, json
from engine.llm.llm_service import LLMService
from engine.model_health import check_model_health

async def test():
    # Read the actual key from openclaw config
    import subprocess
    result = subprocess.run(
        ["openclaw", "config", "get", "models"],
        capture_output=True, text=True
    )
    
    # Find xiaomi-coding section and extract apiKey
    config_text = result.stdout
    # Look for the xiaomi-coding block
    import re
    match = re.search(r'"xiaomi-coding":\s*\{[^}]*"baseUrl":\s*"([^"]+)"[^}]*"apiKey":\s*"([^"]+)"', config_text, re.DOTALL)
    if match:
        base_url = match.group(1)
        api_key = match.group(2)
        print(f"Xiaomi Mimo endpoint: {base_url}")
        print(f"Key prefix: {api_key[:15]}...")
        
        llm = LLMService(base_url=base_url, api_key=api_key)
        for model in ["mimo-v2.5-pro", "mimo-v2.5"]:
            s = await check_model_health(llm, model, timeout=20)
            status = "OK" if s.available else "FAIL"
            err = s.error[:80] if s.error else ""
            print(f"  {model}: {status} {s.latency_ms:.0f}ms {err}")
    else:
        print("Could not find xiaomi-coding config")

asyncio.run(test())
