# Iteration R39  EXP-P4-05: Auth Router Extraction

## Status: COMPLETE

## Hypothesis
Extracting 5 auth endpoints from server.py into `routers/auth.py` using FastAPI APIRouter reduces server.py by ~240 lines and improves modularity.

## Changes Made
- routers/__init__.py: Created empty package init.
- routers/auth.py: Created with APIRouter (prefix=/v1/app/auth). Moved 4 Pydantic models (AppAuthLoginRequest, AppAuthProvisionRequest, BootstrapRequest, ExchangeRequest) and 5 handler functions (provision, login, whoami, bootstrap, exchange). Uses lazy `import server as _srv` inside each handler body to avoid circular imports.
- server.py: Removed 4 Pydantic model classes and 5 auth endpoint functions (~240 lines). Added `from routers.auth import auth_router` + `app.include_router(auth_router)` at inline position after helpers.
- tests/test_password_hashing.py: Updated 2 tests to import `app_auth_provision` from `routers.auth` instead of `server`.
- tests/test_auth_router.py: 19 new tests — route registration (7), module structure (5), lazy import pattern (5), server.py reduction (2).

## Metrics
- Tests: 1085 -> 1104 (0 failures)
- Auth endpoints in server.py: 5 -> 0
- Auth endpoints in routers/auth.py: 0 -> 5
- server.py lines reduced by ~240

## Decision: KEEP

## Next: R40/EXP-P4-06 Learning Router Extraction
