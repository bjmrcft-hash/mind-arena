import asyncio, sys, io
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import os
from engine.llm.llm_service import LLMService
from engine.model_health import check_model_health

async def test():
    # Test modelscope
    llm = LLMService(
        base_url="https://api-inference.modelscope.cn/v1",
        api_key=os.environ.get("MODELSCOPE_API_KEY", "")
    )
    
    models = [
        "MiniMax/MiniMax-M1-80k",
        "iic/Qwen2.5-72B-Instruct",
        "iic/Qwen3-32B",
        "deepseek-ai/DeepSeek-V3-0324",
        "Qwen/Qwen2.5-72B-Instruct",
        "iic/DeepSeek-R1",
    ]
    
    print("=== ModelScope ===")
    for model in models:
        s = await check_model_health(llm, model, timeout=15)
        status = "OK" if s.available else "FAIL"
        err = s.error[:60] if s.error else ""
        print(f"  {model}: {status} {s.latency_ms:.0f}ms {err}")

asyncio.run(test())
