"""Tests for pipeline/agent_loop.py"""
from __future__ import annotations

import json
import os
import textwrap
from pathlib import Path

import pytest
from pipeline.agent_loop import (
    ErrorMemory,
    read_readme_rules,
    parse_hourly_commands,
    interpret_command_intent,
    detect_idle,
    ERROR_MEMORY_PATH,
)


# ── ErrorMemory ───────────────────────────────────────────

class TestErrorMemory:
    def _make_memory(self, tmp_path, entries):
        """Create a temporary error memory JSONL file."""
        fp = tmp_path / "error_memory.jsonl"
        with open(fp, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return fp

    def test_empty_file(self, tmp_path):
        fp = self._make_memory(tmp_path, [])
        mem = ErrorMemory(path=fp)
        assert mem.summary()["total_known"] == 0
        assert mem.get_open_errors() == []

    def test_loads_entries(self, tmp_path):
        entries = [
            {"id": "E001", "status": "open", "severity": "high",
             "code": "solver", "fingerprint": "solver-div", "description": "bad divide"},
            {"id": "E002", "status": "resolved", "severity": "low",
             "code": "hint", "fingerprint": "hint-typo", "description": "typo"},
        ]
        fp = self._make_memory(tmp_path, entries)
        mem = ErrorMemory(path=fp)
        assert mem.summary()["total_known"] == 2

    def test_get_open_errors(self, tmp_path):
        entries = [
            {"id": "E001", "status": "open", "severity": "high",
             "code": "solver", "fingerprint": "solver-x", "description": "bad"},
            {"id": "E002", "status": "resolved", "severity": "low",
             "code": "hint", "fingerprint": "hint-x", "description": "ok"},
        ]
        fp = self._make_memory(tmp_path, entries)
        mem = ErrorMemory(path=fp)
        open_errs = mem.get_open_errors()
        assert len(open_errs) == 1
        assert open_errs[0]["id"] == "E001"

    def test_get_critical_errors(self, tmp_path):
        entries = [
            {"id": "E001", "status": "open", "severity": "critical",
             "code": "bank", "fingerprint": "bank-crash", "description": "crash"},
            {"id": "E002", "status": "open", "severity": "low",
             "code": "hint", "fingerprint": "hint-typo", "description": "typo"},
        ]
        fp = self._make_memory(tmp_path, entries)
        mem = ErrorMemory(path=fp)
        critical = mem.get_critical_errors()
        assert len(critical) == 1
        assert critical[0]["id"] == "E001"

    def test_frequently_broken(self, tmp_path):
        entries = [
            {"id": "E001", "status": "open", "severity": "high",
             "code": "solver", "fingerprint": "solver-err", "count": 3, "description": "a"},
            {"id": "E002", "status": "open", "severity": "high",
             "code": "hint", "fingerprint": "hint-err", "count": 1, "description": "b"},
        ]
        fp = self._make_memory(tmp_path, entries)
        mem = ErrorMemory(path=fp)
        freq = mem.get_frequently_broken(min_count=2)
        assert len(freq) == 1
        assert freq[0]["code"] == "solver"

    def test_should_avoid(self, tmp_path):
        entries = [
            {"id": "E001", "status": "open", "severity": "critical",
             "code": "bank", "fingerprint": "bank-crash", "count": 3, "description": "crash"},
        ]
        fp = self._make_memory(tmp_path, entries)
        mem = ErrorMemory(path=fp)
        assert mem.should_avoid("bank") is True
        assert mem.should_avoid("hint") is False

    def test_nonexistent_file(self, tmp_path):
        fp = tmp_path / "nope.jsonl"
        mem = ErrorMemory(path=fp)
        assert mem.summary()["total_known"] == 0

    def test_get_error_patterns(self, tmp_path):
        entries = [
            {"id": "E001", "status": "open", "severity": "high",
             "code": "solver", "fingerprint": "solver-divzero", "description": "div by zero"},
            {"id": "E002", "status": "open", "severity": "high",
             "code": "solver", "fingerprint": "solver-overflow", "description": "overflow"},
        ]
        fp = self._make_memory(tmp_path, entries)
        mem = ErrorMemory(path=fp)
        patterns = mem.get_error_patterns()
        assert len(patterns) == 2
        assert "solver-divzero" in patterns


# ── README Rules ──────────────────────────────────────────

class TestReadReadmeRules:
    def test_returns_dict(self):
        rules = read_readme_rules()
        assert isinstance(rules, dict)

    def test_contains_validation_commands(self):
        rules = read_readme_rules()
        assert "validation_commands" in rules or "sync_requirements" in rules


# ── Hourly Commands Parser ────────────────────────────────

class TestParseHourlyCommands:
    def test_valid_json(self, tmp_path):
        data = [
            {"action": "npm_script", "value": "verify:all", "cooldown_min": 60},
        ]
        fp = tmp_path / "cmds.json"
        fp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        cmds = parse_hourly_commands(path=fp)
        assert len(cmds) == 1
        assert cmds[0]["action"] == "npm_script"

    def test_trailing_commas(self, tmp_path):
        bad_json = textwrap.dedent("""\
        [
          {"action": "npm_script", "value": "verify:all", "cooldown_min": 60},
        ]
        """)
        fp = tmp_path / "cmds.json"
        fp.write_text(bad_json, encoding="utf-8")
        cmds = parse_hourly_commands(path=fp)
        assert len(cmds) >= 1

    def test_single_quotes(self, tmp_path):
        bad_json = "[{'action': 'npm_script', 'value': 'verify:all'}]"
        fp = tmp_path / "cmds.json"
        fp.write_text(bad_json, encoding="utf-8")
        cmds = parse_hourly_commands(path=fp)
        assert len(cmds) >= 1

    def test_missing_brackets(self, tmp_path):
        bad_json = '{"action": "npm_script", "value": "verify:all"}'
        fp = tmp_path / "cmds.json"
        fp.write_text(bad_json, encoding="utf-8")
        cmds = parse_hourly_commands(path=fp)
        assert len(cmds) >= 1

    def test_nonexistent_file(self, tmp_path):
        fp = tmp_path / "nope.json"
        cmds = parse_hourly_commands(path=fp)
        assert cmds == []


# ── Interpret Command Intent ──────────────────────────────

class TestInterpretCommandIntent:
    def test_known_npm_scripts(self):
        result = interpret_command_intent({"action": "npm_script", "value": "verify:all"})
        assert result["script"] == "verify:all"
        assert result["confidence"] == 1.0

    def test_fuzzy_match(self):
        result = interpret_command_intent({"action": "npm_script", "value": "verfy-all"})
        # Should fuzzy-match via keyword "verify" in value
        assert result is not None

    def test_chinese_keyword(self):
        result = interpret_command_intent({"action": "npm_script", "value": "", "note": "驗證"})
        assert result["type"] == "npm_script"
        assert result["script"] == "verify:all"

    def test_unknown_intent(self):
        result = interpret_command_intent({"action": "npm_script", "value": "xyzzy_unknown_command"})
        assert result["type"] == "unknown"

    def test_hint_keyword(self):
        result = interpret_command_intent({"action": "npm_script", "value": "", "note": "提示"})
        assert result["type"] == "npm_script"
        assert result["script"] == "autotune:hints"


# ── Idle Detection ────────────────────────────────────────

class TestDetectIdle:
    def test_returns_tuple(self):
        result = detect_idle(threshold_minutes=60)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_short_timeout(self):
        # With 0 threshold, most things should be "idle"
        is_idle, reason = detect_idle(threshold_minutes=0)
        assert isinstance(is_idle, bool)
        assert isinstance(reason, str)

    def test_long_timeout(self):
        is_idle, reason = detect_idle(threshold_minutes=999999)
        assert isinstance(is_idle, bool)
