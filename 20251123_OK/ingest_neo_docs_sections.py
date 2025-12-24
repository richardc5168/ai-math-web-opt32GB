# ===========================================
# ingest_neo_docs_sections.py
# Neo 文件分段導入知識庫（自動偵測 embedding 模式）
# ===========================================

import os
import re
import time
import glob
import tqdm
from rag_backend import Retriever

try:
    from PyPDF2 import PdfReader
except ImportError:
    os.system("pip install PyPDF2")
    from PyPDF2 import PdfReader

# === 分段工具 ===
def chunk_text(text, max_len=800):
    """簡易文字分段"""
    sentences = re.split(r'(?<=[。！？\.\!\?])\s+', text)
    chunks, buf = [], ""
    for s in sentences:
        if len(buf) + len(s) > max_len:
            chunks.append(buf.strip())
            buf = s
        else:
            buf += " " + s
    if buf:
        chunks.append(buf.strip())
    return chunks

# === 文件解析 ===
def read_file(path):
    """支援 PDF / TXT / MD 文字讀取"""
    ext = os.path.splitext(path)[1].lower()
    text = ""
    if ext == ".pdf":
        try:
            reader = PdfReader(path)
            for page in reader.pages:
                text += page.extract_text() or ""
        except Exception as e:
            print(f"⚠ 解析 PDF 失敗: {path} ({e})")
    elif ext in [".txt", ".md"]:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    else:
        print(f"⚠ 不支援的文件格式: {path}")
    return text.strip()

# === 主流程 ===
def main():
    docs_dir = "neo_docs"
    db_path = "knowledge.db"

    if not os.path.exists(docs_dir):
        print(f"❌ 找不到資料夾: {docs_dir}")
        return

    retriever = Retriever(db_path)
    print(f"✅ 初始化成功，使用 embedding 模式: {retriever.embedding_mode}")

    # 掃描文件
    files = sorted(glob.glob(os.path.join(docs_dir, "*.*")))
    if not files:
        print("⚠ 資料夾中沒有任何文件")
        return

    for path in files:
        print(f"\n📘 處理文件: {os.path.basename(path)}")
        text = read_file(path)
        if not text:
            print("⚠ 文件內容為空，略過")
            continue

        chunks = chunk_text(text)
        print(f"✂️ 分段完成，共 {len(chunks)} 段")
        time.sleep(0.3)

        # 逐段寫入資料庫
        for i, ck in enumerate(tqdm.tqdm(chunks, desc="🚀 導入中")):
            try:
                retriever.ingest(source=os.path.basename(path), text=ck)
            except Exception as e:
                print(f"⚠ 段落 {i} 導入失敗: {e}")

        print(f"[OK] {os.path.basename(path)} → {len(chunks)} chunks")

    print("\n✅ 所有文件導入完成")
    print(f"📚 資料庫路徑：{db_path}")

if __name__ == "__main__":
    main()
