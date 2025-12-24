import sqlite3, argparse, json

DB="answers.db"

def init_db():
    conn=sqlite3.connect(DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS answers(
        id TEXT PRIMARY KEY,
        question TEXT,
        answer TEXT
    )""")
    conn.commit()
    return conn

def stats():
    conn=sqlite3.connect(DB)
    c=conn.cursor()
    c.execute("SELECT COUNT(*) FROM answers")
    n=c.fetchone()[0]
    print(f"📊 answers.db：共 {n} 題")
    conn.close()

def clear():
    conn=sqlite3.connect(DB)
    conn.execute("DELETE FROM answers")
    conn.commit(); conn.close()
    print("✅ 已清空 answers.db")

def get(qid):
    conn=sqlite3.connect(DB)
    c=conn.cursor()
    c.execute("SELECT question,answer FROM answers WHERE id=?",(qid,))
    r=c.fetchone()
    print(json.dumps({"question":r[0],"answer":r[1]},ensure_ascii=False,indent=2) if r else "❌ 查無資料")
    conn.close()

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--stats",action="store_true")
    p.add_argument("--clear",action="store_true")
    p.add_argument("--get")
    a=p.parse_args()
    if a.stats: stats()
    elif a.clear: clear()
    elif a.get: get(a.get)
    else: print("用法：--stats | --clear | --get <id>")
