import os, json, time, requests, sqlite3, hashlib, glob
from pathlib import Path

OLLAMA_HOST=os.getenv("OLLAMA_HOST","http://localhost:11434")
MODEL=os.getenv("OLLAMA_MODEL","deepseek-math:7b")
BANK="math_bank"; DB="answers.db"
Path(BANK).mkdir(exist_ok=True)

def load_context():
    ctx=[]
    for f in glob.glob(f"{BANK}/*"):
        if f.endswith(".json"):
            try:
                for q in json.load(open(f,encoding="utf-8")):
                    ctx.append(q.get("question",""))
            except: pass
        elif f.endswith(".txt"):
            ctx+=open(f,encoding="utf-8").read().splitlines()
    return "\n".join(ctx[:200])

def ollama_gen(p):
    try:
        r=requests.post(f"{OLLAMA_HOST}/api/generate",
            json={"model":MODEL,"prompt":p},timeout=180)
        return r.text
    except Exception as e:
        print("Ollama錯誤",e); return ""

def save_answer(qid,q,a):
    conn=sqlite3.connect(DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS answers(id TEXT PRIMARY KEY,question TEXT,answer TEXT)""")
    conn.execute("REPLACE INTO answers VALUES(?,?,?)",(qid,q,a))
    conn.commit(); conn.close()

def generate(grade,topic,count=10):
    ctx=load_context()
    print(f"📚 載入題庫背景 {len(ctx.splitlines())} 行")
    out=f"{BANK}/auto_grade{grade}_{topic}.json"
    allq=[]
    for i in range(count):
        print(f"\n🧮 生成第 {i+1}/{count} 題…")
        p=f"""
依照以下風格出一題台灣國小{grade}年級數學題（主題：{topic}），並給出完整解答。
以JSON輸出：
{{"question":"<題目>","answer":"<解答>"}}

參考題庫：
{ctx}
"""
        resp=ollama_gen(p)
        try:
            qa=json.loads(resp.strip("```json").strip("```"))
        except: qa={"question":resp.strip(),"answer":"(格式錯誤)"}
        qid=hashlib.md5(qa["question"].encode()).hexdigest()
        allq.append(qa); save_answer(qid,qa["question"],qa["answer"])
        json.dump(allq,open(out,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
        print(f"✅ 已保存 {out}")
        time.sleep(1)
    print(f"\n🎯 共 {len(allq)} 題完成")

if __name__=="__main__":
    print("=== 離線出題 RAG 增強版 ===")
    g=int(input("輸入年級(4-6)：") or "5")
    t=input("輸入主題(分數/幾何/應用題/小數)：") or "應用題"
    c=int(input("出題數量：") or "10")
    generate(g,t,c)
