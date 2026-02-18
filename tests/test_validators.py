"""Tests for validate_math_correctness.py and validate_hint_ladder_rules.py."""
import json
from pathlib import Path

from scripts.validate_math_correctness import validate_item as validate_math_item
from scripts.validate_hint_ladder_rules import check_item as check_hint_item


def test_math_valid_fraction():
    item = {
        "answer": "3/5",
        "solution_steps": [
            {"step_index": 1, "text": "3 ÷ 5 = 3/5。"},
        ],
    }
    ok, issues = validate_math_item(item)
    assert ok
    assert issues == []


def test_math_valid_integer():
    item = {
        "answer": "30",
        "solution_steps": [
            {"step_index": 1, "text": "計算得到 = 30。"},
        ],
    }
    ok, issues = validate_math_item(item)
    assert ok


def test_math_empty_answer():
    item = {"answer": "", "solution_steps": []}
    ok, issues = validate_math_item(item)
    assert not ok
    assert any("empty" in i for i in issues)


def test_hint_valid_ladder():
    item = {
        "answer": "30",
        "hints": [
            "先想想這題在問什麼運算。",
            "剩下量 = 總量 × (1 − 用掉的分數)。",
            "Step 1: 1 − 3/8 = 5/8。Step 2: 48 × 5/8 = 30。答案：30。",
        ],
    }
    ok, issues = check_hint_item(item)
    assert ok
    assert issues == []


def test_hint_too_few():
    item = {"answer": "7", "hints": ["只有一個"]}
    ok, issues = check_hint_item(item)
    assert not ok


def test_hint_duplicate():
    item = {
        "answer": "7",
        "hints": ["先想一想。", "先想一想。", "算出答案 = 7。"],
    }
    ok, issues = check_hint_item(item)
    assert not ok
    assert any("duplicate" in i for i in issues)


def test_hint_answer_leak_in_hint1():
    item = {
        "answer": "123",
        "hints": [
            "答案是 123 元。",
            "列式…",
            "答案 123。",
        ],
    }
    ok, issues = check_hint_item(item)
    assert not ok
    assert any("leaks" in i for i in issues)
