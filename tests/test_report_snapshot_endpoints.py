"""Tests for subscription-gated report snapshot endpoints.

Covers:
  - POST /v1/app/report_snapshots  (write)
  - POST /v1/app/report_snapshots/latest  (read)
  - Auth: missing API key → 401/422
  - Auth: invalid API key → 401
  - Auth: inactive subscription → 402
  - Ownership: wrong student_id → 404
  - Happy path: write + read roundtrip
"""
import importlib
import os

import httpx
import pytest


@pytest.fixture
def setup_server(tmp_path):
    """Set up a fresh server with a provisioned account."""
    db_path = tmp_path / "snapshots_test.db"
    os.environ["DB_PATH"] = str(db_path)
    os.environ["APP_PROVISION_ADMIN_TOKEN"] = "test-admin-token"

    import server
    importlib.reload(server)
    return server


ADMIN_HEADERS = {"X-Admin-Token": "test-admin-token"}


async def _provision(client, username="testuser"):
    resp = await client.post("/v1/app/auth/provision", json={
        "username": username,
        "password": "pass1234",
    }, headers=ADMIN_HEADERS)
    assert resp.status_code == 200, f"Provision failed: {resp.text}"
    body = resp.json()
    return body["api_key"], body["default_student_id"]


@pytest.mark.anyio
async def test_snapshot_missing_api_key(setup_server):
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        resp = await c.post("/v1/app/report_snapshots", json={
            "student_id": 1,
            "report_payload": {"test": True}
        })
        assert resp.status_code in (401, 422), f"Expected 401 or 422, got {resp.status_code}"


@pytest.mark.anyio
async def test_snapshot_invalid_api_key(setup_server):
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        resp = await c.post(
            "/v1/app/report_snapshots",
            json={"student_id": 1, "report_payload": {"test": True}},
            headers={"X-API-Key": "invalid-key-999"},
        )
        assert resp.status_code == 401


@pytest.mark.anyio
async def test_snapshot_inactive_subscription(setup_server):
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        api_key, student_id = await _provision(c, "testuser_inactive")

        # Deactivate subscription
        conn = setup_server.db()
        conn.execute("UPDATE subscriptions SET status = 'inactive'")
        conn.commit()
        conn.close()

        resp = await c.post(
            "/v1/app/report_snapshots",
            json={"student_id": student_id, "report_payload": {"test": True}},
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 402


@pytest.mark.anyio
async def test_snapshot_wrong_student_ownership(setup_server):
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        api_key, _ = await _provision(c, "testuser_owner")

        resp = await c.post(
            "/v1/app/report_snapshots",
            json={"student_id": 99999, "report_payload": {"test": True}},
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 404


@pytest.mark.anyio
async def test_snapshot_write_and_read_happy_path(setup_server):
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        api_key, student_id = await _provision(c, "testuser_happy")

        report_payload = {
            "v": 1,
            "name": "TestStudent",
            "ts": 1700000000000,
            "days": 7,
            "d": {"total": 10, "correct": 8, "accuracy": 80},
        }

        write_resp = await c.post(
            "/v1/app/report_snapshots",
            json={"student_id": student_id, "report_payload": report_payload, "source": "test"},
            headers={"X-API-Key": api_key},
        )
        assert write_resp.status_code == 200
        assert write_resp.json()["ok"] is True

        read_resp = await c.post(
            "/v1/app/report_snapshots/latest",
            json={"student_id": student_id},
            headers={"X-API-Key": api_key},
        )
        assert read_resp.status_code == 200
        body = read_resp.json()
        assert body["ok"] is True
        assert body["snapshot"]["student_id"] == student_id
        assert body["snapshot"]["report_payload"]["d"]["accuracy"] == 80
        assert body["snapshot"]["source"] == "test"


@pytest.mark.anyio
async def test_snapshot_read_no_snapshot(setup_server):
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        api_key, student_id = await _provision(c, "testuser_nosnapshot")

        read_resp = await c.post(
            "/v1/app/report_snapshots/latest",
            json={"student_id": student_id},
            headers={"X-API-Key": api_key},
        )
        assert read_resp.status_code == 404


@pytest.mark.anyio
async def test_snapshot_upsert_overwrites(setup_server):
    """Second write for same student/account should update, not insert."""
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        api_key, student_id = await _provision(c, "testuser_upsert")
        headers = {"X-API-Key": api_key}

        await c.post("/v1/app/report_snapshots", json={
            "student_id": student_id,
            "report_payload": {"version": 1},
        }, headers=headers)

        await c.post("/v1/app/report_snapshots", json={
            "student_id": student_id,
            "report_payload": {"version": 2},
        }, headers=headers)

        read = await c.post("/v1/app/report_snapshots/latest", json={
            "student_id": student_id,
        }, headers=headers)
        assert read.json()["snapshot"]["report_payload"]["version"] == 2


# ========= Practice Events Endpoint Tests =========

@pytest.mark.anyio
async def test_practice_event_missing_api_key(setup_server):
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        resp = await c.post("/v1/app/practice_events", json={
            "student_id": 1,
            "event": {"score": 8, "total": 10, "topic": "fraction"}
        })
        assert resp.status_code in (401, 422)


@pytest.mark.anyio
async def test_practice_event_inactive_subscription(setup_server):
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        api_key, student_id = await _provision(c, "pe_inactive")
        conn = setup_server.db()
        conn.execute("UPDATE subscriptions SET status = 'inactive' WHERE account_id = (SELECT id FROM accounts WHERE api_key = ?)", (api_key,))
        conn.commit()
        conn.close()

        resp = await c.post("/v1/app/practice_events", json={
            "student_id": student_id,
            "event": {"score": 5, "total": 10}
        }, headers={"X-API-Key": api_key})
        assert resp.status_code == 402


@pytest.mark.anyio
async def test_practice_event_wrong_student(setup_server):
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        api_key, _ = await _provision(c, "pe_owner")
        resp = await c.post("/v1/app/practice_events", json={
            "student_id": 99999,
            "event": {"score": 5, "total": 10}
        }, headers={"X-API-Key": api_key})
        assert resp.status_code == 404


@pytest.mark.anyio
async def test_practice_event_happy_path_creates_snapshot(setup_server):
    """Practice event on a student with no existing snapshot should create one."""
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        api_key, student_id = await _provision(c, "pe_happy_new")
        headers = {"X-API-Key": api_key}

        resp = await c.post("/v1/app/practice_events", json={
            "student_id": student_id,
            "event": {"score": 8, "total": 10, "topic": "fraction", "kind": "add"}
        }, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        # Verify event was stored in snapshot
        read = await c.post("/v1/app/report_snapshots/latest", json={
            "student_id": student_id,
        }, headers=headers)
        assert read.status_code == 200
        payload = read.json()["snapshot"]["report_payload"]
        events = payload["d"]["practice"]["events"]
        assert len(events) == 1
        assert events[0]["score"] == 8
        assert events[0]["topic"] == "fraction"


@pytest.mark.anyio
async def test_practice_event_appends_to_existing_snapshot(setup_server):
    """Practice event on a student with existing snapshot should append."""
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        api_key, student_id = await _provision(c, "pe_happy_existing")
        headers = {"X-API-Key": api_key}

        # Write an initial snapshot
        await c.post("/v1/app/report_snapshots", json={
            "student_id": student_id,
            "report_payload": {"v": 1, "d": {"total": 10}},
        }, headers=headers)

        # Append a practice event
        resp = await c.post("/v1/app/practice_events", json={
            "student_id": student_id,
            "event": {"score": 7, "total": 10, "topic": "decimal"}
        }, headers=headers)
        assert resp.status_code == 200

        # Verify event was appended and original payload preserved
        read = await c.post("/v1/app/report_snapshots/latest", json={
            "student_id": student_id,
        }, headers=headers)
        payload = read.json()["snapshot"]["report_payload"]
        assert payload["v"] == 1
        assert payload["d"]["total"] == 10
        events = payload["d"]["practice"]["events"]
        assert len(events) == 1
        assert events[0]["topic"] == "decimal"


# ========= Bootstrap / Exchange Token Tests =========

@pytest.mark.anyio
async def test_bootstrap_missing_api_key(setup_server):
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        resp = await c.post("/v1/app/auth/bootstrap", json={"student_id": 1})
        assert resp.status_code in (401, 422)


@pytest.mark.anyio
async def test_bootstrap_invalid_api_key(setup_server):
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        resp = await c.post(
            "/v1/app/auth/bootstrap",
            json={"student_id": 1},
            headers={"X-API-Key": "invalid-key-999"},
        )
        assert resp.status_code == 401


@pytest.mark.anyio
async def test_bootstrap_inactive_subscription(setup_server):
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        api_key, student_id = await _provision(c, "bs_inactive")
        conn = setup_server.db()
        conn.execute(
            "UPDATE subscriptions SET status = 'inactive' WHERE account_id = "
            "(SELECT id FROM accounts WHERE api_key = ?)", (api_key,)
        )
        conn.commit()
        conn.close()

        resp = await c.post(
            "/v1/app/auth/bootstrap",
            json={"student_id": student_id},
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 402


@pytest.mark.anyio
async def test_bootstrap_wrong_student(setup_server):
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        api_key, _ = await _provision(c, "bs_owner")
        resp = await c.post(
            "/v1/app/auth/bootstrap",
            json={"student_id": 99999},
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 404


@pytest.mark.anyio
async def test_bootstrap_happy_path(setup_server):
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        api_key, student_id = await _provision(c, "bs_happy")
        resp = await c.post(
            "/v1/app/auth/bootstrap",
            json={"student_id": student_id},
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert len(body["bootstrap_token"]) >= 10


@pytest.mark.anyio
async def test_exchange_invalid_token(setup_server):
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        resp = await c.post(
            "/v1/app/auth/exchange",
            json={"bootstrap_token": "nonexistent-token-value"},
        )
        assert resp.status_code == 401


@pytest.mark.anyio
async def test_exchange_replayed_token(setup_server):
    """Token must be single-use: second exchange attempt must fail."""
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        api_key, student_id = await _provision(c, "ex_replay")
        bs_resp = await c.post(
            "/v1/app/auth/bootstrap",
            json={"student_id": student_id},
            headers={"X-API-Key": api_key},
        )
        token = bs_resp.json()["bootstrap_token"]

        # First exchange — should succeed
        first = await c.post("/v1/app/auth/exchange", json={"bootstrap_token": token})
        assert first.status_code == 200

        # Second exchange — same token — must fail (single-use)
        second = await c.post("/v1/app/auth/exchange", json={"bootstrap_token": token})
        assert second.status_code == 401


@pytest.mark.anyio
async def test_exchange_expired_token(setup_server):
    """Expired tokens must be rejected."""
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        api_key, student_id = await _provision(c, "ex_expired")
        bs_resp = await c.post(
            "/v1/app/auth/bootstrap",
            json={"student_id": student_id},
            headers={"X-API-Key": api_key},
        )
        token = bs_resp.json()["bootstrap_token"]

        # Artificially expire the token via DB
        conn = setup_server.db()
        token_hash = setup_server._hash_token(token)
        conn.execute(
            "UPDATE bootstrap_tokens SET expires_at = '2020-01-01T00:00:00' WHERE token_hash = ?",
            (token_hash,),
        )
        conn.commit()
        conn.close()

        resp = await c.post("/v1/app/auth/exchange", json={"bootstrap_token": token})
        assert resp.status_code == 401


@pytest.mark.anyio
async def test_exchange_happy_path(setup_server):
    """Full bootstrap → exchange roundtrip must return credentials."""
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        api_key, student_id = await _provision(c, "ex_happy")
        bs_resp = await c.post(
            "/v1/app/auth/bootstrap",
            json={"student_id": student_id},
            headers={"X-API-Key": api_key},
        )
        token = bs_resp.json()["bootstrap_token"]

        resp = await c.post("/v1/app/auth/exchange", json={"bootstrap_token": token})
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["api_key"] == api_key
        assert body["student_id"] == student_id
        assert body["subscription"]["status"] == "active"


# ========= Rate Limiting & Token Cap Tests =========

@pytest.mark.anyio
async def test_bootstrap_rate_limit(setup_server):
    """Bootstrap requests exceeding the per-IP limit must return 429."""
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        api_key, student_id = await _provision(c, "rl_bootstrap")
        headers = {"X-API-Key": api_key}

        # Clear any prior rate limit / token state in DB
        conn = setup_server.db()
        conn.execute("DELETE FROM rate_limit_events")
        conn.execute("DELETE FROM bootstrap_tokens")
        conn.commit()
        conn.close()
        # Temporarily lower the limit for testing
        orig = setup_server._RATE_LIMIT_BOOTSTRAP
        setup_server._RATE_LIMIT_BOOTSTRAP = 3
        try:
            for i in range(3):
                resp = await c.post("/v1/app/auth/bootstrap", json={"student_id": student_id}, headers=headers)
                assert resp.status_code == 200, f"Request {i+1} should succeed"
            # 4th request should be rate-limited
            resp = await c.post("/v1/app/auth/bootstrap", json={"student_id": student_id}, headers=headers)
            assert resp.status_code == 429
        finally:
            setup_server._RATE_LIMIT_BOOTSTRAP = orig
            conn = setup_server.db()
            conn.execute("DELETE FROM rate_limit_events")
            conn.execute("DELETE FROM bootstrap_tokens")
            conn.commit()
            conn.close()


@pytest.mark.anyio
async def test_exchange_rate_limit(setup_server):
    """Exchange requests exceeding the per-IP limit must return 429."""
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        # Clear any prior rate limit state in DB
        conn = setup_server.db()
        conn.execute("DELETE FROM rate_limit_events")
        conn.commit()
        conn.close()
        orig = setup_server._RATE_LIMIT_EXCHANGE
        setup_server._RATE_LIMIT_EXCHANGE = 3
        try:
            for i in range(3):
                resp = await c.post("/v1/app/auth/exchange", json={"bootstrap_token": f"nonexistent-token-{i:04d}"})
                # These fail with 401 (invalid token) but still count against rate limit
                assert resp.status_code == 401
            # 4th request should be rate-limited before token check
            resp = await c.post("/v1/app/auth/exchange", json={"bootstrap_token": "nonexistent-token-0003"})
            assert resp.status_code == 429
        finally:
            setup_server._RATE_LIMIT_EXCHANGE = orig
            conn = setup_server.db()
            conn.execute("DELETE FROM rate_limit_events")
            conn.commit()
            conn.close()


@pytest.mark.anyio
async def test_bootstrap_per_account_token_cap(setup_server):
    """Outstanding tokens per account must be capped."""
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        api_key, student_id = await _provision(c, "cap_account")
        headers = {"X-API-Key": api_key}

        conn = setup_server.db()
        conn.execute("DELETE FROM rate_limit_events")
        conn.execute("DELETE FROM bootstrap_tokens")
        conn.commit()
        conn.close()
        orig_cap = setup_server._MAX_OUTSTANDING_TOKENS_PER_ACCOUNT
        setup_server._MAX_OUTSTANDING_TOKENS_PER_ACCOUNT = 2
        try:
            # Create 2 tokens (at cap)
            for i in range(2):
                resp = await c.post("/v1/app/auth/bootstrap", json={"student_id": student_id}, headers=headers)
                assert resp.status_code == 200
            # 3rd token should be refused (cap hit)
            resp = await c.post("/v1/app/auth/bootstrap", json={"student_id": student_id}, headers=headers)
            assert resp.status_code == 429
            assert "outstanding" in resp.json()["detail"].lower()
        finally:
            setup_server._MAX_OUTSTANDING_TOKENS_PER_ACCOUNT = orig_cap
            conn = setup_server.db()
            conn.execute("DELETE FROM bootstrap_tokens")
            conn.execute("DELETE FROM rate_limit_events")
            conn.commit()
            conn.close()


@pytest.mark.anyio
async def test_rate_limit_does_not_block_normal_flow(setup_server):
    """Normal single bootstrap+exchange flow must succeed under default limits."""
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        conn = setup_server.db()
        conn.execute("DELETE FROM rate_limit_events")
        conn.execute("DELETE FROM bootstrap_tokens")
        conn.commit()
        conn.close()
        api_key, student_id = await _provision(c, "rl_normal")

        # Bootstrap
        bs = await c.post("/v1/app/auth/bootstrap", json={"student_id": student_id}, headers={"X-API-Key": api_key})
        assert bs.status_code == 200
        token = bs.json()["bootstrap_token"]

        # Exchange
        ex = await c.post("/v1/app/auth/exchange", json={"bootstrap_token": token})
        assert ex.status_code == 200
        assert ex.json()["api_key"] == api_key


@pytest.mark.anyio
async def test_token_survives_server_module_state(setup_server):
    """Token is stored in DB, not just in-memory. Verify DB-backed persistence."""
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        api_key, student_id = await _provision(c, "db_persist")
        bs = await c.post("/v1/app/auth/bootstrap", json={"student_id": student_id}, headers={"X-API-Key": api_key})
        token = bs.json()["bootstrap_token"]

        # Verify the token exists in the DB
        conn = setup_server.db()
        token_hash = setup_server._hash_token(token)
        row = conn.execute(
            "SELECT * FROM bootstrap_tokens WHERE token_hash = ?", (token_hash,)
        ).fetchone()
        conn.close()
        assert row is not None, "Token must be persisted in DB"
        assert row["consumed_at"] is None, "Token must not be consumed yet"

        # Exchange should still work
        ex = await c.post("/v1/app/auth/exchange", json={"bootstrap_token": token})
        assert ex.status_code == 200

        # Verify consumed_at is now set
        conn = setup_server.db()
        row = conn.execute(
            "SELECT * FROM bootstrap_tokens WHERE token_hash = ?", (token_hash,)
        ).fetchone()
        conn.close()
        assert row["consumed_at"] is not None, "Token must be marked consumed in DB"


# ========= Login Rate Limiting Tests =========

@pytest.mark.anyio
async def test_login_rate_limit(setup_server):
    """Login attempts exceeding the per-IP limit must return 429."""
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        await _provision(c, "rl_login_user")

        # Clear prior rate limit state
        conn = setup_server.db()
        conn.execute("DELETE FROM rate_limit_events")
        conn.commit()
        conn.close()

        orig = setup_server._RATE_LIMIT_LOGIN
        setup_server._RATE_LIMIT_LOGIN = 3
        try:
            for i in range(3):
                resp = await c.post("/v1/app/auth/login", json={
                    "username": "rl_login_user", "password": "pass1234"
                })
                assert resp.status_code == 200, f"Login {i+1} should succeed"
            # 4th request should be rate-limited
            resp = await c.post("/v1/app/auth/login", json={
                "username": "rl_login_user", "password": "pass1234"
            })
            assert resp.status_code == 429
        finally:
            setup_server._RATE_LIMIT_LOGIN = orig
            conn = setup_server.db()
            conn.execute("DELETE FROM rate_limit_events")
            conn.commit()
            conn.close()


@pytest.mark.anyio
async def test_login_rate_limit_fires_before_credential_check(setup_server):
    """Rate limit must trigger BEFORE credential validation to prevent info leakage."""
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        conn = setup_server.db()
        conn.execute("DELETE FROM rate_limit_events")
        conn.commit()
        conn.close()

        orig = setup_server._RATE_LIMIT_LOGIN
        setup_server._RATE_LIMIT_LOGIN = 3
        try:
            # Exhaust rate limit with bad credentials
            for i in range(3):
                resp = await c.post("/v1/app/auth/login", json={
                    "username": f"nonexistent_{i}", "password": "wrong"
                })
                assert resp.status_code == 401

            # Next attempt should be 429, NOT 401 — proving rate limit fires first
            resp = await c.post("/v1/app/auth/login", json={
                "username": "doesnotexist", "password": "wrong"
            })
            assert resp.status_code == 429, \
                f"Expected 429 (rate limited), got {resp.status_code} — rate limit must fire before credential check"
        finally:
            setup_server._RATE_LIMIT_LOGIN = orig
            conn = setup_server.db()
            conn.execute("DELETE FROM rate_limit_events")
            conn.commit()
            conn.close()


@pytest.mark.anyio
async def test_login_rate_limit_response_has_no_credential_leak(setup_server):
    """429 response body must not leak username, password, or credential details."""
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        conn = setup_server.db()
        conn.execute("DELETE FROM rate_limit_events")
        conn.commit()
        conn.close()

        orig = setup_server._RATE_LIMIT_LOGIN
        setup_server._RATE_LIMIT_LOGIN = 1
        try:
            # First request uses up the limit
            await c.post("/v1/app/auth/login", json={
                "username": "secretuser", "password": "secretpass"
            })
            # Second triggers rate limit
            resp = await c.post("/v1/app/auth/login", json={
                "username": "secretuser", "password": "secretpass"
            })
            assert resp.status_code == 429
            body_text = resp.text.lower()
            assert "secretuser" not in body_text, "429 response must not leak username"
            assert "secretpass" not in body_text, "429 response must not leak password"
            assert "api_key" not in body_text, "429 response must not leak api_key"
        finally:
            setup_server._RATE_LIMIT_LOGIN = orig
            conn = setup_server.db()
            conn.execute("DELETE FROM rate_limit_events")
            conn.commit()
            conn.close()


# ── Account-level login lockout tests ──────────────────────────────────

@pytest.mark.anyio
async def test_login_lockout_after_n_failures(setup_server):
    """After N failed login attempts for the same username, account is locked (423)."""
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        await _provision(c, "lockout_user")

        conn = setup_server.db()
        conn.execute("DELETE FROM rate_limit_events")
        conn.execute("DELETE FROM login_failures")
        conn.commit()
        conn.close()

        orig_rl = setup_server._RATE_LIMIT_LOGIN
        orig_threshold = setup_server._LOGIN_LOCKOUT_THRESHOLD
        setup_server._RATE_LIMIT_LOGIN = 100  # disable IP rate limit for this test
        setup_server._LOGIN_LOCKOUT_THRESHOLD = 3
        try:
            # 3 bad password attempts
            for i in range(3):
                resp = await c.post("/v1/app/auth/login", json={
                    "username": "lockout_user", "password": "wrong"
                })
                assert resp.status_code == 401, f"Attempt {i+1} should be 401"

            # 4th attempt — even with CORRECT password — should be locked out
            resp = await c.post("/v1/app/auth/login", json={
                "username": "lockout_user", "password": "pass1234"
            })
            assert resp.status_code == 423, \
                f"Expected 423 (locked), got {resp.status_code}"
        finally:
            setup_server._RATE_LIMIT_LOGIN = orig_rl
            setup_server._LOGIN_LOCKOUT_THRESHOLD = orig_threshold
            conn = setup_server.db()
            conn.execute("DELETE FROM rate_limit_events")
            conn.execute("DELETE FROM login_failures")
            conn.commit()
            conn.close()


@pytest.mark.anyio
async def test_login_lockout_expires(setup_server):
    """Lockout should expire after the lockout duration passes."""
    import time as _time
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        await _provision(c, "lockout_expire")

        conn = setup_server.db()
        conn.execute("DELETE FROM rate_limit_events")
        conn.execute("DELETE FROM login_failures")
        conn.commit()
        conn.close()

        orig_rl = setup_server._RATE_LIMIT_LOGIN
        orig_threshold = setup_server._LOGIN_LOCKOUT_THRESHOLD
        orig_duration = setup_server._LOGIN_LOCKOUT_DURATION_S
        setup_server._RATE_LIMIT_LOGIN = 100
        setup_server._LOGIN_LOCKOUT_THRESHOLD = 2
        setup_server._LOGIN_LOCKOUT_DURATION_S = 1  # 1-second lockout for testing
        try:
            # 2 bad attempts to trigger lockout
            for i in range(2):
                await c.post("/v1/app/auth/login", json={
                    "username": "lockout_expire", "password": "wrong"
                })

            # Should be locked
            resp = await c.post("/v1/app/auth/login", json={
                "username": "lockout_expire", "password": "pass1234"
            })
            assert resp.status_code == 423

            # Wait for lockout to expire
            _time.sleep(1.2)

            # Should work again
            resp = await c.post("/v1/app/auth/login", json={
                "username": "lockout_expire", "password": "pass1234"
            })
            assert resp.status_code == 200, \
                f"Expected 200 after lockout expired, got {resp.status_code}"
        finally:
            setup_server._RATE_LIMIT_LOGIN = orig_rl
            setup_server._LOGIN_LOCKOUT_THRESHOLD = orig_threshold
            setup_server._LOGIN_LOCKOUT_DURATION_S = orig_duration
            conn = setup_server.db()
            conn.execute("DELETE FROM rate_limit_events")
            conn.execute("DELETE FROM login_failures")
            conn.commit()
            conn.close()


@pytest.mark.anyio
async def test_successful_login_clears_failures(setup_server):
    """A successful login must clear the failure count for that account."""
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        await _provision(c, "lockout_clear")

        conn = setup_server.db()
        conn.execute("DELETE FROM rate_limit_events")
        conn.execute("DELETE FROM login_failures")
        conn.commit()
        conn.close()

        orig_rl = setup_server._RATE_LIMIT_LOGIN
        orig_threshold = setup_server._LOGIN_LOCKOUT_THRESHOLD
        setup_server._RATE_LIMIT_LOGIN = 100
        setup_server._LOGIN_LOCKOUT_THRESHOLD = 5
        try:
            # 4 bad attempts (under threshold of 5)
            for i in range(4):
                await c.post("/v1/app/auth/login", json={
                    "username": "lockout_clear", "password": "wrong"
                })

            # Successful login should clear failures
            resp = await c.post("/v1/app/auth/login", json={
                "username": "lockout_clear", "password": "pass1234"
            })
            assert resp.status_code == 200

            # Verify failures were cleared
            conn = setup_server.db()
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM login_failures WHERE username = 'lockout_clear'"
            ).fetchone()
            conn.close()
            assert int(row["c"]) == 0, "Successful login must clear failure records"
        finally:
            setup_server._RATE_LIMIT_LOGIN = orig_rl
            setup_server._LOGIN_LOCKOUT_THRESHOLD = orig_threshold
            conn = setup_server.db()
            conn.execute("DELETE FROM rate_limit_events")
            conn.execute("DELETE FROM login_failures")
            conn.commit()
            conn.close()


@pytest.mark.anyio
async def test_login_lockout_no_cross_account_impact(setup_server):
    """Locking out user A must not affect user B."""
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        await _provision(c, "lockout_a")
        await _provision(c, "lockout_b")

        conn = setup_server.db()
        conn.execute("DELETE FROM rate_limit_events")
        conn.execute("DELETE FROM login_failures")
        conn.commit()
        conn.close()

        orig_rl = setup_server._RATE_LIMIT_LOGIN
        orig_threshold = setup_server._LOGIN_LOCKOUT_THRESHOLD
        setup_server._RATE_LIMIT_LOGIN = 100
        setup_server._LOGIN_LOCKOUT_THRESHOLD = 2
        try:
            # Lock out user A
            for i in range(2):
                await c.post("/v1/app/auth/login", json={
                    "username": "lockout_a", "password": "wrong"
                })
            resp_a = await c.post("/v1/app/auth/login", json={
                "username": "lockout_a", "password": "pass1234"
            })
            assert resp_a.status_code == 423, "User A should be locked"

            # User B should still work
            resp_b = await c.post("/v1/app/auth/login", json={
                "username": "lockout_b", "password": "pass1234"
            })
            assert resp_b.status_code == 200, \
                f"User B should not be affected, got {resp_b.status_code}"
        finally:
            setup_server._RATE_LIMIT_LOGIN = orig_rl
            setup_server._LOGIN_LOCKOUT_THRESHOLD = orig_threshold
            conn = setup_server.db()
            conn.execute("DELETE FROM rate_limit_events")
            conn.execute("DELETE FROM login_failures")
            conn.commit()
            conn.close()


@pytest.mark.anyio
async def test_login_lockout_response_no_credential_leak(setup_server):
    """423 lockout response must not expose username, password, or api_key."""
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        await _provision(c, "lockout_leak_check")

        conn = setup_server.db()
        conn.execute("DELETE FROM rate_limit_events")
        conn.execute("DELETE FROM login_failures")
        conn.commit()
        conn.close()

        orig_rl = setup_server._RATE_LIMIT_LOGIN
        orig_threshold = setup_server._LOGIN_LOCKOUT_THRESHOLD
        setup_server._RATE_LIMIT_LOGIN = 100
        setup_server._LOGIN_LOCKOUT_THRESHOLD = 2
        try:
            for i in range(2):
                await c.post("/v1/app/auth/login", json={
                    "username": "lockout_leak_check", "password": "wrong"
                })
            resp = await c.post("/v1/app/auth/login", json={
                "username": "lockout_leak_check", "password": "secretpass123"
            })
            assert resp.status_code == 423
            body = resp.text.lower()
            assert "lockout_leak_check" not in body, "423 must not leak username"
            assert "secretpass123" not in body, "423 must not leak password"
            assert "api_key" not in body, "423 must not leak api_key"
        finally:
            setup_server._RATE_LIMIT_LOGIN = orig_rl
            setup_server._LOGIN_LOCKOUT_THRESHOLD = orig_threshold
            conn = setup_server.db()
            conn.execute("DELETE FROM rate_limit_events")
            conn.execute("DELETE FROM login_failures")
            conn.commit()
            conn.close()


# ── Login failure logging + admin endpoint tests ───────────────────────

@pytest.mark.anyio
async def test_login_failure_emits_log(setup_server):
    """Failed login must emit a structured WARNING log with username, IP, reason (never password)."""
    import logging
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        await _provision(c, "log_user")

        conn = setup_server.db()
        conn.execute("DELETE FROM rate_limit_events")
        conn.execute("DELETE FROM login_failures")
        conn.commit()
        conn.close()

        orig_rl = setup_server._RATE_LIMIT_LOGIN
        setup_server._RATE_LIMIT_LOGIN = 100
        captured = []
        handler = logging.Handler()
        handler.emit = lambda record: captured.append(record)
        auth_logger = logging.getLogger("auth")
        auth_logger.addHandler(handler)
        auth_logger.setLevel(logging.DEBUG)
        try:
            await c.post("/v1/app/auth/login", json={
                "username": "log_user", "password": "wrongpass"
            })
            # Find failure log
            failure_logs = [r for r in captured if r.getMessage() == "login_failure"]
            assert len(failure_logs) >= 1, "Must emit login_failure log"
            rec = failure_logs[0]
            assert rec.username == "log_user"
            assert rec.reason == "wrong_password"
            assert rec.client_ip
            assert rec.levelno == logging.WARNING

            # Verify no password in log output
            fmt = logging.Formatter("%(message)s %(username)s %(reason)s")
            log_text = fmt.format(rec)
            assert "wrongpass" not in log_text, "Log must never contain password"
        finally:
            auth_logger.removeHandler(handler)
            setup_server._RATE_LIMIT_LOGIN = orig_rl
            conn = setup_server.db()
            conn.execute("DELETE FROM rate_limit_events")
            conn.execute("DELETE FROM login_failures")
            conn.commit()
            conn.close()


@pytest.mark.anyio
async def test_login_success_emits_log(setup_server):
    """Successful login must emit an INFO log."""
    import logging
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        await _provision(c, "log_success_user")

        conn = setup_server.db()
        conn.execute("DELETE FROM rate_limit_events")
        conn.execute("DELETE FROM login_failures")
        conn.commit()
        conn.close()

        captured = []
        handler = logging.Handler()
        handler.emit = lambda record: captured.append(record)
        auth_logger = logging.getLogger("auth")
        auth_logger.addHandler(handler)
        auth_logger.setLevel(logging.DEBUG)
        try:
            resp = await c.post("/v1/app/auth/login", json={
                "username": "log_success_user", "password": "pass1234"
            })
            assert resp.status_code == 200
            success_logs = [r for r in captured if r.getMessage() == "login_success"]
            assert len(success_logs) >= 1, "Must emit login_success log"
            rec = success_logs[0]
            assert rec.username == "log_success_user"
            assert rec.levelno == logging.INFO
        finally:
            auth_logger.removeHandler(handler)
            conn = setup_server.db()
            conn.execute("DELETE FROM rate_limit_events")
            conn.execute("DELETE FROM login_failures")
            conn.commit()
            conn.close()


@pytest.mark.anyio
async def test_admin_login_failures_endpoint(setup_server):
    """Admin endpoint returns recent login failures, gated by admin token."""
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        await _provision(c, "admin_audit_user")

        conn = setup_server.db()
        conn.execute("DELETE FROM rate_limit_events")
        conn.execute("DELETE FROM login_failures")
        conn.commit()
        conn.close()

        orig_rl = setup_server._RATE_LIMIT_LOGIN
        setup_server._RATE_LIMIT_LOGIN = 100
        try:
            # Create some failures
            for i in range(3):
                await c.post("/v1/app/auth/login", json={
                    "username": "admin_audit_user", "password": "wrong"
                })

            # Without admin token → 401
            resp = await c.get("/v1/app/admin/login-failures")
            assert resp.status_code == 401

            # With admin token → 200
            resp = await c.get("/v1/app/admin/login-failures", headers=ADMIN_HEADERS)
            assert resp.status_code == 200
            data = resp.json()
            assert data["count"] >= 3
            assert len(data["failures"]) >= 3
            # Verify structure
            entry = data["failures"][0]
            assert "username" in entry
            assert "client_ip" in entry
            assert "ts" in entry
            # Verify no password in response
            resp_text = resp.text.lower()
            assert "password" not in resp_text
            assert "wrong" not in resp_text
        finally:
            setup_server._RATE_LIMIT_LOGIN = orig_rl
            conn = setup_server.db()
            conn.execute("DELETE FROM rate_limit_events")
            conn.execute("DELETE FROM login_failures")
            conn.commit()
            conn.close()


@pytest.mark.anyio
async def test_admin_login_failures_summary_and_alert_level(setup_server):
    """Admin endpoint includes summary statistics and alert level based on failure count."""
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        await _provision(c, "summary_user_a")
        await _provision(c, "summary_user_b")

        conn = setup_server.db()
        conn.execute("DELETE FROM rate_limit_events")
        conn.execute("DELETE FROM login_failures")
        conn.commit()
        conn.close()

        orig_rl = setup_server._RATE_LIMIT_LOGIN
        orig_lockout = setup_server._LOGIN_LOCKOUT_THRESHOLD
        setup_server._RATE_LIMIT_LOGIN = 200
        setup_server._LOGIN_LOCKOUT_THRESHOLD = 3  # lower for test
        try:
            # Create failures from two users — 3 for user_a (triggers lockout), 2 for user_b
            for _ in range(3):
                await c.post("/v1/app/auth/login", json={
                    "username": "summary_user_a", "password": "wrong"
                })
            for _ in range(2):
                await c.post("/v1/app/auth/login", json={
                    "username": "summary_user_b", "password": "wrong"
                })

            resp = await c.get("/v1/app/admin/login-failures", headers=ADMIN_HEADERS)
            assert resp.status_code == 200
            data = resp.json()

            # Verify summary presence and structure
            assert "summary" in data
            s = data["summary"]
            assert s["total_failures"] >= 5
            assert s["unique_ips"] >= 1
            assert s["unique_usernames"] >= 2
            assert isinstance(s["locked_accounts"], list)
            # summary_user_a hit lockout threshold (3), summary_user_b did not (2 < 3)
            assert "summary_user_a" in s["locked_accounts"]
            assert "summary_user_b" not in s["locked_accounts"]
            # Alert level: 5 failures → "normal" (<10 threshold)
            assert s["alert_level"] == "normal"
        finally:
            setup_server._RATE_LIMIT_LOGIN = orig_rl
            setup_server._LOGIN_LOCKOUT_THRESHOLD = orig_lockout
            conn = setup_server.db()
            conn.execute("DELETE FROM rate_limit_events")
            conn.execute("DELETE FROM login_failures")
            conn.commit()
            conn.close()


@pytest.mark.anyio
async def test_admin_alert_level_elevated(setup_server):
    """Admin endpoint returns elevated alert level when 10+ failures in window."""
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        await _provision(c, "alert_level_user")

        conn = setup_server.db()
        conn.execute("DELETE FROM rate_limit_events")
        conn.execute("DELETE FROM login_failures")
        conn.commit()
        conn.close()

        orig_rl = setup_server._RATE_LIMIT_LOGIN
        orig_lockout = setup_server._LOGIN_LOCKOUT_THRESHOLD
        setup_server._RATE_LIMIT_LOGIN = 200
        setup_server._LOGIN_LOCKOUT_THRESHOLD = 200  # disable lockout for this test
        try:
            # Insert 12 failures to trigger elevated level
            conn = setup_server.db()
            now_ts = __import__("datetime").datetime.now().timestamp()
            for i in range(12):
                conn.execute(
                    "INSERT INTO login_failures (username, client_ip, ts) VALUES (?, ?, ?)",
                    (f"target_user_{i % 3}", f"10.0.0.{i % 4}", now_ts - i),
                )
            conn.commit()
            conn.close()

            resp = await c.get("/v1/app/admin/login-failures", headers=ADMIN_HEADERS)
            assert resp.status_code == 200
            data = resp.json()
            s = data["summary"]
            assert s["alert_level"] == "elevated"
            assert s["unique_ips"] >= 3  # 10.0.0.0 through 10.0.0.3
            assert s["unique_usernames"] >= 3
        finally:
            setup_server._RATE_LIMIT_LOGIN = orig_rl
            setup_server._LOGIN_LOCKOUT_THRESHOLD = orig_lockout
            conn = setup_server.db()
            conn.execute("DELETE FROM rate_limit_events")
            conn.execute("DELETE FROM login_failures")
            conn.commit()
            conn.close()


@pytest.mark.anyio
async def test_login_returns_all_students_for_multi_student_account(setup_server):
    """Login response includes students array with all students when account has >1 student."""
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        api_key, student_id = await _provision(c, "multi_student_user")

        # Add a second student to the same account
        conn = setup_server.db()
        row = conn.execute("SELECT account_id FROM students WHERE id = ?", (student_id,)).fetchone()
        account_id = int(row["account_id"])
        conn.execute(
            "INSERT INTO students(account_id, display_name, grade, created_at) VALUES(?,?,?,?)",
            (account_id, "小花", "G4", "2026-01-01T00:00:00"),
        )
        conn.commit()
        conn.close()

        resp = await c.post("/v1/app/auth/login", json={
            "username": "multi_student_user", "password": "pass1234"
        })
        assert resp.status_code == 200
        body = resp.json()

        # Must have students array with 2 entries
        assert "students" in body, "login response must include students array"
        assert len(body["students"]) == 2, f"expected 2 students, got {len(body['students'])}"

        # Each student must have id, display_name, grade
        for st in body["students"]:
            assert "id" in st
            assert "display_name" in st
            assert "grade" in st

        # default_student still present for backward compat
        assert "default_student" in body
        assert body["default_student"]["id"] == body["students"][0]["id"]

        # Second student is the newly added one
        names = [s["display_name"] for s in body["students"]]
        assert "小花" in names, "second student not found in students array"


@pytest.mark.anyio
async def test_login_single_student_returns_students_array_with_one(setup_server):
    """Login response includes students array with 1 entry for single-student accounts."""
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        await _provision(c, "single_student_user")
        resp = await c.post("/v1/app/auth/login", json={
            "username": "single_student_user", "password": "pass1234"
        })
        assert resp.status_code == 200
        body = resp.json()

        assert "students" in body
        assert len(body["students"]) == 1
        assert body["students"][0]["id"] == body["default_student"]["id"]


@pytest.mark.anyio
async def test_healthz_returns_ok(setup_server):
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        resp = await c.get("/healthz")
        assert resp.status_code == 200
        body = resp.json()
        assert body == {"status": "ok"}


# ── Admin password reset tests ──────────────────────────────────────────

@pytest.mark.anyio
async def test_admin_reset_password_no_token(setup_server):
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        resp = await c.post("/v1/app/admin/reset-password", json={"username": "nouser"})
        assert resp.status_code == 401


@pytest.mark.anyio
async def test_admin_reset_password_unknown_user(setup_server):
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        resp = await c.post("/v1/app/admin/reset-password",
                            json={"username": "nonexistent_user"},
                            headers=ADMIN_HEADERS)
        assert resp.status_code == 404


@pytest.mark.anyio
async def test_admin_reset_password_happy_path(setup_server):
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        await _provision(c, "reset_target")

        # Reset password
        resp = await c.post("/v1/app/admin/reset-password",
                            json={"username": "reset_target"},
                            headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["username"] == "reset_target"
        temp_pw = body["temp_password"]
        assert len(temp_pw) >= 8

        # Login with temp password should succeed
        login_resp = await c.post("/v1/app/auth/login", json={
            "username": "reset_target", "password": temp_pw
        })
        assert login_resp.status_code == 200

        # Old password should fail
        old_resp = await c.post("/v1/app/auth/login", json={
            "username": "reset_target", "password": "pass1234"
        })
        assert old_resp.status_code == 401


@pytest.mark.anyio
async def test_admin_reset_password_clears_failures(setup_server):
    transport = httpx.ASGITransport(app=setup_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        await _provision(c, "lockout_user")

        # Generate login failures
        for _ in range(3):
            await c.post("/v1/app/auth/login", json={
                "username": "lockout_user", "password": "wrong"
            })

        # Check failures exist
        fail_resp = await c.get("/v1/app/admin/login-failures",
                                params={"minutes": 5},
                                headers=ADMIN_HEADERS)
        failures_before = [f for f in fail_resp.json()["failures"] if f["username"] == "lockout_user"]
        assert len(failures_before) >= 3

        # Reset password clears failures
        await c.post("/v1/app/admin/reset-password",
                     json={"username": "lockout_user"},
                     headers=ADMIN_HEADERS)

        # Failures should be cleared
        fail_resp2 = await c.get("/v1/app/admin/login-failures",
                                 params={"minutes": 5},
                                 headers=ADMIN_HEADERS)
        failures_after = [f for f in fail_resp2.json()["failures"] if f["username"] == "lockout_user"]
        assert len(failures_after) == 0
