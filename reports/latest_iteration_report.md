# Iteration R40  EXP-P4-06: Learning Router Extraction

## Status: COMPLETE

## Hypothesis
Extracting 10 learning/analytics endpoints from server.py into `routers/learning.py` using FastAPI APIRouter further reduces server.py and groups related functionality.

## Changes Made
- routers/learning.py: Created with APIRouter (no prefix, tags=["learning"]). Moved 5 Pydantic models (WeeklyReportRequest, PracticeNextRequest, RemediationPlanRequest, BeforeAfterRequest, ConceptNextRequest), 10 handler functions across 4 URL prefixes (/v1/learning/*, /v1/student/*, /v1/practice/*, /v1/adaptive/*), 2 helper functions (_skill_snapshot_from_analytics, _build_concept_question_pool). Uses lazy `import server as _srv` pattern.
- server.py: Removed 5 Pydantic models, 10 endpoint handlers, 2 helpers (~500 lines). Added `from routers.learning import learning_router` + `app.include_router(learning_router)`.
- tests/test_before_after_endpoint.py: Updated 9 references from `server` to `routers.learning` imports.
- tests/test_remediation_plan_api.py: Updated 2 references from `server.RemediationPlanRequest` to `routers.learning`.
- tests/test_learning_router.py: 31 new tests — route registration (15), module structure (5), lazy import pattern (10), server.py reduction (2).

## Metrics
- Tests: 1104 -> 1135 (0 failures)
- Learning endpoints in server.py: 10 -> 0
- Learning endpoints in routers/learning.py: 0 -> 10
- Total endpoints across routers: 15 (5 auth + 10 learning)
- server.py reduced by ~500 lines
- Phase 4 Stage 2: COMPLETE

## Decision: KEEP

## Next: R41/EXP-P4-07 Contract Tests (Phase 4 Stage 3)
