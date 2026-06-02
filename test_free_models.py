import asyncio, os, sys, io
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from engine.llm.llm_service import LLMService
from engine.model_health import check_model_health

async def test():
    # Check if env vars are set
    nvidia_key = os.environ.get("NVIDIA_API_KEY", "")
    ms_key = os.environ.get("MODELSCOPE_API_KEY", "")
    print("NVIDIA_API_KEY set:", bool(nvidia_key))
    print("MODELSCOPE_API_KEY set:", bool(ms_key))
    
    if nvidia_key:
        llm = LLMService(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=nvidia_key
        )
        for model in ["deepseek-ai/deepseek-v4-flash", "moonshotai/kimi-k2.6"]:
            s = await check_model_health(llm, model, timeout=20)
            status = "OK" if s.available else "FAIL"
            err = s.error[:80] if s.error else ""
            print(f"nvidia/{model}: {status} {s.latency_ms:.0f}ms {err}")
    
    if ms_key:
        llm = LLMService(
            base_url="https://api-inference.modelscope.cn/v1",
            api_key=ms_key
        )
        for model in ["Kimi-K2.5", "DeepSeek-V3.2", "GLM-5"]:
            s = await check_model_health(llm, model, timeout=20)
            status = "OK" if s.available else "FAIL"
            err = s.error[:80] if s.error else ""
            print(f"modelscope/{model}: {status} {s.latency_ms:.0f}ms {err}")

asyncio.run(test())
