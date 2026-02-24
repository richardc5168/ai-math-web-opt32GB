import importlib
import os

import httpx
import pytest


def _make_client(tmp_path):
    os.environ["DB_PATH"] = str(tmp_path / "test_app.db")
    os.environ["EXTERNAL_WEB_FRACTION_DECIMAL"] = "1"

    import server

    importlib.reload(server)
    transport = httpx.ASGITransport(app=server.app)
    return transport


@pytest.mark.anyio
async def test_fraction_decimal_application_web_loop(tmp_path):
    transport = _make_client(tmp_path)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/admin/bootstrap", params={"name": "Pytest"})
        assert response.status_code == 200
        api_key = response.json()["api_key"]

        headers = {"X-API-Key": api_key}

        response = await client.get("/v1/students", headers=headers)
        assert response.status_code == 200
        student_id = response.json()["students"][0]["id"]

        response = await client.post(
            "/v1/questions/next",
            params={"student_id": student_id, "topic_key": "fraction_decimal_application_web_v1"},
            headers=headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert data.get("question_id")
        assert data.get("question")
        assert data.get("hints")
        assert data.get("topic") == "fraction_decimal_application_web_v1"
        question_id = data["question_id"]

        response = await client.post(
            "/v1/questions/hint",
            headers=headers,
            json={"question_id": question_id, "level": 3},
        )
        assert response.status_code == 200
        assert response.json().get("hint")

        response = await client.post(
            "/v1/answers/submit",
            headers=headers,
            json={
                "student_id": student_id,
                "question_id": question_id,
                "user_answer": "1/2",
                "time_spent_sec": 5,
            },
        )
        assert response.status_code == 200
        result = response.json()
        assert "is_correct" in result
        assert "correct_answer" in result
