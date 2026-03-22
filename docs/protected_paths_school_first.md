# Protected Paths: School-first

These files and areas are protected before Phase 6. Early phases may document, audit, and test them, but should avoid logic rewrites.

## Protected Paths

- `auth/`
- `docs/shared/payment_provider.js`
- `docs/shared/subscription.js`
- `pricing/`
- `docs/parent-report/` token/sync sensitive logic
- core auth sections in [server.py](server.py)
- `.env*`
- any PAT / token / webhook / payment secret material
- analytics KPI definitions unless only documentation/tests are added

## Allowed Early-Phase Work

- Add adjacent docs
- Add tests that assert protected behavior
- Add new isolated school-first modules that do not alter protected flow semantics
- Add additive endpoints outside the core auth path when they reuse existing auth guards

## Disallowed Early-Phase Work

- Replacing login/subscription/payment flows
- Adding client-side secret storage
- Moving entitlement authority from server to client
- Renaming or reinterpreting KPI definitions without a dedicated validation plan