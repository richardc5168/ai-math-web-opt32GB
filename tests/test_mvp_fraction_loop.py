import importlib
import os

import httpx
import pytest


def _make_client(tmp_path):
    # Use a temp DB so tests are isolated.
    os.environ["DB_PATH"] = str(tmp_path / "test_app.db")

    import server

    importlib.reload(server)

    transport = httpx.ASGITransport(app=server.app)
    return transport


@pytest.mark.anyio
async def test_fraction_mvp_loop(tmp_path):
    transport = _make_client(tmp_path)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # bootstrap
        r = await client.post("/admin/bootstrap", params={"name": "Pytest"})
        assert r.status_code == 200
        api_key = r.json()["api_key"]

        headers = {"X-API-Key": api_key}

        # health
        r = await client.get("/health")
        assert r.status_code == 200
        assert r.json().get("ok") is True

        # get student_id
        r = await client.get("/v1/students", headers=headers)
        assert r.status_code == 200
        students = r.json()["students"]
        assert len(students) >= 1
        student_id = students[0]["id"]

        # next question (force fraction commondenom)
        r = await client.post(
            "/v1/questions/next", params={"student_id": student_id, "topic_key": "2"}, headers=headers
        )
        assert r.status_code == 200
        data = r.json()
        assert "question_id" in data
        assert "hints" in data
        assert "policy" in data
        assert "correct_answer" not in data
        qid = data["question_id"]

        # hint endpoint
        r = await client.post("/v1/questions/hint", headers=headers, json={"question_id": qid, "level": 1})
        assert r.status_code == 200
        assert r.json().get("hint")

        # submit wrong answer
        r = await client.post(
            "/v1/answers/submit",
            headers=headers,
            json={
                "student_id": student_id,
                "question_id": qid,
                "user_answer": "1 1 1",
                "time_spent_sec": 12,
                "hint_level_used": 1,
            },
        )
        assert r.status_code == 200
        j = r.json()
        assert j.get("error_tag")

        # parent weekly report
        r = await client.get(
            "/v1/reports/parent_weekly", headers=headers, params={"student_id": student_id, "days": 7}
        )
        assert r.status_code == 200
        report = r.json()
        assert "weakness_top3" in report
        assert "next_week_plan" in report
        assert isinstance(report["next_week_plan"], list)
        assert len(report["next_week_plan"]) == 7
