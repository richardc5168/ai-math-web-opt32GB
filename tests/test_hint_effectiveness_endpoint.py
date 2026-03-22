"""Tests for EXP-A2: /v1/student/hint-effectiveness API endpoint.

Verifies that hint effectiveness analytics can be read via GET request
using the existing learning analytics pipeline.
"""

from __future__ import annotations

import importlib
import os

import httpx
import pytest


def _make_client(tmp_path):
    os.environ["DB_PATH"] = str(tmp_path / "test_app.db")
    os.environ.pop("EXTERNAL_WEB_QUESTION_BANK", None)

    import engine
    import server

    importlib.reload(engine)
    importlib.reload(server)
    return httpx.ASGITransport(app=server.app)


async def _bootstrap(client):
    """Provision an account and return (api_key, student_id)."""
    resp = await client.post("/admin/bootstrap", params={"name": "HintTest"})
    assert resp.status_code == 200
    api_key = resp.json()["api_key"]

    resp = await client.get("/v1/students", headers={"X-API-Key": api_key})
    assert resp.status_code == 200
    student_id = resp.json()["students"][0]["id"]
    return api_key, student_id


@pytest.mark.anyio
async def test_hint_effectiveness_empty(tmp_path):
    """Endpoint returns zeroed stats when no attempts exist."""
    transport = _make_client(tmp_path)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        api_key, student_id = await _bootstrap(client)
        headers = {"X-API-Key": api_key}

        resp = await client.get(
            "/v1/student/hint-effectiveness",
            params={"student_id": student_id},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["total_hinted_attempts"] == 0
        assert data["hint_success_rate"] == 0.0


@pytest.mark.anyio
async def test_hint_effectiveness_after_hinted_attempt(tmp_path):
    """After a hinted attempt, stats reflect the outcome."""
    transport = _make_client(tmp_path)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        api_key, student_id = await _bootstrap(client)
        headers = {"X-API-Key": api_key}

        # Get a question first
        resp = await client.post(
            "/v1/questions/next",
            params={"student_id": student_id},
            headers=headers,
        )
        assert resp.status_code == 200
        qdata = resp.json()
        question_id = qdata["question_id"]

        # Request a hint (level 1)
        resp = await client.post(
            "/v1/questions/hint",
            headers=headers,
            json={"question_id": question_id, "level": 1},
        )
        assert resp.status_code == 200

        # Submit correct answer
        resp = await client.post(
            "/v1/answers/submit",
            headers=headers,
            json={
                "student_id": student_id,
                "question_id": question_id,
                "answer": str(qdata.get("answer", "0")),
            },
        )
        assert resp.status_code == 200

        # Check hint effectiveness
        resp = await client.get(
            "/v1/student/hint-effectiveness",
            params={"student_id": student_id},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "hint_success_rate" in data
        assert "stuck_after_hint_rate" in data
        assert "by_level" in data
        assert "by_concept" in data
        assert "generated_at" in data


@pytest.mark.anyio
async def test_hint_effectiveness_class_wide(tmp_path):
    """No student_id returns class-wide stats."""
    transport = _make_client(tmp_path)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        api_key, _ = await _bootstrap(client)
        headers = {"X-API-Key": api_key}

        resp = await client.get(
            "/v1/student/hint-effectiveness",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["total_hinted_attempts"] == 0


@pytest.mark.anyio
async def test_hint_effectiveness_bad_student(tmp_path):
    """Invalid student_id returns 404."""
    transport = _make_client(tmp_path)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        api_key, _ = await _bootstrap(client)
        headers = {"X-API-Key": api_key}

        resp = await client.get(
            "/v1/student/hint-effectiveness",
            params={"student_id": 99999},
            headers=headers,
        )
        assert resp.status_code == 404


@pytest.mark.anyio
async def test_hint_effectiveness_no_auth(tmp_path):
    """Missing API key returns 422."""
    transport = _make_client(tmp_path)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/v1/student/hint-effectiveness")
        assert resp.status_code == 422
