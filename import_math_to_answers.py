#!/usr/bin/env python3
# ==========================================================
# 📚 將 math_bank 題庫 JSON 匯入 answers.db
# ==========================================================

import os, json, sqlite3

MATH_FILE = "math_bank/grade5_math_generated.json"
ANS_DB = "answers.db"

def init_db():
    conn = sqlite3.connect(ANS_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS answers (
            id TEXT PRIMARY KEY,
            question TEXT,
            answer TEXT
        )
    """)
    conn.commit()
    return conn

def import_json_to_db(conn):
    if not os.path.exists(MATH_FILE):
        print(f"❌ 找不到題庫檔案: {MATH_FILE}")
        return

    with open(MATH_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items", [])
    if not items:
        print("⚠️ 題庫為空，未匯入任何資料")
        return

    cur = conn.cursor()
    count = 0
    for item in items:
        output = item.get("output", "")
        if not output.strip():
            continue

        # 分割題目與解答
        q = a = ""
        lines = output.splitlines()
        for line in lines:
            if line.startswith("題目"):
                q = line.replace("題目：", "").strip()
            elif line.startswith("解答"):
                a = "\n".join(lines[lines.index(line)+1:]).strip()
                break

        if not q or not a:
            continue

        try:
            cur.execute("INSERT OR REPLACE INTO answers (id, question, answer) VALUES (?, ?, ?)",
                        (hash(q), q, a))
            count += 1
        except Exception:
            continue

    conn.commit()
    print(f"✅ 已匯入 {count} 筆題目到 answers.db")

def show_summary(conn):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*), MIN(rowid), MAX(rowid) FROM answers")
    total, min_id, max_id = cur.fetchone()
    print(f"📊 總筆數：{total}, Row ID 範圍：{min_id} ~ {max_id}")

def main():
    os.makedirs("math_bank", exist_ok=True)
    conn = init_db()
    import_json_to_db(conn)
    show_summary(conn)
    conn.close()

if __name__ == "__main__":
    main()
