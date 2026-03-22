# School-first / Teacher-first PRD

Version: 0.1
Date: 2026-03-21
Scope: School-first / Teacher-first product line
Status: Phase 0 started, implementation in progress

## A. 現況分析

- Current backend truth source is [server.py](server.py): account, student, subscription, attempts, parent-report registry, snapshot, adaptive mastery.
- Parent ownership is already enforced server-side through `account_id -> student_id` checks in parent-report and snapshot endpoints.
- Teacher/class scope is not complete in the shipped baseline. The current worktree contains partial class schema and API drafts in [server.py](server.py) and [learning/class_report.py](learning/class_report.py), but they are not yet fully validated.
- Existing learning analytics are student-centric: [learning/analytics.py](learning/analytics.py), [learning/parent_report.py](learning/parent_report.py), [adaptive_mastery.py](adaptive_mastery.py).
- Existing frontend surfaces are parent/student heavy. No dedicated teacher dashboard or admin dashboard MVP exists yet.
- Existing security work already hardened parent-report writeback, login rate limiting, bootstrap token exchange, and admin audit flows. Protected auth/payment logic should not be rewritten in early phases.

## B. Phase-by-Phase Plan

### Phase 0: 現況分析 + 文件規格 + RBAC 邊界
- Produce governance, PRD, RBAC, protected-path, security audit, assumptions, and iteration docs.
- Define school-first roles, entitlements, event truth source, and acceptable assumptions.
- Confirm affected files and protected areas before implementation.

### Phase 1: Mock Data
- Add deterministic mock data for 1 admin, 2 teachers, 116 students, 116 parents, pre/post assessments, answer records, interventions, parent reports, class analytics, and admin rollups.
- Cover improve / flat / regress cohorts and common error types.

### Phase 2: Schema / Types / Event Model
- Add school-first types under `src/types/`.
- Add explicit question metadata, assessment, answer record, intervention, before/after comparison types.
- Add DB migration for school/class/role tables using additive, non-breaking schema changes.

### Phase 3: UI MVP
- Build Teacher Dashboard MVP.
- Build Parent View MVP.
- Build Admin Dashboard MVP.
- All pages are mock-first with optional real backend wiring.

### Phase 4: Analytics Engine
- Add class analytics engine.
- Add before/after analytics engine using `equivalent_group_id`, `skill_tag`, `knowledge_point`, and difficulty proximity.
- Add parent-readable and teacher-readable summaries.

### Phase 5: 真實資料串接
- Connect teacher dashboard to real class endpoints.
- Keep pre/post event model traceable to answer records and question metadata.

### Phase 6: 安全整改 + 後端 entitlement 驗證
- Enforce teacher/class scope server-side.
- Avoid any client-side authority.
- Audit sensitive sync/token flows without destabilizing protected auth/payment paths.

### Phase 7: 回歸測試 + 驗收報告 + 後續建議
- Run targeted backend tests.
- Run verify gates.
- Update school-first iteration report and rollback notes.

## C. 受影響檔案清單

- [server.py](server.py)
- [learning/parent_report.py](learning/parent_report.py)
- [learning/analytics.py](learning/analytics.py)
- [adaptive_mastery.py](adaptive_mastery.py)
- [tests/test_report_snapshot_endpoints.py](tests/test_report_snapshot_endpoints.py)
- [tests/test_learning_analytics.py](tests/test_learning_analytics.py)
- [src/telemetry/attempt_event.ts](src/telemetry/attempt_event.ts)
- [src/telemetry/attempt_store.ts](src/telemetry/attempt_store.ts)
- [docs/rbac_entitlement_school_first.md](docs/rbac_entitlement_school_first.md)
- [reports/latest_iteration_report.md](reports/latest_iteration_report.md)
- [logs/change_history.jsonl](logs/change_history.jsonl)
- [logs/lessons_learned.jsonl](logs/lessons_learned.jsonl)

## D. 新增檔案清單

- [docs/automation_governance_school_first.md](docs/automation_governance_school_first.md)
- [docs/security_secret_audit.md](docs/security_secret_audit.md)
- [docs/protected_paths_school_first.md](docs/protected_paths_school_first.md)
- [docs/assumptions_school_first.md](docs/assumptions_school_first.md)
- [docs/rbac_test_cases.md](docs/rbac_test_cases.md)
- [docs/data_model_school_first.md](docs/data_model_school_first.md)
- [docs/event_model_school_first.md](docs/event_model_school_first.md)
- [docs/teacher_dashboard_mvp.md](docs/teacher_dashboard_mvp.md)
- [docs/parent_view_mvp.md](docs/parent_view_mvp.md)
- [docs/admin_dashboard_mvp.md](docs/admin_dashboard_mvp.md)
- [docs/before_after_analytics_spec.md](docs/before_after_analytics_spec.md)
- [reports/school_first_iteration_report.md](reports/school_first_iteration_report.md)
- [logs/change_history_school_first.jsonl](logs/change_history_school_first.jsonl)

## E. 風險點

- Protected auth and payment flows exist; touching them too early can regress login, subscription, or parent-report flows.
- `server.py` is monolithic. Large edits increase regression risk. All backend changes must be additive and route-specific.
- Existing analytics tables do not yet encode pre-test/post-test/intervention as first-class records. Phase 1-4 will therefore be mock-first and schema-first before real-data coupling.
- docs/dist mirror rules still apply for any new docs-served UI files.
- The current worktree already contains partial school-first backend changes. All further edits must extend and validate them, not replace them blindly.

## F. Phase 0 具體工作項目

1. Publish governance, protected paths, assumptions, and security audit documents.
2. Lock RBAC boundary: parent owns only child data; teacher owns only class data; admin has full scope.
3. Define school-first data model and event model.
4. Define teacher/parent/admin MVP surfaces and before/after analytics rules.
5. Record current risks, rollout strategy, and test contract.
6. Proceed to mock-first implementation without changing protected auth/payment logic.

## Acceptance Criteria For This Iteration

- Required school-first planning docs exist in repo.
- Assumptions are explicit and conservative.
- RBAC tests and event traceability expectations are documented before code changes.
- Subsequent phases can execute without reopening product ambiguity.