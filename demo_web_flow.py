#!/usr/bin/env python3
import sys
import json
import sqlite3
import secrets
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os
db_path = str(Path(__file__).resolve().parents[1] / 'app.db')
os.environ['DB_PATH'] = db_path

from fastapi.testclient import TestClient
import server

# Create test account directly in DB
def create_test_account():
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    api_key = secrets.token_urlsafe(24)
    cur.execute(
        "INSERT INTO accounts(name, api_key, created_at) VALUES (?,?,?)",
        ('Web-Demo-Account', api_key, datetime.now().isoformat(timespec='seconds'))
    )
    account_id = cur.lastrowid
    cur.execute(
        "INSERT INTO subscriptions(account_id, status, plan, seats, current_period_end, updated_at) VALUES (?,?,?,?,?,?)",
        (account_id, 'active', 'basic', 1,
         (datetime.now() + timedelta(days=30)).isoformat(timespec='seconds'),
         datetime.now().isoformat(timespec='seconds'))
    )
    cur.execute(
        "INSERT INTO students(account_id, display_name, grade, created_at) VALUES (?,?,?,?)",
        (account_id, 'Web-Demo-Student', 'G5', datetime.now().isoformat(timespec='seconds'))
    )
    conn.commit()
    conn.close()
    return api_key, account_id

api_key, account_id = create_test_account()
print(f"[Created test account: account_id={account_id}, api_key={api_key}]\n")

client = TestClient(server.app)
headers = {'X-API-Key': api_key}
student_id = 1  # First student created

print("=" * 80)
print("STEP 1: GET / (載入首頁 HTML)")
print("=" * 80)
r = client.get('/')
print(f"Status: {r.status_code}")
if r.status_code == 200:
    print("✓ HTML page loaded successfully")
    print(f"Content-Type: {r.headers.get('content-type')}")
    print(f"First 300 chars:\n{r.text[:300]}\n")

print("=" * 80)
print("STEP 2: POST /v1/questions/next (取得一題)")
print("=" * 80)
r = client.post('/v1/questions/next', params={'student_id': student_id}, headers=headers)
print(f"Status: {r.status_code}")
resp = r.json()
print(f"Response:\n{json.dumps(resp, ensure_ascii=False, indent=2)}")
qid = resp.get('question_id')
if qid:
    print(f"\n✓ Got question_id={qid}")

print("\n" + "=" * 80)
print("STEP 3: POST /v1/answers/submit (提交答案 '-4')")
print("=" * 80)
body = {'student_id': student_id, 'question_id': qid, 'user_answer': '-4', 'time_spent_sec': 12}
r = client.post('/v1/answers/submit', json=body, headers=headers)
print(f"Status: {r.status_code}")
try:
    resp = r.json()
    print(f"Response:\n{json.dumps(resp, ensure_ascii=False, indent=2)}")
    if r.status_code == 200:
        print(f"\n✓ Answer submitted successfully")
except Exception as e:
    print(f"Error: {e}\nRaw: {r.text}")

print("\n" + "=" * 80)
print("STEP 4: POST /v1/custom/solve (自訂題目：1/2 + 1/3)")
print("=" * 80)
body = {'question': '1/2 + 1/3'}
r = client.post('/v1/custom/solve', json=body, headers=headers)
print(f"Status: {r.status_code}")
try:
    resp = r.json()
    print(f"Response:\n{json.dumps(resp, ensure_ascii=False, indent=2)}")
    if r.status_code == 200:
        print(f"\n✓ Custom solve successful")
except Exception as e:
    print(f"Error: {e}\nRaw: {r.text}")

print("\n" + "=" * 80)
print("STEP 5: GET /v1/reports/summary (查看報表)")
print("=" * 80)
r = client.get('/v1/reports/summary', params={'student_id': student_id}, headers=headers)
print(f"Status: {r.status_code}")
try:
    resp = r.json()
    print(f"Response:\n{json.dumps(resp, ensure_ascii=False, indent=2)}")
except Exception as e:
    print(f"Error: {e}\nRaw: {r.text}")

print("\n" + "=" * 80)
print("✅ 完成示範！")
print("=" * 80)
print(f"\n💡 在瀏覽器操作時，請用 API Key: {api_key}")
print(f"   http://127.0.0.1:8000/")
