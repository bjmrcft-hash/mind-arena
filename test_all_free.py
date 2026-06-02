import asyncio, sys, io, json
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import os
from engine.llm.llm_service import LLMService
from engine.model_health import check_model_health

async def test():
    # Read key from auth profiles
    auth_path = os.path.expanduser("~/.openclaw/agents/main/agent/auth-profiles.json")
    with open(auth_path) as f:
        auth = json.load(f)
    
    xiaomi_key = auth["profiles"]["xiaomi:default"]["key"]
    nvidia_key = auth["profiles"]["nvidia:default"]["key"]
    ms_key = auth["profiles"].get("qwen:default", {}).get("key", "")
    
    print("=== Xiaomi Mimo (token-plan-cn) ===")
    llm = LLMService(base_url="https://token-plan-cn.xiaomimimo.com/v1", api_key=xiaomi_key)
    for model in ["mimo-v2.5-pro", "mimo-v2.5"]:
        s = await check_model_health(llm, model, timeout=20)
        status = "OK" if s.available else "FAIL"
        err = s.error[:80] if s.error else ""
        print(f"  {model}: {status} {s.latency_ms:.0f}ms {err}")
    
    print("\n=== NVIDIA NIM ===")
    llm = LLMService(base_url="https://integrate.api.nvidia.com/v1", api_key=nvidia_key)
    for model in ["deepseek-ai/deepseek-v4-flash", "deepseek-ai/deepseek-v4-pro"]:
        s = await check_model_health(llm, model, timeout=30)
        status = "OK" if s.available else "FAIL"
        err = s.error[:80] if s.error else ""
        print(f"  {model}: {status} {s.latency_ms:.0f}ms {err}")
    
    print("\n=== ModelScope ===")
    ms_key2 = os.environ.get("MODELSCOPE_API_KEY", "")
    llm = LLMService(base_url="https://api-inference.modelscope.cn/v1", api_key=ms_key2)
    for model in ["ZhipuAI/GLM-5", "MiniMax/MiniMax-M1-80k"]:
        s = await check_model_health(llm, model, timeout=20)
        status = "OK" if s.available else "FAIL"
        err = s.error[:80] if s.error else ""
        print(f"  {model}: {status} {s.latency_ms:.0f}ms {err}")

asyncio.run(test())
