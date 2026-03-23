# Iteration R41  EXP-P4-07: Contract Tests

## Status: COMPLETE

## Objective
Add comprehensive API contract tests to `tests/contract/` that validate Pydantic request schema constraints and endpoint registration, preventing silent API breaking changes.

## Main Hypothesis
Adding API contract tests validates request/response schemas and prevents API breaking changes by catching constraint violations, missing routes, and accidental route removals.

## Why This One
Phase 4 Stage 3 starts with contract tests (P4-07) — lowest risk (test-only, zero production changes), highest long-term value (prevents regressions in all 48+ endpoints). Foundation for Stage 3's remaining experiments (schema migration, legacy cleanup).

## Files Inspected
- routers/auth.py (4 Pydantic models, 5 endpoints)
- routers/learning.py (5 Pydantic models, 10 endpoints)
- server.py (17 Pydantic models, 30+ endpoints)
- tests/contract/ (only README.md existed)
- tests/test_school_first_ui_contract.py (existing UI contract pattern)

## Files Changed
- tests/contract/__init__.py: Created (empty, enables pytest discovery)
- tests/contract/test_request_schemas.py: 65 new tests — validates all 26 Pydantic request models across auth, learning, and server modules (happy path, missing fields, constraint violations, defaults)
- tests/contract/test_endpoint_contracts.py: 46 new tests — validates endpoint registration for auth (5), learning (10), core flow (5), engine (7), teacher (5), reports (6), parent registry (2), health (2), admin (4), plus response shape tests for /health, /healthz, /v1/knowledge/graph, plus minimum route count guard (≥45)

## Experiment Design
1. Import all 26 Pydantic request models directly (no server/DB dependency)
2. Test valid construction, default values, field constraints (min_length, ge/le), missing required fields
3. Introspect `app.routes` to verify all documented endpoints exist with correct HTTP methods
4. Use TestClient for health/knowledge-graph response shape validation
5. Add route count guard (≥45) to detect mass route removal

## Tests Run
- Contract tests only: 111 passed, 0 failures
- Full regression: 1246 passed, 0 failures

## Metrics Compared
- Tests: 1135 → 1246 (+111)
- Contract test coverage: 0 → 111 (26 Pydantic models + 48 endpoint routes + 3 response shapes + 1 count guard)
- Pydantic models covered: 0 → 26 (all request models)
- Endpoint registration coverage: 0 → 48+ routes verified

## Results
All 111 new contract tests pass. Full regression green (1246 tests, 0 failures). No production code changed.

## Decision: KEEP

## Lessons Learned
- FastAPI registers separate APIRoute objects for GET and POST on the same path (e.g., /v1/teacher/classes). Route introspection must merge methods per path to avoid overwrites.
- Pure Pydantic model tests are fast (~0.1s) and catch constraint drift without needing DB or server startup.
- Parametrized route existence tests scale well — adding new endpoints to the contract list is a one-liner.

## Next Candidates
1. R42/EXP-P4-08: Schema Migration Consolidation — move inline CREATE TABLE from server.py init_db() into numbered migration files
2. R43/EXP-P4-09: Legacy File Cleanup — archive 40+ unused math_cli_v*.py and mathOK*.py files
