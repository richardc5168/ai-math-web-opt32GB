# Security Secret Audit: School-first

Date: 2026-03-21
Scope: School-first implementation planning and current repository state

## Confirmed Risks

1. Git history still contains an exposed OpenAI key documented in [SECURITY_MANUAL_ACTIONS.md](SECURITY_MANUAL_ACTIONS.md).
2. Protected auth/payment/subscription paths remain sensitive and should not be behaviorally changed before Phase 6.
3. School-first teacher/admin features must not introduce client-side role flags or raw secret transport.

## Current Safe Baseline

- Parent-report write paths are backend-owned.
- Login has per-IP rate limiting and account-level lockout.
- Bootstrap token exchange avoids raw API key in URL.
- Subscription verification has a server-side path.

## School-first Constraints

- Teacher and admin screens may read mock data in Phase 1-4, but production entitlement must remain server-side.
- No new PAT, payment secret, webhook secret, or browser-stored admin token may be added.
- Any school-first UI using real backend data must rely on existing authenticated endpoints or newly added server-side scope-checked endpoints.

## Required Phase 6 Security Checks

1. Teacher cannot access another teacher's class by changing `class_id`.
2. Parent cannot access another child by changing `student_id`.
3. Admin-only endpoints reject missing/invalid admin token.
4. Before/after endpoints never trust client-supplied role/scope.
5. Event traceability does not expose secrets in payloads.

## Deferred Human Actions

- Revoke exposed OpenAI key from history.
- Clean git history if organization policy requires full secret eradication.