import os, json, sqlite3, hashlib, numpy as np, threading, requests

class Retriever:
    def __init__(self, db_path="knowledge.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.lock = threading.Lock()
        self.cache = {}
        self._init_table()
        self.embedding_mode = self._detect_mode()

    def _init_table(self):
        with self.lock:
            self.conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY,
                source TEXT,
                text TEXT,
                embedding BLOB
            )
            """)
            self.conn.commit()

    def _detect_mode(self):
        from openai import OpenAI
        key = os.getenv("OPENAI_API_KEY", "")
        if key:
            try:
                OpenAI(api_key=key).models.list()
                print("GPT embedding 可用")
                return "gpt"
            except Exception as e:
                print(f"GPT embedding 無法使用 ({e}) → 嘗試 Ollama 模式")
        try:
            if requests.get("http://localhost:11434/api/tags", timeout=2).ok:
                print("Ollama 可用")
                return "ollama"
        except Exception:
            pass
        print("使用 Local hash-based embedding")
        return "local"

    def _embed(self, text):
        if not text:
            return np.zeros(384)
        if self.embedding_mode == "gpt":
            try:
                from openai import OpenAI
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                r = client.embeddings.create(model="text-embedding-3-small", input=text)
                return np.array(r.data[0].embedding)
            except Exception:
                self.embedding_mode = "local"
        if self.embedding_mode == "ollama":
            try:
                r = requests.post("http://localhost:11434/api/embeddings",
                                  json={"model": "mxbai-embed-large", "prompt": text},
                                  timeout=10)
                return np.array(r.json().get("embedding", []))
            except Exception:
                self.embedding_mode = "local"
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return np.frombuffer(digest[:384], dtype=np.uint8) / 255.0

    def add_entry(self, src, text):
        v = self._embed(text)
        vb = v.astype(np.float32).tobytes()
        with self.lock:
            self.conn.execute("INSERT INTO knowledge (source,text,embedding) VALUES (?,?,?)",
                              (src, text, vb))
            self.conn.commit()

    def search(self, query, topk=4):
        if not query: return []
        qv = self._embed(query)
        qkey = hashlib.md5(query.encode()).hexdigest()
        if qkey in self.cache: return self.cache[qkey]
        with self.lock:
            rows = self.conn.execute("SELECT id,source,text,embedding FROM knowledge").fetchall()
        scored=[]
        for rid,src,txt,emb in rows:
            try:
                dv=np.frombuffer(emb,dtype=np.float32)
                s=self._cosine(qv,dv)
                scored.append((s,{"id":rid,"source":src,"text":txt}))
            except Exception: continue
        scored.sort(key=lambda x:x[0],reverse=True)
        res=[x[1] for x in scored[:topk]]
        self.cache[qkey]=res
        return res

    def _cosine(self,v1,v2):
        if v1 is None or v2 is None: return 0.0
        v1,v2=np.array(v1),np.array(v2)
        if v1.size==0 or v2.size==0 or v1.shape!=v2.shape: return 0.0
        denom=np.linalg.norm(v1)*np.linalg.norm(v2)
        if denom==0: return 0.0
        return float(np.dot(v1,v2)/denom)
