# Iteration R37  EXP-P4-03: CORS & Config Extraction

## Status: COMPLETE — Phase 4 Stage 1 COMPLETE

## Hypothesis
Moving CORS origins and auth/rate-limit constants to environment variables with safe defaults improves production security posture.

## Changes Made
- server.py: CORS `allow_origins` now reads `CORS_ORIGINS` env var (comma-separated, default `*`).
- server.py: 8 auth/rate-limit constants converted from hardcoded to `os.environ.get()` with same default values: `BOOTSTRAP_TOKEN_TTL_S`, `MAX_OUTSTANDING_TOKENS`, `RATE_LIMIT_WINDOW_S`, `RATE_LIMIT_LOGIN`, `RATE_LIMIT_BOOTSTRAP`, `RATE_LIMIT_EXCHANGE`, `LOGIN_LOCKOUT_THRESHOLD`, `LOGIN_LOCKOUT_DURATION_S`.
- tests/test_cors_config.py: 12 new tests — CORS default, env var references, auth config defaults, type checks.

## Metrics
- Tests: 1056 -> 1068 (0 failures)
- Config values via env vars: 0 -> 9 (CORS + 8 auth constants)

## Decision: KEEP

## Phase 4 Stage 1 Summary (R35-R37)
- R35: Password hashing (SHA-256 -> bcrypt + hmac.compare_digest) — 1041 tests
- R36: Debug route guard (DEV_MODE env var) — 1056 tests
- R37: CORS & config extraction — 1068 tests

## Next: R38/EXP-P4-04 Before-After Endpoint (Stage 2)
