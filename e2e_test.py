"""MindArena 全流程端到端测试."""
import httpx
import json
import time
import sys
import io

# Force UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BASE = "http://localhost:8000"
TOPIC = "远程办公是否应该成为常态"

def test_health():
    r = httpx.get(f"{BASE}/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    print(f"✅ Health: {data}")

def test_root():
    r = httpx.get(f"{BASE}/")
    assert r.status_code == 200
    data = r.json()
    assert data["service"] == "MindArena"
    print(f"✅ Root: {data}")

def test_list_debates_empty():
    r = httpx.get(f"{BASE}/api/debates")
    assert r.status_code == 200
    data = r.json()
    print(f"✅ List debates: {data['count']} debates")

def test_create_debate():
    r = httpx.post(f"{BASE}/api/debates", json={
        "topic": TOPIC,
        "mode": "quick",
        "tts_enabled": False,
    }, timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    assert data["topic"] == TOPIC, f"Topic mismatch: {data['topic']}"
    assert data["status"] == "running"
    print(f"✅ Created debate: {data['id']}")
    print(f"   Topic: {data['topic']}")
    print(f"   Models config: {data['config']['models']}")
    return data["id"]

def test_get_debate(sid):
    r = httpx.get(f"{BASE}/api/debates/{sid}", timeout=10)
    assert r.status_code == 200
    data = r.json()
    print(f"✅ Get debate: status={data['session']['status']}, msgs={len(data['messages'])}")
    return data

def test_get_messages(sid):
    r = httpx.get(f"{BASE}/api/debates/{sid}/messages", timeout=10)
    assert r.status_code == 200
    data = r.json()
    print(f"✅ Messages: {data['count']} messages")
    return data

def test_export_json(sid):
    r = httpx.get(f"{BASE}/api/debates/{sid}/export?format=json", timeout=10)
    assert r.status_code == 200
    print(f"✅ Export JSON: OK")

def test_export_markdown(sid):
    r = httpx.get(f"{BASE}/api/debates/{sid}/export?format=markdown", timeout=10)
    assert r.status_code == 200
    assert "text/markdown" in r.headers.get("content-type", "")
    print(f"✅ Export Markdown: {len(r.text)} chars")

def test_models_endpoint():
    r = httpx.get(f"{BASE}/api/config/models", timeout=10)
    assert r.status_code == 200
    data = r.json()
    print(f"✅ Models: {list(data.get('default_models', {}).keys())}")

def test_404():
    r = httpx.get(f"{BASE}/api/debates/nonexistent-id", timeout=10)
    assert r.status_code == 404
    print(f"✅ 404: Correct")

def main():
    print("=" * 60)
    print("MindArena 全流程端到端测试")
    print("=" * 60)
    
    # Phase 1: 基础端点
    print("\n--- Phase 1: 基础端点 ---")
    test_health()
    test_root()
    test_404()
    test_models_endpoint()
    
    # Phase 2: 辩论生命周期
    print("\n--- Phase 2: 辩论生命周期 ---")
    test_list_debates_empty()
    sid = test_create_debate()
    
    # Phase 3: 等待辩论完成 (quick模式 ~2min)
    print("\n--- Phase 3: 等待辩论完成 ---")
    max_wait = 300  # 5 min
    start = time.time()
    final_status = None
    while time.time() - start < max_wait:
        data = test_get_debate(sid)
        status = data["session"]["status"]
        msgs = len(data["messages"])
        elapsed = time.time() - start
        print(f"   [{elapsed:.0f}s] status={status}, msgs={msgs}")
        if status in ("completed", "stopped", "error"):
            final_status = status
            break
        time.sleep(10)
    
    if not final_status:
        print(f"❌ Timeout after {max_wait}s, status={status}")
        return 1
    
    # Phase 4: 完成后验证
    print(f"\n--- Phase 4: 完成后验证 (status={final_status}) ---")
    if final_status == "completed":
        data = test_get_debate(sid)
        msgs = data["messages"]
        print(f"   Total messages: {len(msgs)}")
        for m in msgs:
            role = m["role"]
            mtype = m["message_type"]
            content_preview = m["content"][:60].replace("\n", " ")
            print(f"   [{role}] {mtype}: {content_preview}...")
        
        test_get_messages(sid)
        test_export_json(sid)
        test_export_markdown(sid)
        test_list_debates_empty()
        
        print("\n" + "=" * 60)
        print("✅ 全流程测试通过!")
        print("=" * 60)
        return 0
    else:
        print(f"❌ 辩论未成功完成: {final_status}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
