import asyncio, sys, io
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path, override=True)

from engine.llm.llm_service import LLMService
from engine.model_health import check_model_health

async def test():
    # Test dashscope with loaded key
    print("=== DashScope (key from .env) ===")
    llm = LLMService()
    for model in ["qwen-turbo", "qwen-plus", "qwen3.5-plus-2026-04-20"]:
        s = await check_model_health(llm, model, timeout=15)
        status = "OK" if s.available else "FAIL"
        err = s.error[:80] if s.error else ""
        print(f"  {model}: {status} {s.latency_ms:.0f}ms {err}")
    
    # Test modelscope
    print("=== ModelScope ===")
    llm_ms = LLMService(
        base_url="https://api-inference.modelscope.cn/v1",
        api_key=os.environ.get("MODELSCOPE_API_KEY", "")
    )
    for model in ["MiniMax/MiniMax-M1-80k"]:
        s = await check_model_health(llm_ms, model, timeout=15)
        status = "OK" if s.available else "FAIL"
        err = s.error[:80] if s.error else ""
        print(f"  {model}: {status} {s.latency_ms:.0f}ms {err}")

asyncio.run(test())
