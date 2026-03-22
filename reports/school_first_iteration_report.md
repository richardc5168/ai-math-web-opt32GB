# School-first Iteration Report

Date: 2026-03-21
Status: active

## Current Goal

Stand up School-first / Teacher-first foundations in required order: governance -> mock data -> schema/types -> UI MVP -> analytics -> real-data wiring -> security validation.

## Completed This Iteration So Far

- Produced Phase 0 planning/governance documents
- Established school-first assumptions and protected-path boundaries
- Confirmed current repo baseline and existing partial teacher/class backend worktree changes

## Files Added

- docs/school_first_prd.md
- docs/automation_governance_school_first.md
- docs/security_secret_audit.md
- docs/protected_paths_school_first.md
- docs/assumptions_school_first.md
- docs/rbac_test_cases.md
- docs/data_model_school_first.md
- docs/event_model_school_first.md
- docs/teacher_dashboard_mvp.md
- docs/parent_view_mvp.md
- docs/admin_dashboard_mvp.md
- docs/before_after_analytics_spec.md
- reports/school_first_iteration_report.md
- logs/change_history_school_first.jsonl

## In Progress

- Phase 1 mock data
- Phase 2 types/schema
- Teacher class backend completion and validation

## Risks

- `server.py` already has partial uncommitted school-first changes; they must be completed carefully.
- Existing login/subscription/payment flows remain protected.
- Real before/post traceability needs dedicated event model and likely new storage beyond current attempts schema.

## Next Step

Create mock fixtures and school-first types, then finish and test teacher/class backend on top of the existing partial worktree.