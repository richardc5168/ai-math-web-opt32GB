import subprocess, time, requests, sqlite3, os, signal

UVICORN_CMD = [
    os.path.join('.', '.venv', 'Scripts', 'python.exe'),
    '-m', 'uvicorn', 'server:app', '--port', '8000'
]
DB = 'app.db'

def wait_up(url, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=1)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False

proc = subprocess.Popen(UVICORN_CMD)
print('started uvicorn pid', proc.pid)
try:
    if not wait_up('http://127.0.0.1:8000/health', timeout=15):
        raise SystemExit('server did not start')

    # bootstrap
    r = requests.post('http://127.0.0.1:8000/admin/bootstrap?name=smoke-run')
    print('bootstrap', r.status_code, r.text)
    api_key = r.json().get('api_key')
    account_id = r.json().get('account_id')
    headers = {'X-API-Key': api_key}

    # determine the created student id for this account
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    st = conn.execute('SELECT * FROM students WHERE account_id = ? ORDER BY id DESC LIMIT 1', (account_id,)).fetchone()
    conn.close()
    if not st:
        raise SystemExit('no student found for account')
    student_id = st['id']

    # next
    r = requests.post(f'http://127.0.0.1:8000/v1/questions/next?student_id={student_id}', headers=headers)
    print('next', r.status_code, r.text)
    qid = r.json().get('question_id')

    # read correct answer from DB
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    row = conn.execute('SELECT * FROM question_cache WHERE id=?', (qid,)).fetchone()
    conn.close()
    print('cached', dict(row) if row else None)
    correct = row['correct_answer'] if row else ''

    # submit
    sub = requests.post('http://127.0.0.1:8000/v1/answers/submit', headers=headers, json={'student_id':student_id,'question_id':qid,'user_answer':correct,'time_spent_sec':5})
    print('submit', sub.status_code, sub.text)

    # custom solve
    r2 = requests.post('http://127.0.0.1:8000/v1/custom/solve', headers=headers, json={'question':'1/2 + 1/3'})
    print('custom', r2.status_code, r2.text)

    # report
    rep = requests.get(f'http://127.0.0.1:8000/v1/reports/summary?student_id={student_id}&days=30', headers=headers)
    print('report', rep.status_code, rep.text)

finally:
    try:
        proc.send_signal(signal.SIGINT)
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
    print('server stopped')
