import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT_ROOT = REPO_ROOT / 'artifacts' / 'run_10h'
DEFAULT_MATHGEN_LOGS = REPO_ROOT / 'mathgen' / 'logs'

COMMAND_NAME_PATTERNS = (
    ('verify:all', 'verify_all_npm'),
    ('validate_all_elementary_banks.py', 'validate_all_elementary_banks'),
    ('scripts/verify_all.py', 'verify_all_py'),
    ('run_full_cycle.py --gate-only', 'mathgen_gate_only'),
    ('run_full_cycle.py', 'mathgen_full_cycle'),
    ('test_mathgen_stability_contract.py', 'stability_contract'),
)

OPEN_COMMAND_RISK = {
    'verify_all_npm': 100,
    'mathgen_full_cycle': 95,
    'stability_contract': 85,
    'validate_all_elementary_banks': 80,
    'verify_all_py': 75,
    'mathgen_gate_only': 70,
}

WATCHLIST_RISK = {
    'hint_leaks_answer': 88,
    'wrong_numeric_answer': 84,
    'wrong_unit': 78,
    'benchmark_contract_drift': 92,
    'answer_format_drift': 72,
    'wording_ambiguity': 68,
    'difficulty_drift': 66,
    'too_many_decimal_places': 64,
}

TEST_GAP_SUGGESTIONS = {
    'verify_all_npm': 'Add a targeted verify:all fixture or seeded input that reproduces the failing step before rerunning the full gate.',
    'mathgen_full_cycle': 'Add a focused CLI regression test around run_full_cycle arguments and generated report outputs.',
    'stability_contract': 'Extend deterministic and fraction-normalization tests before changing generator behavior.',
    'hint_leaks_answer': 'Add benchmark cases and focused hint-level assertions that fail when the final answer appears verbatim.',
    'wrong_numeric_answer': 'Add a benchmark case plus verifier-contract assertion for the affected topic and format policy.',
    'wrong_unit': 'Add a benchmark case plus wording/unit consistency assertion for the affected topic.',
    'benchmark_contract_drift': 'Add a contract test tying benchmark expectations to verifier formatting and template semantics.',
    'answer_format_drift': 'Add explicit answer-format regression tests generated from verifier policy, not hand-written notation.',
    'report_truthfulness': 'Add a runner summary/report assertion that validates mode-specific wording and generated counts.',
}


def _read_json(path: Path, fallback=None):
    if not path.is_file():
        return fallback
    return json.loads(path.read_text(encoding='utf-8'))


def _read_jsonl(path: Path):
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def _write_text(path: Path, body: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding='utf-8')


def _parse_ts(value: str):
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


def _dedupe(values):
    seen = set()
    ordered = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def infer_command_name(command_text: str = '', root_cause: str = ''):
    combined = f'{root_cause} {command_text}'.lower()
    for needle, name in COMMAND_NAME_PATTERNS:
        if needle.lower() in combined:
            return name
    if root_cause:
        token = root_cause.split(' failed', 1)[0].strip()
        if token and ' ' not in token:
            return token
    return 'unknown_command'


def _extract_topic(case_id: str):
    if '[' not in case_id:
        return case_id or 'unknown'
    return case_id.split('[', 1)[0]


def _last_matching_strategy(category: str, change_history, lessons, strategy_kind: str):
    candidates = []
    if strategy_kind == 'successful':
        for entry in change_history:
            error_codes = entry.get('error_codes_addressed', []) or []
            description = entry.get('description', '')
            if category in error_codes or category in description:
                candidates.append((entry.get('timestamp', ''), description))
    for entry in lessons:
        error_codes = entry.get('error_codes', []) or []
        description = entry.get('description', '')
        entry_type = entry.get('type', '')
        if category not in error_codes and category not in description:
            continue
        if strategy_kind == 'failed' and entry_type == 'anti_pattern':
            candidates.append((entry.get('timestamp', ''), description))
        if strategy_kind == 'successful' and entry_type in {'fix_applied', 'pattern_discovered', 'coverage_expansion'}:
            candidates.append((entry.get('timestamp', ''), description))
    if not candidates:
        return ''
    candidates.sort(key=lambda item: _parse_ts(item[0]), reverse=True)
    return candidates[0][1]


def _test_gap(category: str):
    return TEST_GAP_SUGGESTIONS.get(
        category,
        'Add a focused regression test that reproduces the issue before rerunning the smallest relevant gate.',
    )


def build_issue_queue(*, artifact_root: Path, mathgen_logs: Path, run_id: str = ''):
    revision_history = _read_jsonl(artifact_root / 'revision_history.jsonl')
    error_memory = _read_jsonl(artifact_root / 'error_memory.jsonl')
    benchmark_failures = _read_jsonl(mathgen_logs / 'benchmark_failures.jsonl')
    change_history = _read_jsonl(mathgen_logs / 'change_history.jsonl')
    lessons = _read_jsonl(mathgen_logs / 'lessons_learned.jsonl')
    baseline = _read_json(mathgen_logs / 'last_pass_rate.json', {}) or {}

    latest_command_events = {}
    for row in revision_history:
        if row.get('event') != 'command':
            continue
        details = row.get('details', {})
        name = details.get('name') or infer_command_name(
            ' '.join(details.get('arguments', []) or []),
            details.get('name', ''),
        )
        candidate = {
            'name': name,
            'at': details.get('at') or row.get('at', ''),
            'pass': bool(details.get('pass')),
            'command': details.get('command', ''),
            'arguments': details.get('arguments', []) or [],
            'stdout': details.get('stdout', ''),
            'stderr': details.get('stderr', ''),
            'phase': row.get('phase', ''),
        }
        previous = latest_command_events.get(name)
        if previous is None or _parse_ts(candidate['at']) >= _parse_ts(previous['at']):
            latest_command_events[name] = candidate

    error_entries_by_command = defaultdict(list)
    for row in error_memory:
        category = row.get('category', '')
        command_name = infer_command_name(row.get('command', ''), row.get('root_cause', ''))
        if category == 'framework_setup' or command_name != 'unknown_command':
            error_entries_by_command[command_name].append(row)

    current_open_issues = []
    recently_resolved = []
    for name, latest in latest_command_events.items():
        related = sorted(
            error_entries_by_command.get(name, []),
            key=lambda item: _parse_ts(item.get('at', '')),
        )
        first_seen = related[0].get('at', latest.get('at', '')) if related else latest.get('at', '')
        reproducible_command = ' '.join([latest.get('command', '')] + list(latest.get('arguments', []) or [])).strip()
        evidence = _dedupe(
            [latest.get('stdout', ''), latest.get('stderr', '')]
            + [item.get('evidence', [None])[0] for item in related if item.get('evidence')]
        )
        issue = {
            'issue_id': f'gate:{name}',
            'status': 'open' if not latest.get('pass') else 'resolved',
            'error_category': name,
            'source_type': 'gate',
            'first_seen_at': first_seen,
            'last_seen_at': latest.get('at', ''),
            'occurrence_count': len(related) if related else 1,
            'affected_scope': {
                'type': 'command_gate',
                'commands': [reproducible_command],
                'topics': [],
                'cases': [],
            },
            'reproducible_commands': [reproducible_command],
            'risk_score': OPEN_COMMAND_RISK.get(name, 60 if not latest.get('pass') else 20),
            'suggested_test_gap': _test_gap(name),
            'last_failed_strategy': related[-1].get('root_cause', '') if related else '',
            'last_successful_strategy': (
                f"Latest successful gate replay at {latest.get('at', '')}" if latest.get('pass') else ''
            ),
            'evidence': evidence[:5],
        }
        if issue['status'] == 'open':
            current_open_issues.append(issue)
        elif related:
            recently_resolved.append(issue)

    benchmark_groups = {}
    for run in benchmark_failures:
        run_ts = run.get('timestamp', '')
        for failure in run.get('failures', []) or []:
            topic = _extract_topic(failure.get('case', 'unknown'))
            categories = failure.get('classified') or []
            if not categories:
                categories = [failure.get('errors', ['unknown'])[0].split(':', 1)[0]]
            for category in set(categories):
                key = (category, topic)
                group = benchmark_groups.setdefault(
                    key,
                    {
                        'error_category': category,
                        'topic': topic,
                        'first_seen_at': run_ts,
                        'last_seen_at': run_ts,
                        'cases': set(),
                        'runs': set(),
                        'notes': [],
                        'raw_errors': [],
                    },
                )
                group['first_seen_at'] = min(group['first_seen_at'], run_ts, key=_parse_ts)
                group['last_seen_at'] = max(group['last_seen_at'], run_ts, key=_parse_ts)
                group['cases'].add(failure.get('case', ''))
                group['runs'].add(run_ts)
                if failure.get('note'):
                    group['notes'].append(failure['note'])
                for err in failure.get('errors', []) or []:
                    if category in err or err.split(':', 1)[0] == category:
                        group['raw_errors'].append(err)

    watchlist = []
    for (category, topic), group in benchmark_groups.items():
        occurrence_count = len(group['cases'])
        run_count = len(group['runs'])
        successful_strategy = _last_matching_strategy(category, change_history, lessons, 'successful')
        failed_strategy = _last_matching_strategy(category, change_history, lessons, 'failed')
        risk_score = WATCHLIST_RISK.get(category, 55) + min(occurrence_count * 3, 18) + min(run_count * 4, 12)
        if not successful_strategy:
            risk_score += 6
        watchlist.append(
            {
                'issue_id': f'benchmark:{category}:{topic}',
                'status': 'watchlist',
                'error_category': category,
                'source_type': 'benchmark_history',
                'first_seen_at': group['first_seen_at'],
                'last_seen_at': group['last_seen_at'],
                'occurrence_count': occurrence_count,
                'affected_scope': {
                    'type': 'mathgen_topic',
                    'commands': [f'python mathgen/scripts/run_benchmarks.py --topic {topic}'],
                    'topics': [topic],
                    'cases': sorted(group['cases']),
                },
                'reproducible_commands': [
                    f'python mathgen/scripts/run_benchmarks.py --topic {topic}',
                    'python mathgen/scripts/run_full_cycle.py',
                ],
                'risk_score': risk_score,
                'suggested_test_gap': _test_gap(category),
                'last_failed_strategy': failed_strategy,
                'last_successful_strategy': successful_strategy,
                'evidence': _dedupe(group['raw_errors'] + group['notes'])[:5],
            }
        )

    watchlist.sort(key=lambda item: (-item['risk_score'], item['last_seen_at']))
    current_open_issues.sort(key=lambda item: (-item['risk_score'], item['last_seen_at']))
    recently_resolved.sort(key=lambda item: _parse_ts(item['last_seen_at']), reverse=True)

    next_best_targets = current_open_issues[:5] if current_open_issues else watchlist[:5]
    return {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'active_run_id': run_id,
        'baseline': baseline,
        'summary': {
            'current_open_count': len(current_open_issues),
            'watchlist_count': len(watchlist),
            'resolved_recent_count': len(recently_resolved),
            'top_target': next_best_targets[0]['issue_id'] if next_best_targets else None,
        },
        'current_open_issues': current_open_issues,
        'next_best_targets': next_best_targets,
        'watchlist': watchlist,
        'recently_resolved': recently_resolved[:10],
    }


def queue_to_markdown(queue):
    lines = [
        '# Issue Queue',
        '',
        f"- generated_at: {queue.get('generated_at', '')}",
        f"- active_run_id: {queue.get('active_run_id', '')}",
        f"- current_open_count: {queue.get('summary', {}).get('current_open_count', 0)}",
        f"- watchlist_count: {queue.get('summary', {}).get('watchlist_count', 0)}",
        '',
        '## Current Open Issues',
    ]
    open_issues = queue.get('current_open_issues', [])
    if open_issues:
        for item in open_issues:
            lines.append(
                f"- {item['issue_id']} | risk={item['risk_score']} | last_seen={item['last_seen_at']} | test_gap={item['suggested_test_gap']}"
            )
    else:
        lines.append('- none')
    lines += ['', '## Next Best Targets']
    targets = queue.get('next_best_targets', [])
    if targets:
        for item in targets:
            scope = item['affected_scope'].get('topics', []) or item['affected_scope'].get('commands', [])
            lines.append(
                f"- {item['issue_id']} | source={item['source_type']} | risk={item['risk_score']} | scope={','.join(scope)}"
            )
    else:
        lines.append('- none')
    lines += ['', '## Recently Resolved']
    resolved = queue.get('recently_resolved', [])
    if resolved:
        for item in resolved:
            lines.append(f"- {item['issue_id']} | last_seen={item['last_seen_at']}")
    else:
        lines.append('- none')
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description='Build machine-readable issue queue')
    parser.add_argument('--artifact-root', default=str(DEFAULT_ARTIFACT_ROOT))
    parser.add_argument('--mathgen-logs', default=str(DEFAULT_MATHGEN_LOGS))
    parser.add_argument('--run-id', default='')
    args = parser.parse_args()

    artifact_root = Path(args.artifact_root)
    mathgen_logs = Path(args.mathgen_logs)
    queue = build_issue_queue(artifact_root=artifact_root, mathgen_logs=mathgen_logs, run_id=args.run_id)
    markdown = queue_to_markdown(queue)

    _write_json(artifact_root / 'issue_queue.json', queue)
    _write_text(artifact_root / 'issue_queue.md', markdown)
    if args.run_id:
        run_root = artifact_root / args.run_id
        _write_json(run_root / 'issue_queue.json', queue)
        _write_text(run_root / 'issue_queue.md', markdown)

    print(json.dumps(queue['summary'], ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
