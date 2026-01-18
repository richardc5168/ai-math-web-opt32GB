import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os
project_root = Path(__file__).resolve().parents[1]
os.environ['DB_PATH'] = str(project_root / 'app.db')
from fastapi.testclient import TestClient
import server

client = TestClient(server.app)
API_KEY = 'j7sqS2ijtI8kZ8vogO_1Z3B0s74NsHF5'
headers = {'X-API-Key': API_KEY}

print('CALLING /v1/questions/next')
r = client.post('/v1/questions/next', params={'student_id': 2}, headers=headers)
print(r.status_code)
print(r.json())

qid = r.json().get('question_id')
print('\nSUBMITTING answer "-4"')
body = {'student_id': 2, 'question_id': qid, 'user_answer': '-4', 'time_spent_sec': 12}
r2 = client.post('/v1/answers/submit', json=body, headers=headers)
print(r2.status_code)
try:
    print(r2.json())
except Exception:
    print(r2.text)
