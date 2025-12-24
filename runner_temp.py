import os, sqlite3
DB='app.db'
try:
    os.remove(DB)
    print('removed',DB)
except Exception as e:
    print('no existing db to remove',e)
from fastapi.testclient import TestClient
import importlib
import server
importlib.reload(server)
client=TestClient(server.app)
# bootstrap
r=client.post('/admin/bootstrap?name=RunnerRun')
print('bootstrap', r.status_code, r.json())
api_key=r.json()['api_key']; headers={'X-API-Key':api_key}
# next question
r=client.post('/v1/questions/next?student_id=1', headers=headers)
print('next', r.status_code, r.text)
qid=r.json().get('question_id')
# inspect db
conn=sqlite3.connect(DB); conn.row_factory=sqlite3.Row
row=conn.execute('SELECT * FROM question_cache WHERE id=?',(qid,)).fetchone()
print('cached', dict(row) if row else None)
correct = row['correct_answer'] if row else None
# submit
sub=client.post('/v1/answers/submit', headers=headers, json={'student_id':1,'question_id':qid,'user_answer':correct,'time_spent_sec':5})
print('submit', sub.status_code, sub.json())
# custom solve
r2=client.post('/v1/custom/solve', headers=headers, json={'question':'1/2 + 1/3'})
print('custom', r2.status_code, r2.json())
# report
rep=client.get('/v1/reports/summary?student_id=1&days=30', headers=headers)
print('report', rep.status_code, rep.json())
