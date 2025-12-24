#!/usr/bin/env python3
# ==========================================================
# 🧮 AI 自動出題腳本 - 離線 DeepSeek / Llama 模式
# 產生數學題庫並儲存到 math_bank/grade5_math_generated.json
# ==========================================================

import os, json, random, time, requests
from datetime import datetime

# === 設定 ===
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OUT_FILE = "math_bank/grade5_math_generated.json"
MODEL_MATH = "deepseek-math:7b"
MODEL_FALLBACK = "llama3.1:8b-instruct-q5_K_M"

# === 題型範例 ===
TOPICS = {
    "分數運算": [
        "3/4 加上 2/5 等於多少？",
        "求 5/6 減去 1/3 的結果。",
        "把 7/8 乘以 2/7。"
    ],
    "小數與四則運算": [
        "0.25 乘以 8 等於多少？",
        "3.6 除以 0.2 的結果是多少？",
        "2.5 加上 7.35 減去 1.2 等於？"
    ],
    "幾何與面積": [
        "一個長方形長 8 公分、寬 5 公分，面積是多少？",
        "半徑 7 公分的圓面積是多少？（取 π=3.14）",
        "一個三角形底 10 公分，高 6 公分，面積是多少？"
    ],
    "應用題": [
        "一個水桶能裝 12 公升水，現在裝了 3/4，裝了多少公升？",
        "火車每小時行駛 80 公里，3.5 小時共行多少公里？",
        "蛋糕平均分給 8 人，每人分到 1/8，請問蛋糕原本是多少？"
    ]
}

# === 檢查 Ollama 模型 ===
def get_available_models():
    try:
        resp = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        models = [m["name"] for m in resp.json().get("models", [])]
        print("✅ 可用模型：", models)
        return models
    except Exception as e:
        print("⚠️ 無法連線到 Ollama：", e)
        return []

def pick_model():
    models = get_available_models()
    if any("deepseek-math" in m for m in models):
        print("🧠 使用 DeepSeek-Math 離線模型")
        return MODEL_MATH
    elif any("llama3" in m for m in models):
        print("💡 使用 Llama3.1 離線模型")
        return MODEL_FALLBACK
    else:
        print("❌ 未偵測到可用模型，請執行：ollama pull deepseek-math:7b 或 llama3.1:8b-instruct-q5_K_M")
        exit(1)

# === 呼叫模型生成 ===
def generate(model, prompt):
    try:
        r = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": model, "prompt": prompt},
            timeout=120,
            stream=True
        )
        answer = ""
        for line in r.iter_lines():
            if not line:
                continue
            try:
                obj = json.loads(line)
                if "response" in obj:
                    answer += obj["response"]
            except:
                continue
        return answer.strip()
    except Exception as e:
        return f"[模型錯誤] {e}"

# === 出題流程 ===
def main():
    os.makedirs("math_bank", exist_ok=True)
    model = pick_model()
    all_results = []

    print("\n🎯 開始生成五年級數學題庫...\n")

    for topic, examples in TOPICS.items():
        for i in range(3):  # 每類別出 3 題
            seed = random.choice(examples)
            prompt = f"""你是一位小學數學老師。
請根據以下範例題型，設計一個類似但不同的題目（五年級程度），並附上詳細解答步驟。

範例題目：{seed}

回答格式：
題目：
解答：
"""
            print(f"📘 {topic} - 生成題目中...")
            res = generate(model, prompt)
            all_results.append({"topic": topic, "example": seed, "output": res})
            time.sleep(1)

    # === 儲存輸出 ===
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "created": datetime.now().isoformat(),
            "model": model,
            "count": len(all_results),
            "items": all_results
        }, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 已完成，共 {len(all_results)} 題")
    print(f"📂 輸出檔案：{OUT_FILE}")

if __name__ == "__main__":
    main()
