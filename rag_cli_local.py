#!/usr/bin/env python3
"""Unified local CLI entry.

Default: original rag_cli_local behavior (generate via engine, prompt answer, record into app.db).
Also supports launching math123OK.py full CLI from the same entry.

Usage:
    python rag_cli_local.py
    python rag_cli_local.py --mode local
    python rag_cli_local.py --mode math123
    python rag_cli_local.py --math123
"""
import argparse
import sqlite3
from pathlib import Path
import secrets
from datetime import datetime, timedelta
import engine

DB_PATH = Path('app.db')

def now_iso():
    return datetime.now().isoformat(timespec='seconds')


def ensure_demo_account():
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute("SELECT id,api_key FROM accounts WHERE name=?", ('CLI-Local',))
    r = cur.fetchone()
    if r:
        account_id, api_key = r
    else:
        api_key = secrets.token_urlsafe(24)
        cur.execute("INSERT INTO accounts(name,api_key,created_at) VALUES (?,?,?)", ('CLI-Local', api_key, now_iso()))
        account_id = cur.lastrowid
        cur.execute("INSERT INTO subscriptions(account_id,status,plan,seats,current_period_end,updated_at) VALUES (?,?,?,?,?,?)",
                    (account_id,'active','basic',1,(datetime.now()+timedelta(days=30)).isoformat(timespec='seconds'), now_iso()))
        cur.execute("INSERT INTO students(account_id,display_name,grade,created_at) VALUES (?,?,?,?)", (account_id,'LocalStudent','G5',now_iso()))
    conn.commit()
    # find student id
    cur.execute("SELECT id FROM students WHERE account_id=? ORDER BY id DESC LIMIT 1", (account_id,))
    student_id = cur.fetchone()[0]
    conn.close()
    return api_key, account_id, student_id


def insert_question(qdict):
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute("INSERT INTO question_cache(topic,difficulty,question,correct_answer,explanation,created_at) VALUES (?,?,?,?,?,?)",
                (qdict['topic'], qdict['difficulty'], qdict['question'], qdict.get('answer'), qdict.get('explanation',''), now_iso()))
    qid = cur.lastrowid
    conn.commit()
    conn.close()
    return qid


def record_attempt(account_id, student_id, question_id, qdict, user_answer, time_spent=10):
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    # check correctness using engine.check
    is_correct = engine.check(user_answer, qdict.get('answer'))
    cur.execute("INSERT INTO attempts(account_id, student_id, question_id, mode, topic, difficulty, question, correct_answer, user_answer, is_correct, time_spent_sec, ts) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (account_id, student_id, question_id, 'interactive', qdict.get('topic'), qdict.get('difficulty'), qdict.get('question'), qdict.get('answer'), user_answer, is_correct, time_spent, now_iso()))
    conn.commit()
    conn.close()
    return is_correct


def main_local():
    api_key, account_id, student_id = ensure_demo_account()
    print('Using account_id=', account_id, 'student_id=', student_id, 'api_key=', api_key)
    q = engine.next_question()
    print('\nQuestion:')
    print(q['question'])
    try:
        ans = input('\nYour answer: ').strip()
    except Exception:
        ans = ''
    qid = insert_question(q)
    is_correct = record_attempt(account_id, student_id, qid, q, ans or '')
    print('\nRecorded attempt. is_correct=', is_correct)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    totals = conn.execute(
        "SELECT COUNT(*) AS cnt, SUM(CASE WHEN is_correct=1 THEN 1 ELSE 0 END) AS correct FROM attempts WHERE student_id=?",
        (student_id,),
    ).fetchone()
    print('\nTotals:', dict(totals))
    conn.close()


def main_math123():
    # Load and run math123OK in a robust way.
    # The file currently contains U+00A0 (NBSP) characters in indentation,
    # which can raise SyntaxError on import. We sanitize at runtime to keep
    # math123OK.py unchanged while still exposing all its functionality here.
    import sys
    import types

    math_path = Path(__file__).resolve().parent / 'math123OK.py'
    src = math_path.read_text(encoding='utf-8')
    src = src.replace('\u00A0', ' ')

    mod = types.ModuleType('math123OK_sanitized')
    mod.__file__ = str(math_path)
    mod.__package__ = ''

    code = compile(src, str(math_path), 'exec')
    exec(code, mod.__dict__)

    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    if not hasattr(mod, 'main'):
        raise RuntimeError('math123OK.py does not define main()')
    mod.main()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument('--mode', choices=['local', 'math123'], default='local')
    parser.add_argument('--math123', action='store_true', help='Shortcut for --mode math123')
    args = parser.parse_args()

    if args.math123:
        args.mode = 'math123'

    if args.mode == 'math123':
        main_math123()
    else:
        main_local()
