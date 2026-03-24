"""Tests for R48: _sanitize_practice_event hint evidence pass-through.

Validates that hint_sequence, hint_open_ts, hint_level_used survive
the server-side sanitizer when present, and are omitted when absent.
"""

import pytest
from server import _sanitize_practice_event


class TestSanitizePracticeEventHintFields:
    """R48: hint evidence chain fields pass through sanitizer."""

    def test_hint_fields_preserved(self):
        event = {
            "ts": 1700000000000,
            "score": 3,
            "total": 5,
            "topic": "fraction",
            "kind": "add",
            "hint_sequence": [0, 1, 2],
            "hint_open_ts": [1700000001000, 1700000002000, 1700000003000],
            "hint_level_used": 2,
        }
        out = _sanitize_practice_event(event)
        assert out["hint_sequence"] == [0, 1, 2]
        assert out["hint_open_ts"] == [1700000001000, 1700000002000, 1700000003000]
        assert out["hint_level_used"] == 2

    def test_hint_fields_omitted_when_absent(self):
        event = {"ts": 1700000000000, "score": 1, "total": 1, "topic": "t", "kind": "k"}
        out = _sanitize_practice_event(event)
        assert "hint_sequence" not in out
        assert "hint_open_ts" not in out
        assert "hint_level_used" not in out

    def test_empty_hint_lists_omitted(self):
        event = {"ts": 1700000000000, "score": 1, "total": 1,
                 "hint_sequence": [], "hint_open_ts": []}
        out = _sanitize_practice_event(event)
        assert "hint_sequence" not in out
        assert "hint_open_ts" not in out

    def test_hint_sequence_truncated_to_10(self):
        event = {"ts": 1700000000000, "score": 1, "total": 1,
                 "hint_sequence": list(range(20))}
        out = _sanitize_practice_event(event)
        assert len(out["hint_sequence"]) == 10

    def test_hint_level_used_coerced_to_int(self):
        event = {"ts": 1700000000000, "score": 1, "total": 1,
                 "hint_level_used": "3"}
        out = _sanitize_practice_event(event)
        assert out["hint_level_used"] == 3
        assert isinstance(out["hint_level_used"], int)

    def test_basic_fields_still_correct(self):
        event = {"ts": 1700000000000, "score": 4, "total": 5,
                 "topic": "decimal", "kind": "multiply", "mode": "practice",
                 "completed": True}
        out = _sanitize_practice_event(event)
        assert out["score"] == 4
        assert out["total"] == 5
        assert out["topic"] == "decimal"
        assert out["kind"] == "multiply"
        assert out["mode"] == "practice"
        assert out["completed"] is True
