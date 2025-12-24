
"""
ingest_neo_docs.py
将你的 Neo 相關文件（PDF、TXT、MD）批量寫入 knowledge.db，供 RAG 使用。
使用方式：
  1) 將檔案放到 ./neo_docs/ 目錄（可含子資料夾）
  2) python ingest_neo_docs.py
  3) 啟動 Streamlit 前端後，用「知識庫問答」測試

可離線運作。若安裝了 sentence-transformers 與 faiss，RAG 會自動使用語意檢索；
否則回退為關鍵字檢索。
"""
import os, re, sqlite3
from pathlib import Path

# 輕量 PDF/文本抽取
def load_text(path: Path) -> str:
    text = ""
    if path.suffix.lower() in [".txt", ".md", ".rst"]:
        text = path.read_text(encoding="utf-8", errors="ignore")
    elif path.suffix.lower() in [".pdf"]:
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            text = "\n".join([p.extract_text() or "" for p in reader.pages])
        except Exception as e:
            print(f"[WARN] PDF 解析失敗 {path.name}: {e}")
            text = ""
    else:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            text = ""
    return text

def normalize_whitespace(s: str) -> str:
    s = re.sub(r'\s+', ' ', s)
    return s.strip()

def chunk_text(text: str, size=1200, overlap=160):
    out = []
    i = 0
    n = len(text)
    while i < n:
        out.append(text[i:i+size])
        i += size - overlap
    return out

def main():
    from rag_backend import Retriever
    retriever = Retriever(db_path="knowledge.db")

    root = Path("neo_docs")
    root.mkdir(exist_ok=True)
    paths = [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in [".pdf",".txt",".md",".rst"]]

    if not paths:
        print("請將 Neo 文件放到 ./neo_docs/ 後再執行。本程式將自動寫入 knowledge.db")
        return

    total_chunks = 0
    for p in paths:
        text = load_text(p)
        if not text:
            continue
        text = normalize_whitespace(text)
        # 嘗試從檔名推斷版本與章節（若檔名中含 v1.3 / ch3 等字樣，會放入 source 字串）
        fname = p.name
        source = f"NEO|{fname}"
        # 分塊寫入
        for i, ck in enumerate(chunk_text(text)):
            retriever.ingest(source=f"{source}#part{i+1}", text=ck)
            total_chunks += 1
        print(f"[OK] {fname} -> {i+1} chunks")

    print(f"完成。已寫入 knowledge.db，共 {total_chunks} 個片段。")

if __name__ == "__main__":
    main()
