#!/usr/bin/env python3
# ======================================================
# 🧠 DeepSeek / Ollama 模型環境檢查工具
# 版本: 2025.11
# ======================================================

import requests, json, sys, os, time

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
TEST_PROMPT = "請用一句話解釋：為什麼 12 ÷ 0.5 等於 24？"

def check_server():
    print("🔍 檢查 Ollama 服務中...")
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=3)
        if r.ok:
            tags = [m["name"] for m in r.json().get("models", [])]
            print(f"✅ 連線成功 → 可用模型: {tags}")
            return tags
        else:
            print(f"❌ Ollama 回應錯誤 ({r.status_code})")
            return []
    except Exception as e:
        print(f"❌ 無法連線到 Ollama: {e}")
        return []

def test_inference(model: str):
    print(f"\n🧪 測試模型推理: {model}")
    try:
        payload = {"model": model, "prompt": TEST_PROMPT}
        r = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload, stream=True, timeout=60)
        if not r.ok:
            print(f"⚠️  推理失敗 ({r.status_code})")
            return
        print("📤 模型回應:")
        for line in r.iter_lines():
            if line:
                try:
                    obj = json.loads(line)
                    if "response" in obj:
                        sys.stdout.write(obj["response"])
                        sys.stdout.flush()
                except:
                    continue
        print("\n✅ 測試完成")
    except Exception as e:
        print(f"❌ 模型推理錯誤: {e}")

def main():
    tags = check_server()
    if not tags:
        print("\n🚫 未檢測到 Ollama 服務，請先執行:  ollama serve &")
        return

    # 偵測是否存在 math 模型
    if any("deepseek-math" in t for t in tags):
        model = next(t for t in tags if "deepseek-math" in t)
    elif any("llama3" in t for t in tags):
        model = next(t for t in tags if "llama3" in t)
    else:
        print("\n⚠️ 未找到 deepseek-math 或 llama3 模型，請先執行:")
        print("   ollama pull deepseek-math:7b")
        print("   或 ollama pull llama3.1:8b-instruct-q5_K_M")
        return

    test_inference(model)

if __name__ == "__main__":
    main()
