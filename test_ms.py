import asyncio, sys, io
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import os
from engine.llm.llm_service import LLMService
from engine.model_health import check_model_health

async def test():
    # Test modelscope with various model name formats
    llm = LLMService(
        base_url="https://api-inference.modelscope.cn/v1",
        api_key=os.environ.get("MODELSCOPE_API_KEY", "")
    )
    
    models_to_try = [
        "Qwen/Qwen2.5-7B-Instruct",
        "Qwen/Qwen3-8B",
        "deepseek-ai/DeepSeek-V3",
        "deepseek-ai/DeepSeek-R1",
        "ZhipuAI/GLM-4-9B-Chat",
        "moonshotai/Moonlight-16B-A3B-Instruct",
        "MiniMax/MiniMax-M1-80k",
    ]
    
    for model in models_to_try:
        s = await check_model_health(llm, model, timeout=15)
        status = "OK" if s.available else "FAIL"
        err = s.error[:60] if s.error else ""
        print(f"  {model}: {status} {s.latency_ms:.0f}ms {err}")

asyncio.run(test())
