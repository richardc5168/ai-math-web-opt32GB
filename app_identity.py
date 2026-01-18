from __future__ import annotations

import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Identity:
    api_key: str
    account_id: int
    student_id: int
    student_name: str
    grade: str


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def ensure_app_db_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            api_key TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            display_name TEXT NOT NULL,
            grade TEXT DEFAULT 'G5',
            created_at TEXT NOT NULL,
            FOREIGN KEY(account_id) REFERENCES accounts(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            plan TEXT DEFAULT 'basic',
            seats INTEGER DEFAULT 1,
            current_period_end TEXT,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(account_id) REFERENCES accounts(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS question_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT,
            difficulty TEXT,
            question TEXT,
            correct_answer TEXT,
            explanation TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            question_id INTEGER,
            mode TEXT NOT NULL DEFAULT 'interactive',
            topic TEXT,
            difficulty TEXT,
            question TEXT,
            correct_answer TEXT,
            user_answer TEXT,
            is_correct INTEGER,
            time_spent_sec INTEGER DEFAULT 0,
            ts TEXT NOT NULL,
            FOREIGN KEY(account_id) REFERENCES accounts(id),
            FOREIGN KEY(student_id) REFERENCES students(id),
            FOREIGN KEY(question_id) REFERENCES question_cache(id)
        )
        """
    )

    conn.commit()


def _ensure_subscription(conn: sqlite3.Connection, account_id: int) -> None:
    cur = conn.cursor()
    row = cur.execute(
        "SELECT id FROM subscriptions WHERE account_id=? AND status='active' ORDER BY id DESC LIMIT 1",
        (account_id,),
    ).fetchone()
    if row:
        return

    cur.execute(
        "INSERT INTO subscriptions(account_id,status,plan,seats,current_period_end,updated_at) VALUES (?,?,?,?,?,?)",
        (
            account_id,
            "active",
            "basic",
            1,
            (datetime.now() + timedelta(days=30)).isoformat(timespec="seconds"),
            _now_iso(),
        ),
    )
    conn.commit()


def _prompt_choice(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except Exception:
        return ""


def select_or_create_identity(
    app_db_path: str | Path = "app.db",
    default_account_name: str = "MathCLI",
    default_grade: str = "G5",
) -> Identity:
    """Interactive selection/creation of account (api_key) and student."""

    app_db_path = Path(app_db_path)
    conn = sqlite3.connect(str(app_db_path))
    conn.row_factory = sqlite3.Row
    try:
        ensure_app_db_schema(conn)

        print("\n=== 身分/註冊碼 (API key) ===")
        api_key = _prompt_choice("輸入註冊碼(API key)，直接 Enter 產生新的: ")

        cur = conn.cursor()
        if api_key:
            row = cur.execute("SELECT id,name,api_key FROM accounts WHERE api_key=?", (api_key,)).fetchone()
            if row:
                account_id = int(row["id"])
            else:
                name = _prompt_choice(f"此 key 尚未註冊。輸入帳號名稱(Enter 使用 {default_account_name}): ")
                if not name:
                    name = default_account_name
                cur.execute(
                    "INSERT INTO accounts(name,api_key,created_at) VALUES (?,?,?)",
                    (name, api_key, _now_iso()),
                )
                account_id = int(cur.lastrowid)
                conn.commit()
        else:
            api_key = secrets.token_urlsafe(24)
            name = _prompt_choice(f"建立新帳號名稱(Enter 使用 {default_account_name}): ")
            if not name:
                name = default_account_name
            cur.execute(
                "INSERT INTO accounts(name,api_key,created_at) VALUES (?,?,?)",
                (name, api_key, _now_iso()),
            )
            account_id = int(cur.lastrowid)
            conn.commit()

        _ensure_subscription(conn, account_id)

        students = cur.execute(
            "SELECT id,display_name,grade FROM students WHERE account_id=? ORDER BY id ASC",
            (account_id,),
        ).fetchall()

        if students:
            print("\n可用學生：")
            for idx, s in enumerate(students, start=1):
                print(f"  {idx}. {s['display_name']} (id={s['id']}, grade={s['grade']})")
            choice = _prompt_choice("選擇學生編號，或輸入學生名稱(可重用既有)： ")
        else:
            print("\n此帳號尚無學生，請建立一個。")
            choice = ""

        student_id: int
        student_name: str
        grade: str

        if choice.isdigit() and 1 <= int(choice) <= len(students):
            s = students[int(choice) - 1]
            student_id = int(s["id"])
            student_name = str(s["display_name"])
            grade = str(s["grade"])
        else:
            # If user typed a name, try to match an existing student first.
            typed_name = (choice or "").strip()
            if typed_name and students:
                typed_lower = typed_name.casefold()
                matches = [s for s in students if str(s["display_name"]).casefold() == typed_lower]
                if len(matches) == 1:
                    s = matches[0]
                    student_id = int(s["id"])
                    student_name = str(s["display_name"])
                    grade = str(s["grade"])
                elif len(matches) > 1:
                    # Duplicate names exist; pick the newest (highest id).
                    s = sorted(matches, key=lambda r: int(r["id"]), reverse=True)[0]
                    student_id = int(s["id"])
                    student_name = str(s["display_name"])
                    grade = str(s["grade"])
                else:
                    # Not found -> create
                    g = _prompt_choice(f"年級(Enter 使用 {default_grade}): ")
                    if not g:
                        g = default_grade
                    cur.execute(
                        "INSERT INTO students(account_id,display_name,grade,created_at) VALUES (?,?,?,?)",
                        (account_id, typed_name, g, _now_iso()),
                    )
                    student_id = int(cur.lastrowid)
                    student_name = typed_name
                    grade = g
                    conn.commit()
            else:
                if not typed_name:
                    typed_name = _prompt_choice("學生名稱: ")
                if not typed_name:
                    typed_name = "Student"
                g = _prompt_choice(f"年級(Enter 使用 {default_grade}): ")
                if not g:
                    g = default_grade
                cur.execute(
                    "INSERT INTO students(account_id,display_name,grade,created_at) VALUES (?,?,?,?)",
                    (account_id, typed_name, g, _now_iso()),
                )
                student_id = int(cur.lastrowid)
                student_name = typed_name
                grade = g
                conn.commit()

        print(f"\n你的註冊碼(API key)：{api_key}")
        print(f"目前學生：{student_name} (student_id={student_id})\n")

        return Identity(api_key=api_key, account_id=account_id, student_id=student_id, student_name=student_name, grade=grade)

    finally:
        conn.close()


def record_attempt_to_app_db(
    identity: Identity,
    qobj: dict,
    user_answer: str,
    is_correct: int | None,
    mode: str,
    app_db_path: str | Path = "app.db",
    time_spent_sec: int = 0,
) -> None:
    app_db_path = Path(app_db_path)
    conn = sqlite3.connect(str(app_db_path))
    try:
        ensure_app_db_schema(conn)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO question_cache(topic,difficulty,question,correct_answer,explanation,created_at) VALUES (?,?,?,?,?,?)",
            (
                qobj.get("topic"),
                qobj.get("difficulty"),
                qobj.get("question"),
                qobj.get("answer"),
                qobj.get("explanation", ""),
                _now_iso(),
            ),
        )
        question_id = int(cur.lastrowid)
        cur.execute(
            """
            INSERT INTO attempts(account_id, student_id, question_id, mode, topic, difficulty, question, correct_answer,
                                 user_answer, is_correct, time_spent_sec, ts)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                identity.account_id,
                identity.student_id,
                question_id,
                mode,
                qobj.get("topic"),
                qobj.get("difficulty"),
                qobj.get("question"),
                qobj.get("answer"),
                user_answer,
                is_correct,
                int(time_spent_sec),
                _now_iso(),
            ),
        )
        conn.commit()
    finally:
        conn.close()
