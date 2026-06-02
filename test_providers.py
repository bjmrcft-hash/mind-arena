import asyncio, sys, io
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import os
from engine.llm.llm_service import LLMService
from engine.model_health import check_model_health

async def test():
    providers = [
        ("NVIDIA NIM", "https://integrate.api.nvidia.com/v1", os.environ.get("NVIDIA_API_KEY", ""), [
            "deepseek-ai/deepseek-v4-flash",
            "moonshotai/kimi-k2.6",
        ]),
        ("Xiaomi Mimo", "https://token-plan-sgp.xiaomimimo.com/v1", os.environ.get("XIAOMI_CODING_API_KEY", ""), [
            "MiniMax-M2.7",
            "mimo-v2.5-pro",
        ]),
        ("ModelScope", "https://api-inference.modelscope.cn/v1", os.environ.get("MODELSCOPE_API_KEY", ""), [
            "ZhipuAI/GLM-5",
            "Qwen/Qwen3-397B-A17B",
            "MiniMax/MiniMax-M1-80k",
        ]),
    ]
    
    for name, base_url, api_key, models in providers:
        print(f"\n=== {name} ===")
        if not api_key:
            print("  (no API key, skipping)")
            continue
        llm = LLMService(base_url=base_url, api_key=api_key)
        for model in models:
            s = await check_model_health(llm, model, timeout=25)
            status = "OK" if s.available else "FAIL"
            err = s.error[:80] if s.error else ""
            print(f"  {model}: {status} {s.latency_ms:.0f}ms {err}")

asyncio.run(test())
