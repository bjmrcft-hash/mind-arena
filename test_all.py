import asyncio, sys, io
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import os
from engine.llm.llm_service import LLMService
from engine.model_health import check_model_health

async def test():
    # Test nvidia with longer timeout
    print("=== NVIDIA (30s timeout) ===")
    llm = LLMService(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=os.environ.get("NVIDIA_API_KEY", "")
    )
    for model in ["deepseek-ai/deepseek-v4-flash", "moonshotai/kimi-k2.6"]:
        s = await check_model_health(llm, model, timeout=30)
        status = "OK" if s.available else "FAIL"
        err = s.error[:60] if s.error else ""
        print(f"  {model}: {status} {s.latency_ms:.0f}ms {err}")
    
    # Test dashscope qwen-turbo
    print("=== DashScope ===")
    llm = LLMService(
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key=os.environ.get("LLM_API_KEY", "")
    )
    for model in ["qwen-turbo", "qwen-plus"]:
        s = await check_model_health(llm, model, timeout=15)
        status = "OK" if s.available else "FAIL"
        err = s.error[:60] if s.error else ""
        print(f"  {model}: {status} {s.latency_ms:.0f}ms {err}")

asyncio.run(test())
