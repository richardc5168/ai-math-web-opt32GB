import importlib
import json
import os
import random
import sqlite3
from pathlib import Path
from fractions import Fraction

import httpx
import pytest

SPEC_PATH = Path(__file__).parent / "specs" / "question_validation.json"
OFFLINE_BANK_PATH = Path("docs/offline-math/bank.js")

TYPE_MODULES = {
    "g5s_web_concepts_v1": "question_types.g5s_web_concepts.type",
    "g5s_good_concepts_v1": "question_types.g5s_good_concepts.type",
    "external_web_fraction_app_v1": "src.question_types.external_web_fraction_app_v1.type",
    "fraction_decimal_application_web_v1": "src.question_types.fraction_decimal_application_web_v1.type",
}


def _load_spec() -> dict:
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def _parse_time_hhmm(s: str) -> str | None:
    t = (s or "").strip().replace("：", ":")
    if not t:
        return None
    parts = t.split(":")
    if len(parts) != 2:
        return None
    try:
        hh = int(parts[0])
        mm = int(parts[1])
    except Exception:
        return None
    if hh < 0 or hh > 23 or mm < 0 or mm > 59:
        return None
    return f"{hh:02d}:{mm:02d}"


def _parse_fraction(s: str) -> Fraction | None:
    t = (s or "").strip().replace(" ", "")
    if "/" not in t:
        return None
    try:
        return Fraction(t)
    except Exception:
        return None


def _parse_number(s: str) -> float | None:
    t = (s or "").strip().replace(",", "")
    if not t:
        return None
    try:
        return float(t)
    except Exception:
        return None


def _validate_answer_parse(answer: str, validator: dict) -> None:
    vtype = str(validator.get("type") or "text").strip()
    if vtype == "time_hhmm":
        assert _parse_time_hhmm(answer) is not None
        return
    if vtype == "fraction":
        assert _parse_fraction(answer) is not None
        return
    if vtype == "number":
        assert _parse_number(answer) is not None
        return
    # text fallback
    assert str(answer).strip() != ""


def _get_type_module(type_key: str):
    mod_name = TYPE_MODULES.get(type_key)
    if not mod_name:
        raise AssertionError(f"Missing type module mapping for {type_key}")
    return importlib.import_module(mod_name)


def _check_answer_with_module(type_key: str, answer: str, validator: dict) -> None:
    mod = _get_type_module(type_key)
    payload = {"answer": answer, "validator": validator}
    result = mod.check_answer(answer, payload)
    assert result == 1


def _load_pack(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _find_item(items: list[dict], item_id: str) -> dict:
    for it in items:
        if str(it.get("id")) == item_id:
            return it
    raise AssertionError(f"Item not found: {item_id}")


def test_pack_integrity_and_golden_set():
    spec = _load_spec()
    for pack in spec["packs"]:
        data = _load_pack(pack["path"])
        items = data.get("items") or []
        min_items = int(pack.get("min_items") or spec.get("min_items_default") or 1)

        assert data.get("type_key") == pack["type_key"]
        assert isinstance(items, list)
        assert len(items) >= min_items

        seen_ids = set()
        for it in items:
            assert isinstance(it, dict)
            item_id = str(it.get("id") or "")
            assert item_id
            assert item_id not in seen_ids
            seen_ids.add(item_id)

            assert str(it.get("type_key") or "") == pack["type_key"]
            assert str(it.get("difficulty") or "")
            assert str(it.get("question") or "")
            assert str(it.get("answer") or "")

            hints = it.get("hints") or {}
            assert str(hints.get("level1") or "")
            assert str(hints.get("level2") or "")
            assert str(hints.get("level3") or "")

            steps = it.get("steps") or []
            assert isinstance(steps, list)
            assert len(steps) >= 1

            validator = it.get("validator") or {}
            _validate_answer_parse(str(it.get("answer") or ""), validator)
            _check_answer_with_module(pack["type_key"], str(it.get("answer") or ""), validator)

        for g in pack.get("golden_items", []):
            item = _find_item(items, g["id"])
            assert str(item.get("answer") or "") == g["answer"]
            assert item.get("hints") == g["hints"]
            assert item.get("steps") == g["steps"]
            _check_answer_with_module(pack["type_key"], g["answer"], item.get("validator") or {})

        for seed in pack.get("random_seeds", []):
            rng = random.Random(int(seed))
            pick1 = rng.choice(items)
            rng = random.Random(int(seed))
            pick2 = rng.choice(items)
            assert pick1.get("id") == pick2.get("id")
            _check_answer_with_module(pack["type_key"], str(pick1.get("answer") or ""), pick1.get("validator") or {})


def _load_offline_bank() -> list[dict]:
    text = OFFLINE_BANK_PATH.read_text(encoding="utf-8")
    marker = "window.OFFLINE_MATH_BANK ="
    idx = text.find(marker)
    assert idx != -1
    start = text.find("[", idx)
    end = text.rfind("];\n")
    if end == -1:
        end = text.rfind("];\r\n")
    if end == -1:
        end = text.rfind("];")
    assert start != -1 and end != -1 and end > start
    payload = text[start:end + 1]
    return json.loads(payload)


def test_offline_math_has_teacher_steps():
    bank = _load_offline_bank()
    assert isinstance(bank, list)
    assert len(bank) > 0

    missing = []
    for it in bank:
        steps = it.get("teacherSteps")
        if not isinstance(steps, list) or not steps:
            missing.append(it.get("id"))
            continue
        has_say = any(isinstance(s, dict) and str(s.get("say") or "").strip() for s in steps)
        if not has_say:
            missing.append(it.get("id"))

    assert not missing, f"Missing teacherSteps: {missing[:10]}"


def _make_client(tmp_path):
    os.environ["DB_PATH"] = str(tmp_path / "test_app.db")
    import server
    importlib.reload(server)
    transport = httpx.ASGITransport(app=server.app)
    return transport


def _fetch_correct_answer(db_path: str, question_id: int) -> str:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT correct_answer FROM question_cache WHERE id=?", (question_id,)).fetchone()
    conn.close()
    assert row is not None
    return row["correct_answer"]


def _extract_answer(correct_answer: str) -> str:
    try:
        payload = json.loads(correct_answer)
        if isinstance(payload, dict) and "answer" in payload:
            return str(payload.get("answer") or "")
    except Exception:
        pass
    return str(correct_answer or "")


@pytest.mark.anyio
async def test_api_end_to_end_for_topic_keys(tmp_path):
    spec = _load_spec()
    topic_keys = (spec.get("api_validation") or {}).get("topic_keys") or []
    assert topic_keys

    transport = _make_client(tmp_path)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/admin/bootstrap", params={"name": "Pytest"})
        assert r.status_code == 200
        api_key = r.json()["api_key"]
        headers = {"X-API-Key": api_key}

        r = await client.get("/v1/students", headers=headers)
        assert r.status_code == 200
        student_id = r.json()["students"][0]["id"]

        for topic_key in topic_keys:
            r = await client.post(
                "/v1/questions/next",
                params={"student_id": student_id, "topic_key": topic_key},
                headers=headers,
            )
            assert r.status_code == 200
            qid = r.json()["question_id"]

            r = await client.post(
                "/v1/questions/hint",
                headers=headers,
                json={"question_id": qid, "level": 2},
            )
            assert r.status_code == 200
            assert r.json().get("hint")

            correct_answer = _fetch_correct_answer(os.environ["DB_PATH"], qid)
            user_answer = _extract_answer(correct_answer)

            r = await client.post(
                "/v1/answers/submit",
                headers=headers,
                json={
                    "student_id": student_id,
                    "question_id": qid,
                    "user_answer": user_answer,
                    "time_spent_sec": 1,
                },
            )
            assert r.status_code == 200
            j = r.json()
            assert j.get("is_correct") == 1
            assert j.get("correct_answer")
