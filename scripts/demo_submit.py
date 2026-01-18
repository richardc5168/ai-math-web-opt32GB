import json
import urllib.request

API_KEY = "j7sqS2ijtI8kZ8vogO_1Z3B0s74NsHF5"
BASE = "http://127.0.0.1:8000"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

def post(path, body):
    if body is None:
        data = None
    else:
        data = json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method='POST')
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.load(resp)

if __name__ == '__main__':
    # Use query param for next question to match endpoint validation
    next_q = post(f'/v1/questions/next?student_id=2', None)
    print('NEXT:', json.dumps(next_q, ensure_ascii=False))
    qid = next_q['question_id']

    # submit a plausible answer (here we submit the correct numeric result)
    submit = post('/v1/answers/submit', {
        'student_id': 2,
        'question_id': qid,
        'user_answer': '-4',
        'time_spent_sec': 12
    })
    print('SUBMIT:', json.dumps(submit, ensure_ascii=False))
