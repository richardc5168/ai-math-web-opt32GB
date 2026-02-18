import importlib
import os

import httpx
import pytest


def _make_client(tmp_path):
    os.environ["DB_PATH"] = str(tmp_path / "test_app.db")

    import server

    importlib.reload(server)
    transport = httpx.ASGITransport(app=server.app)
    return transport


@pytest.mark.anyio
async def test_hints_next_returns_ratio_reverse_ladder_schema(tmp_path):
    transport = _make_client(tmp_path)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/admin/bootstrap", params={"name": "Pytest"})
        assert r.status_code == 200
        api_key = r.json()["api_key"]
        headers = {"X-API-Key": api_key}

        payload = {
            "question_data": {
                "topic": "分數應用題(五年級)",
                "question": "走完全程需要多少小時？若走了全程的 2/3 時，用了 7/8 小時。",
            },
            "student_state": "先設 T",
            "level": 2,
        }

        r = await client.post("/v1/hints/next", headers=headers, json=payload)
        assert r.status_code == 200
        data = r.json()

        assert isinstance(data.get("hint"), str) and data["hint"]
        assert isinstance(data.get("level"), int)
        assert isinstance(data.get("mode"), str) and data.get("mode") != "fallback"

        ladder = data.get("hint_ladder")
        current = data.get("current_step")

        assert isinstance(ladder, list)
        assert len(ladder) == 7
        assert isinstance(current, dict)

        for key in ("title", "prompt", "expected_answer", "explanation", "formula"):
            assert key in current
