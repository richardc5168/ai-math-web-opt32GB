from __future__ import annotations

import json
from pathlib import Path


def _is_str(x) -> bool:
    return isinstance(x, str) and bool(x.strip())


ALLOWED_TYPES = {
    "attempt_started",
    "hint_shown",
    "answer_submitted",
    "attempt_completed",
    "next_question",
}


def test_event_schema_file_parses() -> None:
    schema_path = Path("src/coaching/event_schema.json")
    obj = json.loads(schema_path.read_text(encoding="utf-8"))
    assert obj.get("type") == "object"
    assert "definitions" in obj


def test_sample_event_log_contract() -> None:
    sample_path = Path("coaching_meta/events.sample.json")
    log = json.loads(sample_path.read_text(encoding="utf-8"))

    assert log.get("version") == 1
    assert _is_str(log.get("user_id"))

    events = log.get("events")
    assert isinstance(events, list)
    assert len(events) >= 1

    for e in events:
        assert isinstance(e, dict)
        assert e.get("type") in ALLOWED_TYPES
        assert isinstance(e.get("ts_ms"), int)
        assert e.get("ts_ms") >= 0

        if "question_id" in e:
            assert e["question_id"] is None or isinstance(e["question_id"], str)

        if "allow_continue" in e:
            assert isinstance(e["allow_continue"], bool)

        payload = e.get("payload")
        assert payload is None or isinstance(payload, dict)
