import importlib
import os

import httpx
import pytest


@pytest.fixture
def setup_teacher_server(tmp_path):
    db_path = tmp_path / "teacher_class_test.db"
    os.environ["DB_PATH"] = str(db_path)
    os.environ["APP_PROVISION_ADMIN_TOKEN"] = "test-admin-token"
    import server
    importlib.reload(server)
    return server


ADMIN_HEADERS = {"X-Admin-Token": "test-admin-token"}


async def _provision(client, username):
    resp = await client.post(
        "/v1/app/auth/provision",
        json={"username": username, "password": "pass1234", "plan": "school"},
        headers=ADMIN_HEADERS,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    return body["api_key"], body["default_student_id"]


@pytest.mark.anyio
async def test_teacher_create_class_add_student_and_report(setup_teacher_server):
    transport = httpx.ASGITransport(app=setup_teacher_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        api_key, _ = await _provision(client, "teacher_a")
        headers = {"X-API-Key": api_key}

        create_resp = await client.post(
            "/v1/teacher/classes",
            json={"class_name": "Class 5A", "grade": 5, "school_name": "North School", "school_code": "NS-01"},
            headers=headers,
        )
        assert create_resp.status_code == 200, create_resp.text
        class_id = create_resp.json()["class"]["id"]

        add_resp = await client.post(
            f"/v1/teacher/classes/{class_id}/students",
            json={"display_name": "Alice", "grade": "G5"},
            headers=headers,
        )
        assert add_resp.status_code == 200, add_resp.text

        report_resp = await client.get(f"/v1/teacher/classes/{class_id}/report", headers=headers)
        assert report_resp.status_code == 200, report_resp.text
        report = report_resp.json()
        assert report["summary"]["student_count"] >= 1
        assert report["class"]["id"] == class_id


@pytest.mark.anyio
async def test_teacher_cannot_read_other_teacher_class(setup_teacher_server):
    transport = httpx.ASGITransport(app=setup_teacher_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        api_key_1, _ = await _provision(client, "teacher_scope_1")
        api_key_2, _ = await _provision(client, "teacher_scope_2")

        create_resp = await client.post(
            "/v1/teacher/classes",
            json={"class_name": "Class 5A", "grade": 5, "school_name": "North School", "school_code": "NS-01"},
            headers={"X-API-Key": api_key_1},
        )
        class_id = create_resp.json()["class"]["id"]

        forbidden = await client.get(f"/v1/teacher/classes/{class_id}/report", headers={"X-API-Key": api_key_2})
        assert forbidden.status_code in (403, 404)


@pytest.mark.anyio
async def test_teacher_concept_report_includes_hint_evidence_blocks(setup_teacher_server):
    transport = httpx.ASGITransport(app=setup_teacher_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        api_key, _ = await _provision(client, "teacher_hint_block")
        headers = {"X-API-Key": api_key}

        create_resp = await client.post(
            "/v1/teacher/classes",
            json={"class_name": "Class 5B", "grade": 5, "school_name": "North School", "school_code": "NS-02"},
            headers=headers,
        )
        assert create_resp.status_code == 200, create_resp.text
        class_id = create_resp.json()["class"]["id"]

        add_resp = await client.post(
            f"/v1/teacher/classes/{class_id}/students",
            json={"display_name": "Bob", "grade": "G5"},
            headers=headers,
        )
        assert add_resp.status_code == 200, add_resp.text
        student_id = add_resp.json()["student"]["id"]

        question_resp = await client.post(
            "/v1/questions/next",
            params={"student_id": student_id},
            headers=headers,
        )
        assert question_resp.status_code == 200, question_resp.text
        qdata = question_resp.json()

        submit_resp = await client.post(
            "/v1/answers/submit",
            headers=headers,
            json={
                "student_id": student_id,
                "question_id": qdata["question_id"],
                "user_answer": "wrong",
                "hint_level_used": 1,
                "meta": {
                    "hint_sequence": [1],
                    "hint_open_ts": [1000, 2000],
                },
            },
        )
        assert submit_resp.status_code == 200, submit_resp.text

        report_resp = await client.get(
            f"/v1/teacher/classes/{class_id}/concept-report",
            headers=headers,
        )
        assert report_resp.status_code == 200, report_resp.text
        data = report_resp.json()

        assert "hint_summary" in data
        assert "one_page_summary" in data
        overview = data["hint_summary"]["overview"]
        assert "hint_sequence_coverage_rate_pct" in overview
        assert "hint_open_ts_coverage_rate_pct" in overview
        assert "evidence_chain_complete_rate_pct" in overview
        assert "avg_hints_before_success" in overview
        assert "hint_escalation_rate_pct" in overview
        assert "by_submit_level" in data["hint_summary"]
        assert "hint_decision_block" in data["one_page_summary"]
        assert isinstance(data["one_page_summary"]["hint_decision_block"], list)