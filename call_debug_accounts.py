import requests
print('calling debug accounts...')
try:
    r = requests.get('http://127.0.0.1:8000/_debug/accounts', timeout=5)
    print(r.status_code)
    print(r.text)
except Exception as e:
    print('error', e)
