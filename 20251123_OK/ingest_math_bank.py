# ============================================
# ingest_math_bank.py
# 數學題庫自動載入器（支援 JSON / TXT / PDF）
# 整合 RAG 資料庫 knowledge.db
# ============================================

import os, json, glob
from rag_backend import Retriever

# --------------------------------------------
# 初始化 RAG Retriever
# --------------------------------------------
retriever = Retriever()
MATH_BANK_DIR = "math_bank"

def ingest_json_file(path):
    """載入 JSON 題庫"""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    count = 0
    for item in data:
        q = item.get("question")
        a = item.get("answer", "")
        if not q:
            continue
        retriever.add_entry(os.path.basename(path), f"{q}\n解答提示：{a}")
        count += 1
    print(f"✅ {os.path.basename(path)} → 匯入 {count} 題")


def ingest_txt_file(path):
    """載入 TXT 題庫，每行一題"""
    with open(path, "r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f.readlines() if ln.strip()]
    for ln in lines:
        retriever.add_entry(os.path.basename(path), ln)
    print(f"✅ {os.path.basename(path)} → 匯入 {len(lines)} 行")


def ingest_pdf_file(path):
    """可選：載入 PDF 題庫（需 PyPDF2）"""
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(path)
        text = "\n".join([p.extract_text() or "" for p in reader.pages])
        retriever.add_entry(os.path.basename(path), text)
        print(f"✅ {os.path.basename(path)} → 匯入 PDF 文字 {len(text)} 字元")
    except Exception as e:
        print(f"⚠️ PDF 匯入失敗：{path} ({e})")


def main():
    if not os.path.exists(MATH_BANK_DIR):
        print(f"⚠️ 找不到題庫資料夾 {MATH_BANK_DIR}/")
        return

    files = glob.glob(f"{MATH_BANK_DIR}/*")
    if not files:
        print("⚠️ 題庫資料夾內沒有檔案")
        return

    for f in files:
        if f.endswith(".json"):
            ingest_json_file(f)
        elif f.endswith(".txt"):
            ingest_txt_file(f)
        elif f.endswith(".pdf"):
            ingest_pdf_file(f)
        else:
            print(f"⚠️ 未支援檔案格式：{f}")

    print("📘 題庫匯入完成 ✅")


if __name__ == "__main__":
    main()
