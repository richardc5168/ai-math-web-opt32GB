# Automation Governance: School-first

## Goal

Keep long-run automation aligned with School-first / Teacher-first priorities while avoiding unsafe edits to protected auth/payment paths.

## Governance Rules

1. P0 order is fixed: RBAC -> event truth source -> secret hardening -> teacher/class evidence chain.
2. Mock-first before real data.
3. No client-side authority for parent/teacher/admin visibility.
4. Before/after reports must be traceable to question metadata and answer records.
5. Protected paths may be audited and documented before Phase 6, but not behaviorally rewritten.

## Mandatory Writeback

- Update [reports/school_first_iteration_report.md](reports/school_first_iteration_report.md)
- Update [docs/assumptions_school_first.md](docs/assumptions_school_first.md)
- Update [logs/change_history_school_first.jsonl](logs/change_history_school_first.jsonl)
- Also update root [logs/change_history.jsonl](logs/change_history.jsonl), [logs/lessons_learned.jsonl](logs/lessons_learned.jsonl), and [reports/latest_iteration_report.md](reports/latest_iteration_report.md) for meaningful production-affecting work

## Validation Ladder

1. File-level syntax or import validation
2. Targeted unit/integration tests for changed modules
3. `python scripts/verify_all.py`
4. `python tools/validate_all_elementary_banks.py` when docs-served JS/HTML is touched
5. Remote cross-validate only after deploy parity is expected

## Rollback Rule

If a school-first change threatens parent-report, login, subscription, or docs/dist parity, revert only the new school-first slice, not unrelated hardened flows.