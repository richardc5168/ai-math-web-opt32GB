#!/usr/bin/env python3
"""Audit docs/ pages for hint evidence chain coverage.

Scans all docs/*/index.html pages and classifies each as:
  - FULL:    uses shared hint engine + shared telemetry + setCurrentQuestion + appendAttempt
  - PARTIAL: uses some shared components but not all four
  - CUSTOM:  has hint UI but uses custom (non-shared) implementation
  - NONE:    no hint system (dashboard, report, info page — expected)

Exit code 0 if no PARTIAL pages (all question pages are FULL or deliberately NONE).
Exit code 1 if any PARTIAL pages need attention.

Usage:
    python tools/audit_hint_coverage.py          # human-readable table
    python tools/audit_hint_coverage.py --json   # machine-readable JSON
"""

import json
import os
import re
import sys
from pathlib import Path

DOCS_ROOT = Path(__file__).resolve().parent.parent / "docs"

# Pages that are NOT question/practice pages (no hint coverage expected)
NON_QUESTION_PAGES = {
    "docs",           # landing page
    "about",
    "admin-dashboard",
    "agent-status",
    "analytics-export",
    "kpi",
    "learning-map",
    "linear",
    "parent-report",
    "parent-view",
    "pricing",
    "privacy",
    "qa",
    "quadratic",
    "report",
    "teacher-dashboard",
    "terms",
    "territory-demo",
    "star-pack",
    "task-center",
    "offline-math-v2",
}


def scan_page(html_path: Path) -> dict:
    """Return coverage signals for a single page."""
    content = html_path.read_text(encoding="utf-8", errors="replace")
    return {
        "path": str(html_path.relative_to(DOCS_ROOT.parent)),
        "dir": html_path.parent.name,
        "has_setCurrentQuestion": bool(re.search(r"setCurrentQuestion", content)),
        "has_appendAttempt": bool(re.search(r"appendAttempt", content)),
        "has_hint_engine": bool(re.search(r"hint_engine\.js|AIMathHintEngine", content)),
        "has_telemetry": bool(re.search(r"attempt_telemetry\.js|AIMathAttemptTelemetry", content)),
        "has_custom_hint": bool(re.search(r"btnHint|hint_ladder|hintsByStyle", content)),
    }


def classify(info: dict) -> str:
    """Classify coverage level."""
    all_four = all([
        info["has_setCurrentQuestion"],
        info["has_appendAttempt"],
        info["has_hint_engine"],
        info["has_telemetry"],
    ])
    any_four = any([
        info["has_setCurrentQuestion"],
        info["has_appendAttempt"],
        info["has_hint_engine"],
        info["has_telemetry"],
    ])
    if all_four:
        return "FULL"
    if any_four or info["has_custom_hint"]:
        return "PARTIAL"
    return "NONE"


def main():
    json_mode = "--json" in sys.argv

    pages = sorted(DOCS_ROOT.glob("*/index.html"))
    # Also check docs/index.html itself
    root_index = DOCS_ROOT / "index.html"
    if root_index.exists() and root_index not in pages:
        pages.insert(0, root_index)

    results = []
    for p in pages:
        info = scan_page(p)
        info["classification"] = classify(info)
        info["is_question_page"] = info["dir"] not in NON_QUESTION_PAGES
        results.append(info)

    # Summary
    full = [r for r in results if r["classification"] == "FULL"]
    partial = [r for r in results if r["classification"] == "PARTIAL" and r["is_question_page"]]
    custom_only = [r for r in results if r["classification"] == "PARTIAL" and not r["is_question_page"]]
    none_expected = [r for r in results if r["classification"] == "NONE"]

    summary = {
        "total_pages": len(results),
        "full_coverage": len(full),
        "partial_question_pages": len(partial),
        "non_question_pages": len(none_expected) + len(custom_only),
        "coverage_rate": len(full) / max(1, len(full) + len(partial)),
        "partial_details": [{"dir": r["dir"], "missing": [
            k.replace("has_", "") for k in
            ["has_setCurrentQuestion", "has_appendAttempt", "has_hint_engine", "has_telemetry"]
            if not r[k]
        ]} for r in partial],
    }

    if json_mode:
        print(json.dumps({"pages": results, "summary": summary}, indent=2))
    else:
        print("=" * 70)
        print("HINT EVIDENCE CHAIN — PAGE COVERAGE AUDIT")
        print("=" * 70)
        print(f"\n{'Page':<45} {'Class':<10} {'setQ':<6} {'app':<6} {'hint':<6} {'telem':<6}")
        print("-" * 70)
        for r in results:
            mark = "✓" if r["classification"] == "FULL" else ("⚠" if r["classification"] == "PARTIAL" else "—")
            print(f"{mark} {r['dir']:<43} {r['classification']:<10} "
                  f"{'Y' if r['has_setCurrentQuestion'] else '.':<6} "
                  f"{'Y' if r['has_appendAttempt'] else '.':<6} "
                  f"{'Y' if r['has_hint_engine'] else '.':<6} "
                  f"{'Y' if r['has_telemetry'] else '.':<6}")

        print(f"\n{'=' * 70}")
        print(f"FULL coverage:  {summary['full_coverage']} question pages")
        print(f"PARTIAL (need attention): {summary['partial_question_pages']} pages")
        print(f"Non-question (OK):       {summary['non_question_pages']} pages")
        print(f"Coverage rate:           {summary['coverage_rate']:.0%}")

        if partial:
            print(f"\n⚠ PARTIAL pages needing attention:")
            for d in summary["partial_details"]:
                print(f"  - {d['dir']}: missing {', '.join(d['missing'])}")

    sys.exit(1 if partial else 0)


if __name__ == "__main__":
    main()
