import os
import sqlite3
from fastapi.testclient import TestClient

# remove DB before importing server so init_db() runs against a clean file
DB = 'app.db'
try:
    if os.path.exists(DB):
        os.remove(DB)
except Exception:
    pass

import importlib
import server
importlib.reload(server)


def test_full_flow():
    client = TestClient(server.app)

    # bootstrap
    r = client.post('/admin/bootstrap?name=pytest-run')
    assert r.status_code == 200
    api_key = r.json().get('api_key')
    assert api_key
    headers = {'X-API-Key': api_key}

    # next question
    r = client.post('/v1/questions/next?student_id=1', headers=headers)
    assert r.status_code == 200
    qid = r.json().get('question_id')
    assert qid is not None

    # read correct answer from DB
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    row = conn.execute('SELECT * FROM question_cache WHERE id=?', (qid,)).fetchone()
    conn.close()
    assert row is not None
    correct = row['correct_answer']

    # submit answer
    sub = client.post('/v1/answers/submit', headers=headers, json={'student_id': 1, 'question_id': qid, 'user_answer': correct, 'time_spent_sec': 2})
    assert sub.status_code == 200
    assert sub.json().get('is_correct') in (0, 1, None)

    # custom solve
    r2 = client.post('/v1/custom/solve', headers=headers, json={'question': '1/2 + 1/3'})
    assert r2.status_code == 200
    assert 'final_answer' in r2.json()

    # report
    rep = client.get('/v1/reports/summary?student_id=1&days=30', headers=headers)
    assert rep.status_code == 200
    body = rep.json()
    assert 'summary' in body and body['summary'].get('valid_total', 0) >= 1
