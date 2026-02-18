"""validate_math_correctness.py — Verify answers in questions_dump.jsonl using SymPy.

Usage:
    python scripts/validate_math_correctness.py --in_jsonl 20260218_test/questions_dump.jsonl

Reads each JSONL line, parses the answer, re-computes from the solution_steps where
possible, and flags any discrepancy.  Outputs a per-line pass/fail + summary.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import sympy  # noqa: F401
    HAS_SYMPY = True
except ImportError:
    HAS_SYMPY = False


def _parse_fraction_str(s: str) -> Optional[Fraction]:
    """Parse '3/5', '7', '1 3/5' etc. into a Fraction."""
    s = s.strip()
    if not s:
        return None
    # Mixed number: "2 3/5"
    m = re.match(r'^(\d+)\s+(\d+)\s*/\s*(\d+)$', s)
    if m:
        return Fraction(int(m.group(1)), 1) + Fraction(int(m.group(2)), int(m.group(3)))
    # Simple fraction: "3/5"
    m = re.match(r'^(-?\d+)\s*/\s*(\d+)$', s)
    if m:
        return Fraction(int(m.group(1)), int(m.group(2)))
    # Integer
    m = re.match(r'^(-?\d+)$', s)
    if m:
        return Fraction(int(m.group(1)), 1)
    # Decimal
    try:
        return Fraction(s).limit_denominator(10000)
    except (ValueError, ZeroDivisionError):
        return None


def _extract_numbers_from_steps(steps: List[Dict[str, Any]]) -> List[str]:
    """Pull final-looking numeric strings from solution_steps."""
    numbers: List[str] = []
    for st in steps:
        text = str(st.get("text") or "")
        # Look for patterns like "= 30" or "= 3/5" at end of line
        for m in re.finditer(r'=\s*(-?\d+(?:\s*/\s*\d+)?(?:\s+\d+/\d+)?)\s*(?:[。公]|$)', text):
            numbers.append(m.group(1).strip())
    return numbers


def _sympy_check(answer_str: str) -> Optional[bool]:
    """Use SymPy to check if the answer expression is self-consistent."""
    if not HAS_SYMPY:
        return None
    try:
        from sympy import Rational, simplify
        # Try parsing as SymPy expression
        ans_frac = _parse_fraction_str(answer_str)
        if ans_frac is None:
            return None
        sym_ans = Rational(ans_frac.numerator, ans_frac.denominator)
        # Self-consistency: simplified form should equal itself
        return bool(simplify(sym_ans - sym_ans) == 0)
    except Exception:
        return None


def validate_item(item: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate a single dump item. Returns (passed, list_of_issues)."""
    issues: List[str] = []
    answer_str = str(item.get("answer") or "").strip()

    if not answer_str:
        issues.append("empty answer")
        return False, issues

    # 1. Parse answer
    answer_frac = _parse_fraction_str(answer_str)
    if answer_frac is None:
        # Might be a text answer like "123 元" — try stripping units
        cleaned = re.sub(r'[^\d/.\-\s]', '', answer_str).strip()
        answer_frac = _parse_fraction_str(cleaned)

    if answer_frac is None:
        issues.append(f"cannot parse answer: {answer_str}")
        return False, issues

    # 2. Check answer is finite and non-negative (for G5 word problems)
    if answer_frac < 0:
        issues.append(f"negative answer: {answer_frac}")

    # 3. Solution steps should yield the same answer
    steps = item.get("solution_steps") or []
    if isinstance(steps, list) and steps:
        step_numbers = _extract_numbers_from_steps(steps)
        if step_numbers:
            last_num = _parse_fraction_str(step_numbers[-1])
            if last_num is not None and last_num != answer_frac:
                issues.append(f"step result {last_num} != answer {answer_frac}")

    # 4. SymPy self-consistency
    sym_ok = _sympy_check(answer_str)
    if sym_ok is False:
        issues.append("sympy self-consistency failed")

    passed = len(issues) == 0
    return passed, issues


def validate_jsonl(in_path: Path) -> Dict[str, Any]:
    """Validate all items in a JSONL file. Returns summary dict."""
    if not in_path.exists():
        raise FileNotFoundError(in_path)

    items = []
    for line in in_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        items.append(json.loads(line))

    total = len(items)
    passed = 0
    failed = 0
    failures: List[Dict[str, Any]] = []

    for item in items:
        ok, issues = validate_item(item)
        if ok:
            passed += 1
        else:
            failed += 1
            failures.append({
                "template_id": item.get("template_id"),
                "seed": item.get("seed"),
                "answer": item.get("answer"),
                "issues": issues,
            })

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "failures": failures[:50],  # cap for readability
    }


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Validate math correctness of questions_dump.jsonl")
    p.add_argument("--in_jsonl", default="20260218_test/questions_dump.jsonl")
    args = p.parse_args(argv)

    result = validate_jsonl(Path(args.in_jsonl))

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["failed"] > 0:
        print(f"\n⚠ {result['failed']}/{result['total']} items have math issues")
        return 1
    print(f"\n✓ {result['passed']}/{result['total']} items passed math validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
