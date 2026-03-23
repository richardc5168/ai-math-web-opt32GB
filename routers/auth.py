"""Auth router — extracted from server.py (EXP-P4-05).

All 5 /v1/app/auth/* endpoints live here.
Helpers remain in server.py; accessed via lazy ``import server`` inside
handler bodies to avoid circular imports.
"""

from __future__ import annotations

import hmac
import os
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

# ── Pydantic models (moved from server.py) ──────────────────────────────

class AppAuthLoginRequest(BaseModel):
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=4)


class AppAuthProvisionRequest(BaseModel):
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=4)
    account_name: str = Field(default="APP User")
    student_name: str = Field(default="學生")
    grade: str = Field(default="G5")
    plan: str = Field(default="basic")
    seats: int = Field(default=1, ge=1, le=200)


class BootstrapRequest(BaseModel):
    student_id: int


class ExchangeRequest(BaseModel):
    bootstrap_token: str = Field(..., min_length=10)


# ── Router ──────────────────────────────────────────────────────────────

auth_router = APIRouter(prefix="/v1/app/auth", tags=["auth"])


@auth_router.post("/provision", summary="Provision purchased app user (admin only)")
def app_auth_provision(
    payload: AppAuthProvisionRequest,
    x_admin_token: str = Header("", alias="X-Admin-Token"),
):
    import server as _srv

    expected = os.getenv("APP_PROVISION_ADMIN_TOKEN", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="APP_PROVISION_ADMIN_TOKEN is not configured")
    if not x_admin_token or not hmac.compare_digest(x_admin_token, expected):
        raise HTTPException(status_code=401, detail="Invalid admin token")

    username = payload.username.strip().lower()
    if not username:
        raise HTTPException(status_code=400, detail="username required")

    conn = _srv.db()
    cur = conn.cursor()
    exists = cur.execute("SELECT id FROM app_users WHERE username = ?", (username,)).fetchone()
    if exists:
        conn.close()
        raise HTTPException(status_code=409, detail="username already exists")

    created = _srv.now_iso()
    api_key = secrets.token_urlsafe(24)
    cur.execute(
        "INSERT INTO accounts(name, api_key, created_at) VALUES(?,?,?)",
        (payload.account_name, api_key, created),
    )
    account_id = int(cur.lastrowid)

    cur.execute(
        """
        INSERT INTO subscriptions(account_id, status, plan, seats, current_period_end, updated_at)
        VALUES(?,?,?,?,?,?)
        """,
        (
            account_id,
            "active",
            payload.plan,
            int(payload.seats),
            (datetime.now() + timedelta(days=30)).isoformat(timespec="seconds"),
            created,
        ),
    )

    cur.execute(
        "INSERT INTO students(account_id, display_name, grade, created_at) VALUES(?,?,?,?)",
        (account_id, payload.student_name, payload.grade, created),
    )
    student_id = int(cur.lastrowid)

    salt = secrets.token_hex(16)
    pwd_hash = _srv._pwd_hash(payload.password, salt)
    cur.execute(
        """
        INSERT INTO app_users(account_id, username, password_hash, password_salt, active, created_at, updated_at)
        VALUES(?,?,?,?,1,?,?)
        """,
        (account_id, username, pwd_hash, salt, created, created),
    )

    conn.commit()
    conn.close()

    return {
        "ok": True,
        "username": username,
        "account_id": account_id,
        "default_student_id": student_id,
        "api_key": api_key,
        "plan": payload.plan,
        "seats": int(payload.seats),
    }


@auth_router.post("/login", summary="Login app user with purchased username/password")
def app_auth_login(payload: AppAuthLoginRequest, request: Request):
    import server as _srv

    client_ip = request.client.host if request.client else "unknown"
    if not _srv._check_rate_limit(f"login:{client_ip}", _srv._RATE_LIMIT_LOGIN):
        raise HTTPException(status_code=429, detail="Too many login attempts")

    username = payload.username.strip().lower()

    if _srv._is_account_locked(username):
        _srv._auth_logger.warning("login_lockout", extra={"username": username, "client_ip": client_ip})
        raise HTTPException(status_code=423, detail="Account temporarily locked due to too many failed attempts")

    conn = _srv.db()
    row = conn.execute(
        """
        SELECT au.*, a.id AS account_id, a.name AS account_name, a.api_key
        FROM app_users au
        JOIN accounts a ON a.id = au.account_id
        WHERE au.username = ?
        """,
        (username,),
    ).fetchone()

    if not row:
        conn.close()
        _srv._record_login_failure(username, client_ip, "unknown_username")
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if int(row["active"] or 0) != 1:
        conn.close()
        _srv._record_login_failure(username, client_ip, "inactive_user")
        raise HTTPException(status_code=403, detail="User is inactive")
    if not _srv._pwd_ok(payload.password, str(row["password_salt"] or ""), str(row["password_hash"] or "")):
        conn.close()
        _srv._record_login_failure(username, client_ip, "wrong_password")
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Lazy re-hash: upgrade SHA-256 to bcrypt on successful login
    stored_hash = str(row["password_hash"] or "")
    if stored_hash and not stored_hash.startswith("$2b$") and not stored_hash.startswith("$2a$"):
        new_hash = _srv._pwd_hash(payload.password, "")
        conn.execute(
            "UPDATE app_users SET password_hash = ?, updated_at = ? WHERE username = ?",
            (new_hash, _srv.now_iso(), username),
        )
        conn.commit()

    sub = conn.execute(
        "SELECT * FROM subscriptions WHERE account_id = ? ORDER BY updated_at DESC LIMIT 1",
        (int(row["account_id"]),),
    ).fetchone()
    if not sub or sub["status"] != "active":
        conn.close()
        raise HTTPException(status_code=402, detail="Subscription required (inactive)")

    all_students = conn.execute(
        "SELECT id, display_name, grade FROM students WHERE account_id = ? ORDER BY id ASC",
        (int(row["account_id"]),),
    ).fetchall()
    conn.close()

    students_list = [
        {"id": int(s["id"]), "display_name": s["display_name"], "grade": s["grade"]}
        for s in all_students
    ]
    st = all_students[0] if all_students else None

    _srv._clear_login_failures(username)
    _srv._auth_logger.info("login_success", extra={"username": username, "client_ip": client_ip})

    return {
        "ok": True,
        "username": username,
        "account_id": int(row["account_id"]),
        "account_name": row["account_name"],
        "api_key": row["api_key"],
        "subscription": {
            "status": sub["status"],
            "plan": sub["plan"],
            "seats": int(sub["seats"] or 0),
            "current_period_end": sub["current_period_end"],
        },
        "default_student": {
            "id": int(st["id"]) if st else None,
            "display_name": st["display_name"] if st else None,
            "grade": st["grade"] if st else None,
        },
        "students": students_list,
    }


@auth_router.get("/whoami", summary="Who am I (via X-API-Key)")
def app_auth_whoami(x_api_key: str = Header(..., alias="X-API-Key")):
    import server as _srv

    acc = _srv.get_account_by_api_key(x_api_key)
    _srv.ensure_subscription_active(int(acc["id"]))
    conn = _srv.db()
    st_count = conn.execute("SELECT COUNT(*) AS c FROM students WHERE account_id = ?", (int(acc["id"]),)).fetchone()
    conn.close()
    return {
        "ok": True,
        "account_id": int(acc["id"]),
        "account_name": acc["name"],
        "students": int((st_count["c"] if st_count else 0) or 0),
    }


@auth_router.post("/bootstrap", summary="Create short-lived bootstrap token for parent-report handoff")
def app_auth_bootstrap(
    payload: BootstrapRequest,
    request: Request,
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    """APP calls this server-side with X-API-Key + student_id.
    Returns a short-lived, single-use bootstrap_token that can be passed
    via URL to parent-report. The token is NOT a long-lived credential."""
    import server as _srv

    client_ip = request.client.host if request.client else "unknown"
    if not _srv._check_rate_limit(f"bootstrap:{client_ip}", _srv._RATE_LIMIT_BOOTSTRAP):
        raise HTTPException(status_code=429, detail="Too many bootstrap requests")

    acc = _srv.get_account_by_api_key(x_api_key)
    account_id = int(acc["id"])
    _srv.ensure_subscription_active(account_id)
    conn = _srv.db()
    _srv._verify_student_ownership(conn, account_id, payload.student_id)
    conn.close()

    _srv._cleanup_expired_tokens_db()

    outstanding = _srv._count_outstanding_tokens(account_id)
    if outstanding >= _srv._MAX_OUTSTANDING_TOKENS_PER_ACCOUNT:
        raise HTTPException(status_code=429, detail="Too many outstanding bootstrap tokens")

    token = secrets.token_urlsafe(32)
    _srv._store_bootstrap_token(token, acc["api_key"], account_id, payload.student_id)
    return {"ok": True, "bootstrap_token": token}


@auth_router.post("/exchange", summary="Exchange bootstrap token for session credentials")
def app_auth_exchange(payload: ExchangeRequest, request: Request):
    """Frontend calls this with a bootstrap_token received via URL.
    Validates and consumes the token (single-use), then returns
    the real credentials + subscription context via POST body only."""
    import server as _srv

    client_ip = request.client.host if request.client else "unknown"
    if not _srv._check_rate_limit(f"exchange:{client_ip}", _srv._RATE_LIMIT_EXCHANGE):
        raise HTTPException(status_code=429, detail="Too many exchange requests")

    entry = _srv._consume_bootstrap_token(payload.bootstrap_token)
    if not entry:
        raise HTTPException(status_code=401, detail="Invalid or expired bootstrap token")

    _srv.ensure_subscription_active(entry["account_id"])

    return {
        "ok": True,
        "api_key": entry["api_key"],
        "student_id": entry["student_id"],
        "subscription": {"status": "active"},
    }
