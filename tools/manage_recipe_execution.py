import argparse
import json
import shlex
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path
import sys

if __package__ in {None, ''}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT_ROOT = REPO_ROOT / 'artifacts' / 'run_10h'
DEFAULT_MATHGEN_LOGS = REPO_ROOT / 'mathgen' / 'logs'


def _read_json(path: Path, fallback=None):
    if not path.is_file():
        return fallback
    return json.loads(path.read_text(encoding='utf-8'))


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def _write_text(path: Path, body: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding='utf-8')


def _read_jsonl(path: Path):
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _append_jsonl(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + '\n')


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _normalize_error_category(value: str):
    return (value or '').strip()


def _substitute_placeholders(command_text: str, target):
    topic = ''
    topics = ((target.get('affected_scope') or {}).get('topics') or [])
    if topics:
        topic = topics[0]
    return command_text.replace('<topic>', topic)


def _parse_command(command_text: str):
    parts = shlex.split(command_text, posix=False)
    if not parts:
        return None
    return {
        'display': command_text,
        'program': parts[0],
        'arguments': parts[1:],
    }


def _extract_executable_commands(command_texts, target):
    commands = []
    seen = set()
    for entry in command_texts:
        if not isinstance(entry, str):
            continue
        substituted = _substitute_placeholders(entry, target).strip()
        if not substituted.startswith(('python ', 'node ', 'npm ')):
            continue
        parsed = _parse_command(substituted)
        if parsed is None:
            continue
        key = (parsed['program'], tuple(parsed['arguments']))
        if key in seen:
            continue
        seen.add(key)
        commands.append(parsed)
    return commands


def _active_recipe_markdown(recipe):
    lines = [
        '# Active Recipe',
        '',
        f"- run_id: {recipe.get('run_id', '')}",
        f"- status: {recipe.get('status', '')}",
        f"- issue_id: {recipe.get('issue_id', '')}",
        f"- error_category: {recipe.get('error_category', '')}",
        f"- strategy_key: {recipe.get('strategy_key', '')}",
        f"- strategy: {recipe.get('strategy', '')}",
        f"- selected_at: {recipe.get('selected_at', '')}",
        '',
        '## Decision',
        f"- {recipe.get('decision_reason', '')}",
        '',
        '## Allowed Edit Scope',
    ]
    for item in recipe.get('allowed_edit_scope', []):
        lines.append(f'- {item}')
    lines += ['', '## Preflight Commands']
    if recipe.get('preflight_commands'):
        for item in recipe['preflight_commands']:
            lines.append(f"- {item['display']}")
    else:
        lines.append('- none')
    lines += ['', '## Postflight Commands']
    if recipe.get('postflight_commands'):
        for item in recipe['postflight_commands']:
            lines.append(f"- {item['display']}")
    else:
        lines.append('- none')
    return '\n'.join(lines) + '\n'


def _outcome_paths(artifact_root: Path, run_id: str):
    run_root = artifact_root / run_id if run_id else artifact_root
    return {
        'strategy_outcomes': artifact_root / 'strategy_outcomes.jsonl',
        'active_recipe_json': artifact_root / 'active_recipe.json',
        'active_recipe_md': artifact_root / 'active_recipe.md',
        'run_active_recipe_json': run_root / 'active_recipe.json',
        'run_active_recipe_md': run_root / 'active_recipe.md',
    }


def _mathgen_log_paths(mathgen_logs: Path):
    return {
        'change_history': mathgen_logs / 'change_history.jsonl',
        'lessons_learned': mathgen_logs / 'lessons_learned.jsonl',
    }


def _latest_outcome(rows, *, issue_id: str, strategy_key: str, event: str):
    for row in reversed(rows):
        if row.get('issue_id') == issue_id and row.get('strategy_key') == strategy_key and row.get('event') == event:
            return row
    return None


def select_active_recipe(*, artifact_root: Path, run_id: str):
    queue = _read_json(artifact_root / 'issue_queue.json', {}) or {}
    paths = _outcome_paths(artifact_root, run_id)
    outcomes = _read_jsonl(paths['strategy_outcomes'])
    targets = queue.get('next_best_actionable_targets', []) or []
    selected = targets[0] if targets else None
    previous = _read_json(paths['active_recipe_json'], {}) or {}

    if not selected:
        payload = {
            'run_id': run_id,
            'status': 'idle',
            'selected_at': _now_iso(),
            'issue_id': '',
            'error_category': '',
            'strategy_key': '',
            'strategy': '',
            'decision_reason': 'No actionable target is currently available.',
            'allowed_edit_scope': [],
            'preflight_commands': [],
            'postflight_commands': [],
        }
        _write_json(paths['active_recipe_json'], payload)
        _write_text(paths['active_recipe_md'], _active_recipe_markdown(payload))
        if run_id:
            _write_json(paths['run_active_recipe_json'], payload)
            _write_text(paths['run_active_recipe_md'], _active_recipe_markdown(payload))
        return {'selection_changed': previous.get('issue_id', '') != '', 'active_recipe': payload}

    recipe = selected.get('fix_recipe') or {}
    anti_repeat = selected.get('anti_repeat') or {}
    payload = {
        'run_id': run_id,
        'status': 'selected' if anti_repeat.get('decision') == 'allow' else anti_repeat.get('decision', 'blocked'),
        'selected_at': _now_iso(),
        'issue_id': selected.get('issue_id', ''),
        'error_category': selected.get('error_category', ''),
        'topic': ((selected.get('affected_scope') or {}).get('topics') or [''])[0],
        'source_type': selected.get('source_type', ''),
        'risk_score': selected.get('risk_score', 0),
        'strategy_key': anti_repeat.get('proposed_strategy_key', ''),
        'strategy': anti_repeat.get('proposed_strategy', ''),
        'decision_reason': anti_repeat.get('reason', ''),
        'allowed_edit_scope': recipe.get('allowed_edit_scope', []),
        'forbidden_shortcuts': recipe.get('forbidden_shortcuts', []),
        'rollback_condition': recipe.get('rollback_condition', []),
        'recommended_diff_pattern': recipe.get('recommended_diff_pattern', []),
        'reproducible_commands': selected.get('reproducible_commands', []),
        'preflight_commands': _extract_executable_commands(recipe.get('mandatory_pre_test', []), selected),
        'postflight_commands': _extract_executable_commands(recipe.get('mandatory_post_test', []), selected),
        'selection_changed': (
            previous.get('issue_id') != selected.get('issue_id')
            or previous.get('strategy_key') != anti_repeat.get('proposed_strategy_key', '')
        ),
    }

    _write_json(paths['active_recipe_json'], payload)
    _write_text(paths['active_recipe_md'], _active_recipe_markdown(payload))
    if run_id:
        _write_json(paths['run_active_recipe_json'], payload)
        _write_text(paths['run_active_recipe_md'], _active_recipe_markdown(payload))

    if payload['selection_changed']:
        row = {
            'timestamp': payload['selected_at'],
            'run_id': run_id,
            'issue_id': payload['issue_id'],
            'error_category': payload['error_category'],
            'topic': payload.get('topic', ''),
            'strategy_key': payload['strategy_key'],
            'strategy': payload['strategy'],
            'event': 'selected',
            'outcome': 'pending' if payload['status'] == 'selected' else payload['status'],
            'blocked': payload['status'] != 'selected',
            'has_side_effect': False,
            'counts_toward_blacklist': False,
            'source': 'auto_recipe_controller',
            'reason': payload['decision_reason'],
            'changed_files': [],
        }
        _append_jsonl(paths['strategy_outcomes'], row)
    else:
        last_selection = _latest_outcome(outcomes, issue_id=payload['issue_id'], strategy_key=payload['strategy_key'], event='selected')
        if last_selection is None:
            _append_jsonl(
                paths['strategy_outcomes'],
                {
                    'timestamp': payload['selected_at'],
                    'run_id': run_id,
                    'issue_id': payload['issue_id'],
                    'error_category': payload['error_category'],
                    'topic': payload.get('topic', ''),
                    'strategy_key': payload['strategy_key'],
                    'strategy': payload['strategy'],
                    'event': 'selected',
                    'outcome': 'pending',
                    'blocked': False,
                    'has_side_effect': False,
                    'counts_toward_blacklist': False,
                    'source': 'auto_recipe_controller',
                    'reason': payload['decision_reason'],
                    'changed_files': [],
                },
            )
    return {'selection_changed': payload['selection_changed'], 'active_recipe': payload}


def _scope_ok(changed_files, allowed_patterns):
    if not changed_files:
        return True
    if not allowed_patterns:
        return False
    for path in changed_files:
        if not any(fnmatch(path, pattern) for pattern in allowed_patterns):
            return False
    return True


def _write_durable_strategy_learning(*, mathgen_logs: Path, active_recipe, outcome_row):
    if not active_recipe.get('issue_id') or not active_recipe.get('strategy_key'):
        return

    paths = _mathgen_log_paths(mathgen_logs)
    error_category = _normalize_error_category(active_recipe.get('error_category', ''))
    strategy_summary = active_recipe.get('strategy', '')
    changed_files = outcome_row.get('changed_files', [])

    if outcome_row.get('outcome') == 'successful':
        _append_jsonl(
            paths['change_history'],
            {
                'timestamp': outcome_row['timestamp'],
                'description': (
                    f"Auto recipe success for {active_recipe.get('issue_id', '')}: "
                    f"{active_recipe.get('strategy_key', '')} validated by {outcome_row.get('verify_mode', '')}"
                ),
                'error_codes_addressed': [error_category] if error_category else [],
                'files_changed': changed_files,
                'strategy': strategy_summary,
                'strategy_key': active_recipe.get('strategy_key', ''),
                'source': 'auto_recipe_controller',
            },
        )
        _append_jsonl(
            paths['lessons_learned'],
            {
                'timestamp': outcome_row['timestamp'],
                'type': 'fix_applied',
                'description': (
                    f"Validated controlled recipe success for {active_recipe.get('issue_id', '')}. "
                    f"Strategy {active_recipe.get('strategy_key', '')} stayed in scope and passed {outcome_row.get('verify_mode', '')}."
                ),
                'error_codes': [error_category] if error_category else [],
                'strategy': strategy_summary,
                'strategy_key': active_recipe.get('strategy_key', ''),
                'source': 'auto_recipe_controller',
                'result': 'validated_success',
            },
        )
        return

    _append_jsonl(
        paths['lessons_learned'],
        {
            'timestamp': outcome_row['timestamp'],
            'type': 'anti_pattern',
            'description': outcome_row.get('reason', ''),
            'error_codes': [error_category] if error_category else [],
            'strategy': strategy_summary,
            'strategy_key': active_recipe.get('strategy_key', ''),
            'source': 'auto_recipe_controller',
            'result': 'validated_failure',
            'changed_files': changed_files,
        },
    )


def finalize_active_recipe(*, artifact_root: Path, mathgen_logs: Path, run_id: str, verify_mode: str, gate_pass: bool, changed_files):
    paths = _outcome_paths(artifact_root, run_id)
    active = _read_json(paths['active_recipe_json'], {}) or {}
    if not active or not active.get('issue_id') or active.get('status') != 'selected':
        return {'finalized': False, 'reason': 'No selected active recipe to finalize.'}
    normalized_files = sorted({path.replace('\\', '/') for path in changed_files if path})
    if not normalized_files:
        return {'finalized': False, 'reason': 'No changed files detected for the active recipe.'}
    scope_ok = _scope_ok(normalized_files, active.get('allowed_edit_scope', []))
    outcome = 'validated_success' if gate_pass and scope_ok else 'validated_failure'
    has_side_effect = not gate_pass
    reason = 'Latest gate passed and all changed files stayed within the allowed recipe scope.'
    if not scope_ok:
        reason = 'Changed files escaped the allowed edit scope for the active recipe.'
    elif not gate_pass:
        reason = 'Latest verify cycle failed after applying files tied to the active recipe.'

    outcomes = _read_jsonl(paths['strategy_outcomes'])
    duplicate = None
    for row in reversed(outcomes):
        if row.get('issue_id') == active.get('issue_id') and row.get('strategy_key') == active.get('strategy_key') and row.get('event') == outcome:
            if sorted(row.get('changed_files', [])) == normalized_files and row.get('verify_mode') == verify_mode:
                duplicate = row
                break
    if duplicate is not None:
        return {'finalized': False, 'reason': 'This strategy outcome was already recorded.'}

    row = {
        'timestamp': _now_iso(),
        'run_id': run_id,
        'issue_id': active.get('issue_id', ''),
        'error_category': active.get('error_category', ''),
        'topic': active.get('topic', ''),
        'strategy_key': active.get('strategy_key', ''),
        'strategy': active.get('strategy', ''),
        'event': outcome,
        'outcome': 'successful' if outcome == 'validated_success' else 'failed',
        'blocked': False,
        'has_side_effect': has_side_effect,
        'counts_toward_blacklist': (not scope_ok) or has_side_effect,
        'source': 'auto_recipe_controller',
        'reason': reason,
        'verify_mode': verify_mode,
        'gate_pass': gate_pass,
        'scope_ok': scope_ok,
        'changed_files': normalized_files,
    }
    _append_jsonl(paths['strategy_outcomes'], row)
    _write_durable_strategy_learning(mathgen_logs=mathgen_logs, active_recipe=active, outcome_row=row)

    active['status'] = outcome
    active['finalized_at'] = row['timestamp']
    active['last_outcome'] = row
    _write_json(paths['active_recipe_json'], active)
    _write_text(paths['active_recipe_md'], _active_recipe_markdown(active))
    if run_id:
        _write_json(paths['run_active_recipe_json'], active)
        _write_text(paths['run_active_recipe_md'], _active_recipe_markdown(active))
    return {'finalized': True, 'outcome': row}


_AUTO_APPLY_EXECUTORS = {
    'wrong_numeric_answer': 'tools.auto_apply_wrong_numeric',
    'benchmark_contract_drift': 'tools.auto_apply_contract_drift',
}


def execute_active_recipe(*, artifact_root: Path, run_id: str, dry_run: bool = True):
    """Execute the active recipe's auto-apply executor if one is registered.

    Returns a result dict with keys: executed, executor, topic, apply_result.
    """
    active = _read_json(artifact_root / 'active_recipe.json', {}) or {}
    if not active or active.get('status') != 'selected':
        return {'executed': False, 'reason': 'No selected active recipe to execute.'}

    category = _normalize_error_category(active.get('error_category', ''))
    module_name = _AUTO_APPLY_EXECUTORS.get(category)
    if module_name is None:
        return {'executed': False, 'reason': f'No auto-apply executor registered for category: {category}'}

    topic = active.get('topic', '')
    if not topic:
        return {'executed': False, 'reason': 'Active recipe has no topic specified.'}

    import importlib
    mod = importlib.import_module(module_name)
    diagnosis = mod.diagnose_benchmark(topic)
    if 'error' in diagnosis:
        return {'executed': False, 'reason': diagnosis['error']}

    if diagnosis['auto_fixable'] == 0:
        return {
            'executed': False,
            'reason': f'No auto-fixable cases found for {topic}.',
            'diagnosis': {k: diagnosis[k] for k in ['total_cases', 'passing', 'auto_fixable', 'escalations']},
        }

    apply_result = mod.apply_fix(topic, dry_run=dry_run, artifact_root=artifact_root)
    return {
        'executed': True,
        'executor': module_name,
        'topic': topic,
        'dry_run': dry_run,
        'apply_result': apply_result,
    }


def main():
    parser = argparse.ArgumentParser(description='Select, execute, and finalize controlled fix recipes for the 10h runner')
    subparsers = parser.add_subparsers(dest='command', required=True)

    select_parser = subparsers.add_parser('select')
    select_parser.add_argument('--artifact-root', default=str(DEFAULT_ARTIFACT_ROOT))
    select_parser.add_argument('--mathgen-logs', default=str(DEFAULT_MATHGEN_LOGS))
    select_parser.add_argument('--run-id', default='')

    execute_parser = subparsers.add_parser('execute')
    execute_parser.add_argument('--artifact-root', default=str(DEFAULT_ARTIFACT_ROOT))
    execute_parser.add_argument('--run-id', default='')
    execute_parser.add_argument('--dry-run', action='store_true', default=False)

    finalize_parser = subparsers.add_parser('finalize')
    finalize_parser.add_argument('--artifact-root', default=str(DEFAULT_ARTIFACT_ROOT))
    finalize_parser.add_argument('--mathgen-logs', default=str(DEFAULT_MATHGEN_LOGS))
    finalize_parser.add_argument('--run-id', default='')
    finalize_parser.add_argument('--verify-mode', required=True)
    finalize_parser.add_argument('--gate-pass', required=True, choices=['true', 'false'])
    finalize_parser.add_argument('--changed-file', action='append', default=[])

    args = parser.parse_args()
    artifact_root = Path(args.artifact_root)

    if args.command == 'select':
        result = select_active_recipe(artifact_root=artifact_root, run_id=args.run_id)
    elif args.command == 'execute':
        result = execute_active_recipe(artifact_root=artifact_root, run_id=args.run_id, dry_run=args.dry_run)
    else:
        mathgen_logs = Path(args.mathgen_logs)
        result = finalize_active_recipe(
            artifact_root=artifact_root,
            mathgen_logs=mathgen_logs,
            run_id=args.run_id,
            verify_mode=args.verify_mode,
            gate_pass=(args.gate_pass == 'true'),
            changed_files=args.changed_file,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
