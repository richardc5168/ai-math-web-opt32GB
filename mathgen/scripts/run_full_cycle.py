#!/usr/bin/env python3
"""Full cycle runner — benchmark → analyze → learn → report → gate.

This is the single-command sustainability engine for mathgen.
Every run automatically:
  1. Runs all benchmarks
  2. Loads previous lessons from the learning ledger
  3. Compares with last run to detect new/resolved errors
  4. Records new lessons learned to the ledger
  5. Generates an iteration report
  6. Prints actionable next steps

Usage:
    python mathgen/scripts/run_full_cycle.py
    python mathgen/scripts/run_full_cycle.py --changes "fixed L4 hint leak"
    python mathgen/scripts/run_full_cycle.py --gate-only  # exit code only, no report

Exit code 0 = all pass, 1 = failures found.
"""
import json
import os
import sys
from datetime import datetime, date, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_MATHGEN = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_MATHGEN)
sys.path.insert(0, _ROOT)

from mathgen.question_templates import ALL_GENERATORS
from mathgen.scripts.run_benchmarks import load_benchmark, run_topic
from mathgen.error_taxonomy import classify_error
from mathgen.reports.iteration_report_generator import (
    generate_iteration_report,
    save_iteration_report,
)

LOG_DIR = os.path.join(_MATHGEN, 'logs')
REPORTS_DIR = os.path.join(_MATHGEN, 'reports')
LESSONS_PATH = os.path.join(LOG_DIR, 'lessons_learned.jsonl')
HISTORY_PATH = os.path.join(LOG_DIR, 'change_history.jsonl')
BASELINE_PATH = os.path.join(LOG_DIR, 'last_pass_rate.json')


# ── Learning Ledger ──────────────────────────────────────────────

def load_lessons():
    """Load all accumulated lessons."""
    if not os.path.isfile(LESSONS_PATH):
        return []
    entries = []
    with open(LESSONS_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def record_lesson(lesson_type, description, error_codes=None, source='auto'):
    """Append a structured lesson to the learning ledger.

    lesson_type: 'fix_applied' | 'pattern_discovered' | 'anti_pattern' | 'rule_added'
    """
    os.makedirs(LOG_DIR, exist_ok=True)
    entry = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'type': lesson_type,
        'description': description,
        'error_codes': error_codes or [],
        'source': source,
    }
    with open(LESSONS_PATH, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    return entry


def load_baseline():
    """Load last known pass rate baseline."""
    if not os.path.isfile(BASELINE_PATH):
        return None
    with open(BASELINE_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_baseline(total, passed, by_topic):
    """Save current pass rate as the new baseline."""
    os.makedirs(LOG_DIR, exist_ok=True)
    data = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'total': total,
        'passed': passed,
        'by_topic': by_topic,
    }
    with open(BASELINE_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def load_change_history():
    """Load change history for anti-repeat checking."""
    if not os.path.isfile(HISTORY_PATH):
        return []
    entries = []
    with open(HISTORY_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


# ── Core Cycle ───────────────────────────────────────────────────

def run_all_benchmarks():
    """Run all benchmarks and return structured results."""
    all_pass = 0
    all_fail = 0
    all_failures = []
    by_topic = {}

    for topic, gen_cls in ALL_GENERATORS.items():
        cases = load_benchmark(topic)
        if cases is None:
            continue
        p, f, failures = run_topic(topic, gen_cls, cases)
        all_pass += p
        all_fail += f
        all_failures.extend(failures)
        by_topic[topic] = {'total': p + f, 'passed': p, 'failed': f}

    return {
        'total': all_pass + all_fail,
        'passed': all_pass,
        'failed': all_fail,
        'by_topic': by_topic,
        'fail_cases': all_failures,
    }


def detect_changes(current, baseline):
    """Compare current results with baseline to detect new/resolved errors."""
    if baseline is None:
        return [], []

    # New errors = error categories in current but not in baseline
    # We track at the topic level
    new_errors = []
    resolved_errors = []

    prev_topics = baseline.get('by_topic', {})
    curr_topics = current.get('by_topic', {})

    for topic in set(list(prev_topics.keys()) + list(curr_topics.keys())):
        prev_fail = prev_topics.get(topic, {}).get('failed', 0)
        curr_fail = curr_topics.get(topic, {}).get('failed', 0)

        if curr_fail > prev_fail:
            new_errors.append(f'{topic}: {prev_fail}→{curr_fail} failures')
        elif curr_fail < prev_fail:
            resolved_errors.append(f'{topic}: {prev_fail}→{curr_fail} failures')

    return new_errors, resolved_errors


def check_regression(current, baseline):
    """Check if pass rate has regressed. Returns (is_regression, message)."""
    if baseline is None:
        return False, 'No baseline yet — this run becomes the baseline.'

    prev_pass = baseline.get('passed', 0)
    curr_pass = current['passed']
    prev_total = baseline.get('total', 0)
    curr_total = current['total']

    if curr_total > 0 and prev_total > 0:
        prev_rate = prev_pass / prev_total
        curr_rate = curr_pass / curr_total
        if curr_rate < prev_rate:
            return True, (
                f'REGRESSION: pass rate dropped from {prev_rate:.1%} '
                f'({prev_pass}/{prev_total}) to {curr_rate:.1%} '
                f'({curr_pass}/{curr_total})'
            )

    return False, f'No regression. {curr_pass}/{curr_total} passing.'


def print_lessons_summary(lessons):
    """Print a brief summary of accumulated lessons for context."""
    if not lessons:
        return
    print(f'📖 {len(lessons)} accumulated lessons in the learning ledger.')
    # Show last 3 lessons
    recent = lessons[-3:]
    for l in recent:
        ts = l.get('timestamp', '')[:10]
        print(f'  [{ts}] {l["type"]}: {l["description"][:80]}')


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Mathgen full cycle')
    parser.add_argument('--changes', type=str, default='',
                        help='Description of changes made this iteration')
    parser.add_argument('--gate-only', action='store_true',
                        help='Only check pass/fail, no report generation')
    args = parser.parse_args()

    print('=' * 60)
    print('MATHGEN FULL CYCLE')
    print('=' * 60)

    # Step 1: Load previous state
    baseline = load_baseline()
    lessons = load_lessons()
    history = load_change_history()
    print_lessons_summary(lessons)
    print()

    # Step 2: Run benchmarks
    print('── Running Benchmarks ──')
    results = run_all_benchmarks()

    for topic, stats in sorted(results['by_topic'].items()):
        status = 'PASS' if stats['failed'] == 0 else 'FAIL'
        print(f'  [{status}] {topic}: {stats["passed"]}/{stats["total"]}')

    total = results['total']
    passed = results['passed']
    failed = results['failed']
    rate = passed / total if total > 0 else 0
    print(f'\n  Total: {passed}/{total} ({rate:.1%})')

    if args.gate_only:
        sys.exit(0 if failed == 0 else 1)

    # Step 3: Regression check
    print('\n── Regression Check ──')
    is_regression, reg_msg = check_regression(results, baseline)
    if is_regression:
        print(f'  ❌ {reg_msg}')
        record_lesson('anti_pattern', reg_msg,
                       error_codes=[c.get('case', '') for c in results['fail_cases'][:5]])
    else:
        print(f'  ✅ {reg_msg}')

    # Step 4: Detect new/resolved
    new_errors, resolved_errors = detect_changes(results, baseline)
    if new_errors:
        print('\n── New Errors ──')
        for e in new_errors:
            print(f'  ⚠ {e}')
    if resolved_errors:
        print('\n── Resolved Errors ──')
        for e in resolved_errors:
            print(f'  ✅ {e}')

    # Step 5: Anti-repeat check
    if results['fail_cases'] and history:
        recent_fix_codes = set()
        for h in history[-5:]:
            for c in h.get('error_codes_addressed', []):
                recent_fix_codes.add(c)

        current_error_cats = set()
        for fc in results['fail_cases']:
            for err in fc.get('errors', []):
                current_error_cats.add(classify_error(err))

        repeat_cats = current_error_cats & recent_fix_codes
        if repeat_cats:
            print('\n── Anti-Repeat Warning ──')
            for cat in repeat_cats:
                print(f'  ⚠ "{cat}" was recently addressed but still failing.')
                print(f'    → Try a DIFFERENT approach or escalate.')

    # Step 6: Generate iteration report
    report_md = generate_iteration_report(
        benchmark_results=results,
        changes_description=args.changes or '(first full cycle run)',
        new_errors=new_errors,
        resolved_errors=resolved_errors,
    )
    latest_path, history_path = save_iteration_report(report_md, REPORTS_DIR)
    print(f'\n── Iteration Report ──')
    print(f'  Latest: {latest_path}')
    print(f'  History: {history_path}')

    # Step 7: Auto-learn
    if failed == 0 and not is_regression:
        if baseline is None or passed > baseline.get('passed', 0):
            record_lesson(
                'fix_applied',
                f'All {passed} benchmarks passing. Changes: {args.changes or "initial run"}',
            )
        save_baseline(total, passed, results['by_topic'])
        print('\n  ✅ Baseline updated. Safe to commit.')
    elif failed > 0:
        # Record failure patterns as lessons
        error_cats = {}
        for fc in results['fail_cases']:
            for err in fc.get('errors', []):
                cat = classify_error(err)
                error_cats[cat] = error_cats.get(cat, 0) + 1
        top_cat = max(error_cats, key=error_cats.get) if error_cats else 'unknown'
        record_lesson(
            'pattern_discovered',
            f'{failed} failures. Top error category: {top_cat} ({error_cats.get(top_cat, 0)}x). '
            f'Change: {args.changes or "unknown"}',
            error_codes=list(error_cats.keys()),
        )
        print(f'\n  ❌ {failed} failures. Fix the top error category: {top_cat}')
        print(f'     DO NOT commit until all benchmarks pass.')

    # Step 8: Summary for next iteration
    print('\n── Next Steps ──')
    if failed == 0:
        print('  1. If changes were made, commit with: git add mathgen/ && git commit')
        print('  2. Consider adding more benchmark cases for edge coverage')
        print('  3. Check lessons_learned.jsonl for accumulated insights')
    else:
        print(f'  1. Fix the top error: {top_cat}')
        print(f'  2. Re-run: python mathgen/scripts/run_full_cycle.py --changes "description"')
        print(f'  3. Do NOT commit until this script exits 0')

    print()
    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
