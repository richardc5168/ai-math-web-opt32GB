#!/usr/bin/env python3
"""Iteration runner — controlled optimization loop with anti-repeat.

Usage:
    python mathgen/scripts/run_iteration.py

Reads benchmark failures, classifies errors, checks change_history
to avoid repeating the same fix, suggests next actions.
"""
import json
import os
import sys
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _ROOT)

from mathgen.error_taxonomy import classify_error, KNOWN_ERROR_CODES
from mathgen.reports.iteration_report_generator import (
    generate_iteration_report,
    save_iteration_report,
)

MATHGEN_DIR = os.path.dirname(_HERE)
LOG_DIR = os.path.join(MATHGEN_DIR, 'logs')
HISTORY_PATH = os.path.join(LOG_DIR, 'change_history.jsonl')
FAILURES_PATH = os.path.join(LOG_DIR, 'benchmark_failures.jsonl')


def load_latest_failures():
    """Load the most recent benchmark failure entry."""
    if not os.path.isfile(FAILURES_PATH):
        return None
    last_line = None
    with open(FAILURES_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                last_line = line
    if not last_line:
        return None
    return json.loads(last_line)


def load_change_history():
    """Load all past change entries."""
    if not os.path.isfile(HISTORY_PATH):
        return []
    entries = []
    with open(HISTORY_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def record_change(change_desc, error_codes_addressed):
    """Record a change to the history for anti-repeat."""
    os.makedirs(LOG_DIR, exist_ok=True)
    entry = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'description': change_desc,
        'error_codes_addressed': list(error_codes_addressed),
    }
    with open(HISTORY_PATH, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    return entry


def suggest_fixes(failures, history):
    """Analyze failures and suggest fixes, avoiding repeats.

    Returns:
        list of suggestion dicts
    """
    if not failures:
        return []

    # Collect all error categories from latest failures
    error_counts = {}
    for fail in failures.get('failures', []):
        for err_str in fail.get('errors', []):
            cat = classify_error(err_str)
            error_counts[cat] = error_counts.get(cat, 0) + 1

    # Find categories already addressed recently
    recent_fixes = set()
    for h in history[-5:]:  # last 5 changes
        for code in h.get('error_codes_addressed', []):
            recent_fixes.add(code)

    suggestions = []
    for cat, count in sorted(error_counts.items(), key=lambda x: -x[1]):
        if cat in recent_fixes:
            suggestions.append({
                'category': cat,
                'count': count,
                'status': 'RECENTLY_FIXED',
                'action': f'Category "{cat}" was recently addressed. Check if the fix was effective or try a different approach.',
            })
        else:
            suggestions.append({
                'category': cat,
                'count': count,
                'status': 'NEW',
                'action': f'Fix {count} occurrence(s) of "{cat}". Check generator logic for this error type.',
            })

    return suggestions


def main():
    print('=== Mathgen Iteration Runner ===\n')

    # Load data
    latest = load_latest_failures()
    history = load_change_history()

    if latest is None:
        print('No benchmark failure log found. Run benchmarks first:')
        print('  python mathgen/scripts/run_benchmarks.py')
        sys.exit(0)

    total_pass = latest.get('total_pass', 0)
    total_fail = latest.get('total_fail', 0)
    timestamp = latest.get('timestamp', 'unknown')

    print(f'Latest benchmark run: {timestamp}')
    print(f'Results: {total_pass} passed, {total_fail} failed')
    print(f'Change history entries: {len(history)}\n')

    if total_fail == 0:
        print('All benchmarks passing. No fixes needed.')
        # Generate clean iteration report
        reports_dir = os.path.join(MATHGEN_DIR, 'reports')
        report = generate_iteration_report(
            benchmark_results={
                'total': total_pass, 'passed': total_pass, 'failed': 0,
                'by_topic': {}, 'fail_cases': [],
            },
            changes_description='(no changes — all benchmarks passing)',
        )
        save_iteration_report(report, reports_dir)
        print(f'\nIteration report saved.')
        sys.exit(0)

    # Suggest fixes
    suggestions = suggest_fixes(latest, history)

    print('--- Suggested Fixes ---')
    for s in suggestions:
        marker = '⚠' if s['status'] == 'RECENTLY_FIXED' else '→'
        print(f'  {marker} [{s["status"]}] {s["category"]} (×{s["count"]}): {s["action"]}')

    print(f'\n--- Failed Cases ---')
    for fail in latest.get('failures', []):
        print(f'  ✗ {fail["case"]}: {fail["errors"]}')
        if fail.get('note'):
            print(f'    note: {fail["note"]}')

    print(f'\nTo record a fix after making changes:')
    print(f'  python -c "from mathgen.scripts.run_iteration import record_change; '
          f'record_change(\'description\', [\'error_code\'])"')

    sys.exit(1 if total_fail > 0 else 0)


if __name__ == '__main__':
    main()
