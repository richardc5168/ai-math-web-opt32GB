# Iteration R35  EXP-P4-01: Password Hashing Upgrade

## Status: COMPLETE

## Hypothesis
Replacing SHA-256 password hashing with bcrypt and adding timing-safe comparisons eliminates brute-force and timing-attack vectors.

## Changes Made
- server.py: `_pwd_hash()` now uses bcrypt.hashpw() (was SHA-256). `_pwd_ok()` supports dual verify (bcrypt first, SHA-256 fallback with lazy re-hash). All 3 admin token comparisons now use `hmac.compare_digest()`. Login flow lazily re-hashes SHA-256 passwords to bcrypt on successful auth.
- server.py: Added `_legacy_sha256_hash()` for backward compat verification.
- server.py: Added `import bcrypt`.
- requirements.txt: Added `bcrypt>=4.0.0`.
- tests/test_password_hashing.py: 18 new tests (bcrypt output, legacy compat, timing-safe source inspection).

## Metrics
- Tests: 1023 -> 1041 (0 failures)
- SHA-256 password hashing: eliminated for new hashes
- Timing-safe comparisons: 3 admin token checks + legacy password verify

## Decision: KEEP

## Next: R36/EXP-P4-02 Debug Route Guard
