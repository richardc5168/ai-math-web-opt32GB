"""
R56: Cross-device student-parent data flow verification.

Scenario: Student on Computer A does practice → data auto-syncs to cloud
          → Parent on Computer B enters same name+PIN → sees same records.

Tests cover:
1. Upsert with full report_data → fetch returns identical data
2. Multiple upserts (incremental sync) → fetch returns latest
3. Name normalization (case-insensitive matching)
4. Wrong PIN → 403
5. Unknown student → 404
6. Practice events accumulate across upserts
7. Report freshness (cloud_ts updates on each upsert)
8. Concurrent students don't leak data
9. Unicode student names work
10. Large report payload round-trips correctly
"""

import importlib
import os
import time

import httpx
import pytest


def _make_report_data(name, total=10, correct=8, wrong_items=None, attempts=None):
    """Build a realistic report_data payload matching the JS buildReportData format."""
    accuracy = round(correct / total * 100) if total else 0
    return {
        "v": 1,
        "name": name,
        "ts": int(time.time() * 1000),
        "days": 7,
        "d": {
            "total": total,
            "correct": correct,
            "incorrect": total - correct,
            "accuracy": accuracy,
            "avgMs": 5200,
            "hintDist": [correct, 1, 1, total - correct - 2] if total > 2 else [total, 0, 0, 0],
            "weak": wrong_items or [
                {"t": "fraction-word-g5", "k": "add_fraction", "w": 2, "n": 5, "h2": 1, "h3": 1}
            ],
            "wrong": [
                {
                    "ts": int(time.time() * 1000) - 60000,
                    "q": "1/3 + 1/4 = ?",
                    "sa": "2/7",
                    "ca": "7/12",
                    "t": "fraction-word-g5",
                    "k": "add_fraction",
                    "et": "denom_add",
                    "ed": "分母直接相加",
                }
            ],
            "daily": {"2025-01-15": {"n": total, "ok": correct}},
            "modules": [
                {"m": "fraction-word-g5", "n": total, "ok": correct, "acc": accuracy}
            ],
            "h24": {
                "total": 3,
                "correct": 2,
                "accuracy": 67,
                "avgMs": 4000,
                "hintDist": [2, 0, 0, 1],
                "modules": [
                    {"m": "fraction-word-g5", "n": 3, "ok": 2, "acc": 67}
                ],
            },
        },
        "_attempts": attempts or [],
    }


@pytest.fixture
async def client(tmp_path):
    db_path = tmp_path / "test_cross_device.db"
    os.environ["DB_PATH"] = str(db_path)
    import server
    importlib.reload(server)
    transport = httpx.ASGITransport(app=server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


@pytest.mark.anyio
async def test_full_round_trip(client):
    """Student upserts on device A, parent fetches on device B — same data."""
    report = _make_report_data("小明", total=15, correct=12)

    resp = await client.post(
        "/v1/parent-report/registry/upsert",
        json={"name": "小明", "pin": "1234", "report_data": report},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    fetch = await client.post(
        "/v1/parent-report/registry/fetch",
        json={"name": "小明", "pin": "1234"},
    )
    assert fetch.status_code == 200
    body = fetch.json()
    assert body["ok"] is True
    entry = body["entry"]
    assert entry["name"] == "小明"
    assert entry["data"]["d"]["total"] == 15
    assert entry["data"]["d"]["correct"] == 12
    assert entry["data"]["d"]["accuracy"] == 80
    assert len(entry["data"]["d"]["wrong"]) == 1
    assert entry["data"]["d"]["wrong"][0]["q"] == "1/3 + 1/4 = ?"
    assert entry["cloud_ts"] > 0


@pytest.mark.anyio
async def test_incremental_sync_updates(client):
    """Later upserts overwrite report — parent always sees latest."""
    report1 = _make_report_data("小明", total=5, correct=3)
    await client.post(
        "/v1/parent-report/registry/upsert",
        json={"name": "小明", "pin": "5678", "report_data": report1},
    )

    report2 = _make_report_data("小明", total=20, correct=18)
    resp2 = await client.post(
        "/v1/parent-report/registry/upsert",
        json={"name": "小明", "pin": "5678", "report_data": report2},
    )
    assert resp2.status_code == 200

    fetch = await client.post(
        "/v1/parent-report/registry/fetch",
        json={"name": "小明", "pin": "5678"},
    )
    entry = fetch.json()["entry"]
    assert entry["data"]["d"]["total"] == 20
    assert entry["data"]["d"]["correct"] == 18


@pytest.mark.anyio
async def test_name_case_insensitive(client):
    """Name matching is case-insensitive for English names."""
    report = _make_report_data("Kai", total=8, correct=6)
    await client.post(
        "/v1/parent-report/registry/upsert",
        json={"name": "Kai", "pin": "1111", "report_data": report},
    )

    fetch = await client.post(
        "/v1/parent-report/registry/fetch",
        json={"name": "kai", "pin": "1111"},
    )
    assert fetch.status_code == 200
    assert fetch.json()["entry"]["data"]["d"]["total"] == 8

    fetch2 = await client.post(
        "/v1/parent-report/registry/fetch",
        json={"name": "KAI", "pin": "1111"},
    )
    assert fetch2.status_code == 200
    assert fetch2.json()["entry"]["data"]["d"]["total"] == 8


@pytest.mark.anyio
async def test_wrong_pin_rejected(client):
    """Parent with wrong PIN cannot access student data."""
    report = _make_report_data("小花")
    await client.post(
        "/v1/parent-report/registry/upsert",
        json={"name": "小花", "pin": "1234", "report_data": report},
    )

    fetch = await client.post(
        "/v1/parent-report/registry/fetch",
        json={"name": "小花", "pin": "9999"},
    )
    assert fetch.status_code == 403


@pytest.mark.anyio
async def test_unknown_student_404(client):
    """Fetching a non-existent student returns 404."""
    fetch = await client.post(
        "/v1/parent-report/registry/fetch",
        json={"name": "不存在的學生", "pin": "1234"},
    )
    assert fetch.status_code == 404


@pytest.mark.anyio
async def test_practice_events_accumulate(client):
    """Practice events from separate upserts accumulate."""
    report = _make_report_data("小明")
    await client.post(
        "/v1/parent-report/registry/upsert",
        json={"name": "小明", "pin": "2222", "report_data": report},
    )

    for i in range(3):
        await client.post(
            "/v1/parent-report/registry/upsert",
            json={
                "name": "小明",
                "pin": "2222",
                "practice_event": {
                    "ts": 1700000000000 + i * 1000,
                    "score": i + 1,
                    "total": 3,
                    "topic": "fraction-word-g5",
                    "kind": "add_fraction",
                    "mode": "quiz3",
                    "completed": True,
                },
            },
        )

    fetch = await client.post(
        "/v1/parent-report/registry/fetch",
        json={"name": "小明", "pin": "2222"},
    )
    events = fetch.json()["entry"]["data"]["d"]["practice"]["events"]
    assert len(events) == 3
    assert events[0]["score"] == 1
    assert events[2]["score"] == 3


@pytest.mark.anyio
async def test_cloud_ts_freshness(client):
    """cloud_ts updates on each upsert so parent knows data freshness."""
    report = _make_report_data("小明")
    r1 = await client.post(
        "/v1/parent-report/registry/upsert",
        json={"name": "小明", "pin": "3333", "report_data": report},
    )
    ts1 = r1.json()["cloud_ts"]

    report2 = _make_report_data("小明", total=20, correct=15)
    r2 = await client.post(
        "/v1/parent-report/registry/upsert",
        json={"name": "小明", "pin": "3333", "report_data": report2},
    )
    ts2 = r2.json()["cloud_ts"]
    assert ts2 >= ts1

    fetch = await client.post(
        "/v1/parent-report/registry/fetch",
        json={"name": "小明", "pin": "3333"},
    )
    assert fetch.json()["entry"]["cloud_ts"] == ts2


@pytest.mark.anyio
async def test_students_dont_leak_data(client):
    """Two different students with different PINs — no data leakage."""
    report_a = _make_report_data("小明", total=10, correct=8)
    report_b = _make_report_data("小花", total=5, correct=2)

    await client.post(
        "/v1/parent-report/registry/upsert",
        json={"name": "小明", "pin": "1111", "report_data": report_a},
    )
    await client.post(
        "/v1/parent-report/registry/upsert",
        json={"name": "小花", "pin": "2222", "report_data": report_b},
    )

    fetch_a = await client.post(
        "/v1/parent-report/registry/fetch",
        json={"name": "小明", "pin": "1111"},
    )
    assert fetch_a.json()["entry"]["data"]["d"]["total"] == 10

    fetch_b = await client.post(
        "/v1/parent-report/registry/fetch",
        json={"name": "小花", "pin": "2222"},
    )
    assert fetch_b.json()["entry"]["data"]["d"]["total"] == 5

    cross = await client.post(
        "/v1/parent-report/registry/fetch",
        json={"name": "小明", "pin": "2222"},
    )
    assert cross.status_code == 403


@pytest.mark.anyio
async def test_unicode_names(client):
    """Full unicode student names round-trip correctly."""
    report = _make_report_data("大寶貝🌟")
    await client.post(
        "/v1/parent-report/registry/upsert",
        json={"name": "大寶貝🌟", "pin": "4444", "report_data": report},
    )

    fetch = await client.post(
        "/v1/parent-report/registry/fetch",
        json={"name": "大寶貝🌟", "pin": "4444"},
    )
    assert fetch.status_code == 200
    assert fetch.json()["entry"]["name"] == "大寶貝🌟"


@pytest.mark.anyio
async def test_large_payload_round_trip(client):
    """A report with many attempts round-trips without data loss."""
    attempts = []
    for i in range(200):
        attempts.append({
            "ts": 1700000000000 + i * 60000,
            "correct": i % 3 != 0,
            "topic": "unit-conversion-g5",
            "kind": "length",
            "hint_level": i % 4,
        })
    report = _make_report_data("小明", total=200, correct=134, attempts=attempts)

    await client.post(
        "/v1/parent-report/registry/upsert",
        json={"name": "小明", "pin": "5555", "report_data": report},
    )

    fetch = await client.post(
        "/v1/parent-report/registry/fetch",
        json={"name": "小明", "pin": "5555"},
    )
    data = fetch.json()["entry"]["data"]
    assert data["d"]["total"] == 200
    assert data["d"]["correct"] == 134
