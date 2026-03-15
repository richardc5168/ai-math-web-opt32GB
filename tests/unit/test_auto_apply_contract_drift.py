"""Tests for the benchmark_contract_drift auto-apply executor."""
import json
from pathlib import Path
from unittest.mock import patch

from tools.auto_apply_contract_drift import apply_fix, diagnose_benchmark, verify_after_fix


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def _read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def _read_jsonl(path: Path):
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


class _MockVerifyResult:
    def __init__(self, *, match, expected, actual):
        self.topic = 'decimal_word_problem'
        self.match = match
        self.expected = expected
        self.actual = actual
        self.errors = []
        self.invariants_checked = 0
        self.invariants_passed = 0


class _MockGenerator:
    def generate(self, params=None):
        return {
            'correct_answer': params.get('_mock_answer', '2.3'),
            'unit': params.get('_mock_unit', '公升'),
            'parameters': params,
            'topic': 'decimal_word_problem',
            'steps': [],
        }


def _mock_verify_agree(topic, params, actual_answer):
    return _MockVerifyResult(match=True, expected=actual_answer, actual=actual_answer)


def _mock_verify_disagree(topic, params, actual_answer):
    return _MockVerifyResult(match=False, expected='WRONG', actual=actual_answer)


# ----------- diagnose tests -----------

def test_diagnose_passing_when_all_agree(tmp_path):
    bench_dir = tmp_path / 'mathgen' / 'benchmarks'
    _write_json(bench_dir / 'decimal_word_problem_bench.json', [
        {'input': {'_mock_answer': '2.3', '_mock_unit': '公升'}, 'expected_answer': '2.3', 'expected_unit': '公升'},
    ])

    with patch('tools.auto_apply_contract_drift.BENCH_DIR', bench_dir), \
         patch('tools.auto_apply_contract_drift.ALL_GENERATORS', {'decimal_word_problem': _MockGenerator}), \
         patch('tools.auto_apply_contract_drift.verify_answer', _mock_verify_agree):
        result = diagnose_benchmark('decimal_word_problem')

    assert result['passing'] == 1
    assert result['auto_fixable'] == 0
    assert result['escalations'] == 0


def test_diagnose_detects_answer_drift(tmp_path):
    bench_dir = tmp_path / 'mathgen' / 'benchmarks'
    _write_json(bench_dir / 'decimal_word_problem_bench.json', [
        {'input': {'_mock_answer': '2.3', '_mock_unit': '公升'}, 'expected_answer': '2.30', 'expected_unit': '公升'},
    ])

    with patch('tools.auto_apply_contract_drift.BENCH_DIR', bench_dir), \
         patch('tools.auto_apply_contract_drift.ALL_GENERATORS', {'decimal_word_problem': _MockGenerator}), \
         patch('tools.auto_apply_contract_drift.verify_answer', _mock_verify_agree):
        result = diagnose_benchmark('decimal_word_problem')

    assert result['auto_fixable'] == 1
    assert result['auto_fixable_cases'][0]['status'] == 'answer_drift'
    assert result['auto_fixable_cases'][0]['drifted_fields'] == ['expected_answer']


def test_diagnose_detects_unit_drift(tmp_path):
    bench_dir = tmp_path / 'mathgen' / 'benchmarks'
    _write_json(bench_dir / 'decimal_word_problem_bench.json', [
        {'input': {'_mock_answer': '2.3', '_mock_unit': '公升'}, 'expected_answer': '2.3', 'expected_unit': '毫升'},
    ])

    with patch('tools.auto_apply_contract_drift.BENCH_DIR', bench_dir), \
         patch('tools.auto_apply_contract_drift.ALL_GENERATORS', {'decimal_word_problem': _MockGenerator}), \
         patch('tools.auto_apply_contract_drift.verify_answer', _mock_verify_agree):
        result = diagnose_benchmark('decimal_word_problem')

    assert result['auto_fixable'] == 1
    assert result['auto_fixable_cases'][0]['status'] == 'unit_drift'
    assert result['auto_fixable_cases'][0]['drifted_fields'] == ['expected_unit']


def test_diagnose_detects_multi_drift(tmp_path):
    bench_dir = tmp_path / 'mathgen' / 'benchmarks'
    _write_json(bench_dir / 'decimal_word_problem_bench.json', [
        {'input': {'_mock_answer': '2.3', '_mock_unit': '公升'}, 'expected_answer': '2.30', 'expected_unit': '毫升'},
    ])

    with patch('tools.auto_apply_contract_drift.BENCH_DIR', bench_dir), \
         patch('tools.auto_apply_contract_drift.ALL_GENERATORS', {'decimal_word_problem': _MockGenerator}), \
         patch('tools.auto_apply_contract_drift.verify_answer', _mock_verify_agree):
        result = diagnose_benchmark('decimal_word_problem')

    assert result['auto_fixable'] == 1
    assert result['auto_fixable_cases'][0]['status'] == 'multi_drift'
    assert set(result['auto_fixable_cases'][0]['drifted_fields']) == {'expected_answer', 'expected_unit'}


def test_diagnose_escalates_when_verifier_disagrees(tmp_path):
    bench_dir = tmp_path / 'mathgen' / 'benchmarks'
    _write_json(bench_dir / 'decimal_word_problem_bench.json', [
        {'input': {'_mock_answer': '2.3', '_mock_unit': '公升'}, 'expected_answer': '999', 'expected_unit': '公升'},
    ])

    with patch('tools.auto_apply_contract_drift.BENCH_DIR', bench_dir), \
         patch('tools.auto_apply_contract_drift.ALL_GENERATORS', {'decimal_word_problem': _MockGenerator}), \
         patch('tools.auto_apply_contract_drift.verify_answer', _mock_verify_disagree):
        result = diagnose_benchmark('decimal_word_problem')

    assert result['escalations'] == 1
    assert result['auto_fixable'] == 0


# ----------- apply tests -----------

def test_apply_fixes_answer_and_unit_drift(tmp_path):
    bench_dir = tmp_path / 'mathgen' / 'benchmarks'
    artifact_root = tmp_path / 'artifacts' / 'run_10h'
    _write_json(bench_dir / 'decimal_word_problem_bench.json', [
        {'input': {'_mock_answer': '2.3', '_mock_unit': '公升'}, 'expected_answer': '2.30', 'expected_unit': '毫升'},
        {'input': {'_mock_answer': '5', '_mock_unit': '公里'}, 'expected_answer': '5', 'expected_unit': '公里'},
    ])

    with patch('tools.auto_apply_contract_drift.BENCH_DIR', bench_dir), \
         patch('tools.auto_apply_contract_drift.ALL_GENERATORS', {'decimal_word_problem': _MockGenerator}), \
         patch('tools.auto_apply_contract_drift.verify_answer', _mock_verify_agree):
        result = apply_fix('decimal_word_problem', dry_run=False, artifact_root=artifact_root)

    assert result['applied'] == 1
    updated = _read_json(bench_dir / 'decimal_word_problem_bench.json')
    assert updated[0]['expected_answer'] == '2.3'
    assert updated[0]['expected_unit'] == '公升'
    assert updated[1]['expected_answer'] == '5'  # untouched

    outcomes = _read_jsonl(artifact_root / 'strategy_outcomes.jsonl')
    assert outcomes[-1]['strategy_key'] == 'contract_test_first'
    assert outcomes[-1]['event'] == 'auto_applied'


def test_apply_dry_run_does_not_write(tmp_path):
    bench_dir = tmp_path / 'mathgen' / 'benchmarks'
    _write_json(bench_dir / 'decimal_word_problem_bench.json', [
        {'input': {'_mock_answer': '2.3', '_mock_unit': '公升'}, 'expected_answer': '2.30', 'expected_unit': '公升'},
    ])

    with patch('tools.auto_apply_contract_drift.BENCH_DIR', bench_dir), \
         patch('tools.auto_apply_contract_drift.ALL_GENERATORS', {'decimal_word_problem': _MockGenerator}), \
         patch('tools.auto_apply_contract_drift.verify_answer', _mock_verify_agree):
        result = apply_fix('decimal_word_problem', dry_run=True, artifact_root=tmp_path / 'artifacts')

    assert result['applied'] == 1
    assert result['dry_run'] is True
    original = _read_json(bench_dir / 'decimal_word_problem_bench.json')
    assert original[0]['expected_answer'] == '2.30'  # unchanged


# ----------- verify_after_fix tests -----------

def test_verify_after_fix_reports_clean(tmp_path):
    bench_dir = tmp_path / 'mathgen' / 'benchmarks'
    _write_json(bench_dir / 'decimal_word_problem_bench.json', [
        {'input': {'_mock_answer': '2.3', '_mock_unit': '公升'}, 'expected_answer': '2.3', 'expected_unit': '公升'},
    ])

    with patch('tools.auto_apply_contract_drift.BENCH_DIR', bench_dir), \
         patch('tools.auto_apply_contract_drift.ALL_GENERATORS', {'decimal_word_problem': _MockGenerator}), \
         patch('tools.auto_apply_contract_drift.verify_answer', _mock_verify_agree):
        result = verify_after_fix('decimal_word_problem')

    assert result['clean'] is True
