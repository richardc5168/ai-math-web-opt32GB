#!/usr/bin/env python3
"""RAGWEB interactive CLI

Usage: run in PowerShell with `.
ag_cli.ps1` or `python rag_cli.py`
"""
import json
import os
import sqlite3
import secrets
import sys
from pathlib import Path
from datetime import datetime, timedelta

try:
    import requests
except Exception:
    print('Please install requests: pip install requests')
    raise

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / '.rag_cli_config.json'
LOG_PATH = ROOT / 'rag_cli_log.jsonl'


def load_config():
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
        except Exception:
            return {}
    return {}


def save_config(cfg):
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding='utf-8')


def log(entry: dict):
    entry.setdefault('ts', datetime.utcnow().isoformat() + 'Z')
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')


def create_demo_account():
    """Create a demo account + subscription + student directly in app.db and return api_key, student_id, account_id"""
    db_path = ROOT / 'app.db'
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    api_key = secrets.token_urlsafe(24)
    now = datetime.now().isoformat(timespec='seconds')
    cur.execute("INSERT INTO accounts(name, api_key, created_at) VALUES (?,?,?)",
                ('CLI-Demo-Account', api_key, now))
    account_id = cur.lastrowid
    cur.execute(
        "INSERT INTO subscriptions(account_id, status, plan, seats, current_period_end, updated_at) VALUES (?,?,?,?,?,?)",
        (account_id, 'active', 'basic', 1, (datetime.now() + timedelta(days=30)).isoformat(timespec='seconds'), now)
    )
    cur.execute(
        "INSERT INTO students(account_id, display_name, grade, created_at) VALUES (?,?,?,?)",
        (account_id, 'CLI-Demo-Student', 'G5', now)
    )
    student_id = cur.lastrowid
    conn.commit()
    conn.close()
    return api_key, student_id, account_id


def post_next(base_url, api_key, student_id):
    url = base_url.rstrip('/') + '/v1/questions/next'
    headers = {'X-API-Key': api_key}
    try:
        r = requests.post(url, params={'student_id': student_id}, headers=headers, timeout=10)
        data = r.json() if r.text else {}
    except Exception as e:
        print('Request error:', e)
        return None
    print(f'Status: {r.status_code}')
    print(json.dumps(data, ensure_ascii=False, indent=2))
    log({'action': 'next', 'status': r.status_code, 'resp': data, 'student_id': student_id})
    return data


def post_submit(base_url, api_key, body: dict):
    url = base_url.rstrip('/') + '/v1/answers/submit'
    headers = {'X-API-Key': api_key}
    try:
        r = requests.post(url, json=body, headers=headers, timeout=10)
        data = r.json() if r.text else {}
    except Exception as e:
        print('Request error:', e)
        return None
    print(f'Status: {r.status_code}')
    print(json.dumps(data, ensure_ascii=False, indent=2))
    log({'action': 'submit', 'status': r.status_code, 'req': body, 'resp': data})
    return data


def post_customsolve(base_url, api_key, question_text):
    url = base_url.rstrip('/') + '/v1/custom/solve'
    headers = {'X-API-Key': api_key}
    body = {'question': question_text}
    try:
        r = requests.post(url, json=body, headers=headers, timeout=15)
        data = r.json() if r.text else {}
    except Exception as e:
        print('Request error:', e)
        return None
    print(f'Status: {r.status_code}')
    print(json.dumps(data, ensure_ascii=False, indent=2))
    log({'action': 'custom_solve', 'status': r.status_code, 'req': body, 'resp': data})
    return data


def get_summary(base_url, api_key, student_id):
    url = base_url.rstrip('/') + '/v1/reports/summary'
    headers = {'X-API-Key': api_key}
    try:
        r = requests.get(url, params={'student_id': student_id}, headers=headers, timeout=10)
        data = r.json() if r.text else {}
    except Exception as e:
        print('Request error:', e)
        return None
    print(f'Status: {r.status_code}')
    print(json.dumps(data, ensure_ascii=False, indent=2))
    log({'action': 'summary', 'status': r.status_code, 'resp': data, 'student_id': student_id})
    return data


def interactive():
    cfg = load_config()
    base_url = cfg.get('base_url', 'http://127.0.0.1:8000')
    api_key = cfg.get('api_key', '')
    student_id = cfg.get('student_id', 1)

    print('RAGWEB CLI — 互動模式')
    print('伺服器 base URL:', base_url)
    print('若需修改設定請輸入 `config`')

    while True:
        cmd = input('\n輸入指令 [next, submit, custom, summary, config, log, quit]: ').strip()
        if cmd in ('q', 'quit'):
            break
        if cmd == 'config':
            new = input(f'Base URL ({base_url}): ').strip()
            if new:
                base_url = new
            new = input(f'API Key ({"set" if api_key else "not set"}): ').strip()
            if new:
                api_key = new
            new = input(f'Student ID ({student_id}): ').strip()
            if new:
                try:
                    student_id = int(new)
                except Exception:
                    print('Student ID 必須為數字，保留原值')
            cfg.update({'base_url': base_url, 'api_key': api_key, 'student_id': student_id})
            save_config(cfg)
            print('設定已儲存')
            continue

        if cmd == 'next':
            if not api_key:
                print('請先在 config 中設定 API Key')
                continue
            post_next(base_url, api_key, student_id)
            continue

        if cmd == 'submit':
            if not api_key:
                print('請先在 config 中設定 API Key')
                continue
            qid = input('Question ID: ').strip()
            if not qid:
                print('Question ID 為必填')
                continue
            ans = input('Your answer: ').strip()
            ts = input('Time spent seconds (default 10): ').strip() or '10'
            try:
                body = {'student_id': int(student_id), 'question_id': int(qid), 'user_answer': ans, 'time_spent_sec': int(ts)}
            except Exception:
                print('輸入格式錯誤，請確認數字欄位')
                continue
            post_submit(base_url, api_key, body)
            continue

        if cmd == 'custom':
            if not api_key:
                print('請先在 config 中設定 API Key')
                continue
            qtxt = input('Custom question text: ').strip()
            if not qtxt:
                print('題目不得為空')
                continue
            post_customsolve(base_url, api_key, qtxt)
            continue

        if cmd == 'summary':
            if not api_key:
                print('請先在 config 中設定 API Key')
                continue
            get_summary(base_url, api_key, student_id)
            continue

        if cmd == 'log':
            if LOG_PATH.exists():
                print('最近 200 行 log:')
                with open(LOG_PATH, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[-200:]
                    for l in lines:
                        print(l.strip())
            else:
                print('尚無 log')
            continue

        print('未知指令')


if __name__ == '__main__':
    # support a non-interactive bootstrap mode for PowerShell convenience
    if '--bootstrap' in sys.argv:
        print('Creating demo account and student in app.db...')
        try:
            api_key, student_id, account_id = create_demo_account()
            cfg = load_config()
            cfg.update({'api_key': api_key, 'student_id': student_id, 'base_url': cfg.get('base_url', 'http://127.0.0.1:8000')})
            save_config(cfg)
            print(f'Created account_id={account_id}, student_id={student_id}, api_key={api_key}')
            print('Config saved to', CONFIG_PATH)
        except Exception as e:
            print('Error creating demo account:', e)
        sys.exit(0)
    interactive()
