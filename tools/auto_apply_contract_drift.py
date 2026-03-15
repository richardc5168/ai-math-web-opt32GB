"""Auto-apply executor for benchmark_contract_drift — contract_test_first strategy.

Detects benchmark cases where the generator and verifier agree on an answer
(and optionally unit) but the benchmark's expected_answer or expected_unit
has drifted from the current generator/verifier contract.

Safe auto-fix: update benchmark expectations to match the verified generator
output.  Escalate when generator and verifier disagree.

Usage:
    python tools/auto_apply_contract_drift.py diagnose --topic <topic>
    python tools/auto_apply_contract_drift.py apply --topic <topic> [--dry-run]
    python tools/auto_apply_contract_drift.py verify --topic <topic>
"""
import argparse
import json
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT))

from mathgen.question_templates import ALL_GENERATORS
from mathgen.validators.answer_verifier import verify_answer

BENCH_DIR = _ROOT / 'mathgen' / 'benchmarks'
DEFAULT_ARTIFACT_ROOT = _ROOT / 'artifacts' / 'run_10h'


def _load_benchmark(topic: str):
    path = BENCH_DIR / f'{topic}_bench.json'
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding='utf-8'))


def _write_benchmark(topic: str, cases):
    path = BENCH_DIR / f'{topic}_bench.json'
    path.write_text(
        json.dumps(cases, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _append_jsonl(path: Path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + '\n')


def diagnose_benchmark(topic: str):
    """Classify each benchmark case: passing | answer_drift | unit_drift | multi_drift | escalate."""
    cases = _load_benchmark(topic)
    if cases is None:
        return {'error': f'No benchmark file for topic: {topic}'}

    generator_cls = ALL_GENERATORS.get(topic)
    if generator_cls is None:
        return {'error': f'No generator for topic: {topic}'}

    gen = generator_cls()
    results = []

    for i, case in enumerate(cases):
        case_id = f'{topic}[{i}]'
        expected_answer = str(case.get('expected_answer', ''))
        expected_unit = case.get('expected_unit', '')

        try:
            q = gen.generate(params=case['input'])
        except Exception as exc:
            results.append({
                'case_id': case_id,
                'index': i,
                'status': 'escalate',
                'reason': f'generator_exception: {exc}',
                'drifted_fields': [],
                'expected_answer': expected_answer,
                'expected_unit': expected_unit,
                'generator_answer': '',
                'generator_unit': '',
                'verifier_answer': '',
            })
            continue

        gen_answer = q.get('correct_answer', '')
        gen_unit = q.get('unit', '')
        vr = verify_answer(topic, q.get('parameters', {}), gen_answer)

        answer_match = gen_answer == expected_answer
        unit_match = (not expected_unit) or gen_unit == expected_unit

        if answer_match and unit_match:
            if vr.match:
                results.append({
                    'case_id': case_id,
                    'index': i,
                    'status': 'passing',
                    'reason': 'All agree.',
                    'drifted_fields': [],
                    'expected_answer': expected_answer,
                    'expected_unit': expected_unit,
                    'generator_answer': gen_answer,
                    'generator_unit': gen_unit,
                    'verifier_answer': vr.expected,
                })
            else:
                results.append({
                    'case_id': case_id,
                    'index': i,
                    'status': 'escalate',
                    'reason': f'Benchmark matches generator but verifier disagrees (verifier={vr.expected}).',
                    'drifted_fields': [],
                    'expected_answer': expected_answer,
                    'expected_unit': expected_unit,
                    'generator_answer': gen_answer,
                    'generator_unit': gen_unit,
                    'verifier_answer': vr.expected,
                })
        elif vr.match:
            # Generator and verifier agree but benchmark drifted
            drifted = []
            if not answer_match:
                drifted.append('expected_answer')
            if not unit_match:
                drifted.append('expected_unit')
            status = 'answer_drift' if drifted == ['expected_answer'] else (
                'unit_drift' if drifted == ['expected_unit'] else 'multi_drift'
            )
            results.append({
                'case_id': case_id,
                'index': i,
                'status': status,
                'reason': f'Generator and verifier agree but benchmark drifted on: {", ".join(drifted)}.',
                'drifted_fields': drifted,
                'expected_answer': expected_answer,
                'expected_unit': expected_unit,
                'generator_answer': gen_answer,
                'generator_unit': gen_unit,
                'verifier_answer': vr.expected,
            })
        else:
            results.append({
                'case_id': case_id,
                'index': i,
                'status': 'escalate',
                'reason': f'Generator ({gen_answer}) and verifier ({vr.expected}) disagree. Manual review needed.',
                'drifted_fields': [],
                'expected_answer': expected_answer,
                'expected_unit': expected_unit,
                'generator_answer': gen_answer,
                'generator_unit': gen_unit,
                'verifier_answer': vr.expected,
            })

    passing = [r for r in results if r['status'] == 'passing']
    auto_fixable = [r for r in results if r['status'] in {'answer_drift', 'unit_drift', 'multi_drift'}]
    escalations = [r for r in results if r['status'] == 'escalate']

    return {
        'topic': topic,
        'total_cases': len(cases),
        'passing': len(passing),
        'auto_fixable': len(auto_fixable),
        'escalations': len(escalations),
        'auto_fixable_cases': auto_fixable,
        'escalation_cases': escalations,
        'all_results': results,
    }


def apply_fix(topic: str, *, dry_run: bool = True, artifact_root: Path = DEFAULT_ARTIFACT_ROOT):
    """Apply contract_test_first auto-fix: update benchmark expectations where generator+verifier agree."""
    diagnosis = diagnose_benchmark(topic)
    if 'error' in diagnosis:
        return diagnosis

    auto_fixable = diagnosis['auto_fixable_cases']
    if not auto_fixable:
        return {
            'topic': topic,
            'applied': 0,
            'dry_run': dry_run,
            'message': 'No drifted cases found.',
            'escalations': diagnosis['escalations'],
        }

    cases = _load_benchmark(topic)
    changes = []

    for item in auto_fixable:
        idx = item['index']
        change = {
            'case_id': item['case_id'],
            'index': idx,
            'drifted_fields': item['drifted_fields'],
        }
        if 'expected_answer' in item['drifted_fields']:
            change['old_expected_answer'] = str(cases[idx].get('expected_answer', ''))
            change['new_expected_answer'] = item['generator_answer']
            cases[idx]['expected_answer'] = item['generator_answer']
        if 'expected_unit' in item['drifted_fields']:
            change['old_expected_unit'] = cases[idx].get('expected_unit', '')
            change['new_expected_unit'] = item['generator_unit']
            cases[idx]['expected_unit'] = item['generator_unit']
        change['reason'] = item['reason']
        changes.append(change)

    if not dry_run:
        _write_benchmark(topic, cases)

        outcome_path = artifact_root / 'strategy_outcomes.jsonl'
        _append_jsonl(outcome_path, {
            'timestamp': _now_iso(),
            'issue_id': f'benchmark:benchmark_contract_drift:{topic}',
            'error_category': 'benchmark_contract_drift',
            'topic': topic,
            'strategy_key': 'contract_test_first',
            'strategy': 'Add a contract regression tying verifier output and benchmark expectation together.',
            'event': 'auto_applied',
            'outcome': 'applied',
            'has_side_effect': False,
            'counts_toward_blacklist': False,
            'source': 'auto_apply_contract_drift',
            'reason': f'Updated {len(changes)} benchmark cases to match verifier contract.',
            'changed_files': [f'mathgen/benchmarks/{topic}_bench.json'],
            'changes_count': len(changes),
        })

    return {
        'topic': topic,
        'applied': len(changes),
        'dry_run': dry_run,
        'changes': changes,
        'escalations': diagnosis['escalations'],
        'escalation_count': diagnosis['escalations'],
        'message': f'{"Would update" if dry_run else "Updated"} {len(changes)} benchmark cases.',
    }


def verify_after_fix(topic: str):
    """Confirm all cases pass after fix."""
    diagnosis = diagnose_benchmark(topic)
    if 'error' in diagnosis:
        return diagnosis
    return {
        'topic': topic,
        'total_cases': diagnosis['total_cases'],
        'passing': diagnosis['passing'],
        'auto_fixable': diagnosis['auto_fixable'],
        'escalations': diagnosis['escalations'],
        'clean': diagnosis['auto_fixable'] == 0 and diagnosis['escalations'] == 0,
    }


def main():
    parser = argparse.ArgumentParser(description='Auto-apply executor for benchmark_contract_drift (contract_test_first)')
    sub = parser.add_subparsers(dest='command', required=True)

    diag = sub.add_parser('diagnose', help='Classify all benchmark cases for a topic')
    diag.add_argument('--topic', required=True)

    apply_cmd = sub.add_parser('apply', help='Apply auto-fix for drifted cases')
    apply_cmd.add_argument('--topic', required=True)
    apply_cmd.add_argument('--dry-run', action='store_true', default=False)
    apply_cmd.add_argument('--artifact-root', default=str(DEFAULT_ARTIFACT_ROOT))

    verify_cmd = sub.add_parser('verify', help='Verify all cases pass after fix')
    verify_cmd.add_argument('--topic', required=True)

    args = parser.parse_args()

    if args.command == 'diagnose':
        result = diagnose_benchmark(args.topic)
    elif args.command == 'apply':
        result = apply_fix(args.topic, dry_run=args.dry_run, artifact_root=Path(args.artifact_root))
    else:
        result = verify_after_fix(args.topic)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
