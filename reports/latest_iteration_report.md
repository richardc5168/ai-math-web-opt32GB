# Iteration R36  EXP-P4-02: Debug Route Guard

## Status: COMPLETE

## Hypothesis
Guarding `_debug/*` endpoints with DEV_MODE environment variable prevents accidental data exposure in production.

## Changes Made
- server.py: Moved `_debug_accounts` and `_debug_students` from dead code (nested inside `parent_weekly` after return) to top-level module functions. Added `_is_dev_mode()` helper that checks `DEV_MODE` env var. Both debug endpoints return 404 unless DEV_MODE is set to `1`/`true`/`yes`.
- tests/test_debug_route_guard.py: 15 new tests — `_is_dev_mode()` unit tests (7), blocked-without-DEV_MODE (2), accessible-with-DEV_MODE (2), module-level structure checks (4).

## Metrics
- Tests: 1041 -> 1056 (0 failures)
- Debug endpoints guarded: 2/2 (was 0/2, and previously dead code)

## Decision: KEEP

## Next: R37/EXP-P4-03 CORS & Config Extraction
