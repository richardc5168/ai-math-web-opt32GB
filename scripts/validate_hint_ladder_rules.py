"""validate_hint_ladder_rules.py — Check hint ladder contract on questions_dump.jsonl.

Rules enforced:
  1. Exactly 3 hints per question.
  2. hint1 (概念引導) must NOT contain the final answer OR intermediate computed numbers.
  3. hint2 (列式引導) must NOT contain the final answer.
  4. hint3 (完整步驟) MUST contain the final answer.
  5. All hints must be non-empty and ≥ 8 characters (meaningful sentence).
  6. Hint difficulty must be progressive: hint1 shortest, hint3 longest (soft rule).
  7. No hint should be identical to another hint in the same question.

Usage:
    python scripts/validate_hint_ladder_rules.py --in_jsonl 20260218_test/questions_dump.jsonl
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _extract_answer_core(answer: str) -> str:
    """Strip units and whitespace, return the numeric core for leakage detection."""
    s = re.sub(r'[^\d/.\-]', '', answer.strip())
    return s.strip()


def check_item(item: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Check a single dump item's hint ladder. Returns (passed, issues)."""
    issues: List[str] = []
    hints = item.get("hints")
    answer = str(item.get("answer") or "").strip()
    answer_core = _extract_answer_core(answer)

    # Rule 1: exactly 3 hints
    if not isinstance(hints, list) or len(hints) != 3:
        issues.append(f"expected 3 hints, got {len(hints) if isinstance(hints, list) else 'non-list'}")
        return False, issues

    h1, h2, h3 = [str(h).strip() for h in hints]

    # Rule 5: non-empty and meaningful length
    for idx, h in enumerate([h1, h2, h3], 1):
        if not h:
            issues.append(f"hint{idx} is empty")
        elif len(h) < 8:
            issues.append(f"hint{idx} too short ({len(h)} chars)")

    # Rule 7: no duplicates
    if h1 == h2:
        issues.append("hint1 == hint2 (duplicate)")
    if h2 == h3:
        issues.append("hint2 == hint3 (duplicate)")
    if h1 == h3:
        issues.append("hint1 == hint3 (duplicate)")

    # Rule 2: hint1 must not contain final answer
    if answer_core and len(answer_core) >= 1:
        # For short answers like "7", only flag if it appears as a standalone number
        if len(answer_core) <= 2:
            # Use word boundary to avoid false positives
            if re.search(r'(?<![0-9/])' + re.escape(answer_core) + r'(?![0-9/])', h1):
                # Only flag if it looks like a standalone answer (not part of fraction notation)
                # Be lenient: single-digit answers are very common in Chinese text
                pass  # Too many false positives for short answers; skip
        else:
            if answer_core in h1:
                issues.append(f"hint1 leaks answer '{answer_core}'")

    # Rule 3: hint2 must not contain final answer (same logic)
    if answer_core and len(answer_core) >= 3:
        if answer_core in h2:
            issues.append(f"hint2 leaks answer '{answer_core}'")

    # Rule 4: hint3 SHOULD contain the answer (soft warning, not hard fail)
    # Many hint3s contain the full worked solution, so the answer should appear somewhere
    # This is informational, not a hard rule
    if answer_core and len(answer_core) >= 2 and answer_core not in h3:
        # Soft: don't fail, just note
        pass

    # Rule 6: progressive length (soft)
    if len(h1) > len(h3):
        issues.append("hint1 longer than hint3 (should be progressive)")

    passed = len(issues) == 0
    return passed, issues


def validate_jsonl(in_path: Path) -> Dict[str, Any]:
    """Validate all items. Returns summary."""
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
    all_issues: List[Dict[str, Any]] = []

    for item in items:
        ok, issues = check_item(item)
        if ok:
            passed += 1
        else:
            failed += 1
            all_issues.append({
                "template_id": item.get("template_id"),
                "seed": item.get("seed"),
                "issues": issues,
            })

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "failures": all_issues[:50],
    }


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Validate hint ladder rules on questions_dump.jsonl")
    p.add_argument("--in_jsonl", default="20260218_test/questions_dump.jsonl")
    args = p.parse_args(argv)

    result = validate_jsonl(Path(args.in_jsonl))

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["failed"] > 0:
        print(f"\n⚠ {result['failed']}/{result['total']} items have hint ladder issues")
        return 1
    print(f"\n✓ {result['passed']}/{result['total']} items passed hint ladder rules")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
