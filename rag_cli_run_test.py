import json
from pathlib import Path
import requests
cfg = json.loads(Path('.rag_cli_config.json').read_text())
base = cfg['base_url'].rstrip('/')
key = cfg['api_key']
sid = cfg['student_id']
headers={'X-API-Key':key}
print('Using', base, 'student_id=', sid)
# Next question
r = requests.post(base+'/v1/questions/next', params={'student_id':sid}, headers=headers, timeout=10)
print('next status', r.status_code)
print(r.text[:800])
if r.status_code==200:
    q = r.json()
    qid = q.get('question_id')
    print('question_id=', qid)
    # submit an answer placeholder
    body={'student_id':sid,'question_id':qid,'user_answer':'42','time_spent_sec':15}
    s = requests.post(base+'/v1/answers/submit', json=body, headers=headers, timeout=10)
    print('submit status', s.status_code)
    print(s.text[:800])
else:
    print('Failed to get question')
# summary
t = requests.get(base+'/v1/reports/summary', params={'student_id':sid}, headers=headers, timeout=10)
print('summary', t.status_code)
print(t.text[:1200])
