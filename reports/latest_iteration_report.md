# Latest Iteration Report

## Session Summary (Iterations 12–34)

### Iteration 12 (commit `43b4417ba`)
- Expanded TOPIC_LINK_MAP with 4 new entries: commercial-pack1-fraction-sprint, national-bank, midterm, grand-slam
- Fixed commercial-pack1-fraction-sprint falling through to generic fraction link
- +4 regression tests → **42 pass**

### Iteration 13 (commit `bb02692bb`)
- Added collapsible section groups to parent report dashboard (17 cards → 7 `<details>` groups)
- Groups: 24h (collapsed), Quick Summary (open), 7-Day Overview (collapsed), Learning Analysis (collapsed), Advanced Analysis (collapsed), Wrong Q & Practice (open), Advice & Export (open)
- **42 pass**

### Iteration 14 (commit `fd7a41b1b`)
- **Critical fix**: WoW identity mismatch — queried telemetry with `d.name` (display name) instead of device UUID
- Added `getDeviceUid()` helper using `AIMathCoachLog.getOrCreateUserId()`
- **43 pass**

### Iteration 15 (commit `8eb71d19c`)
- Added expand/collapse-all toggle button for collapsible groups
- **43 pass**

### Iteration 16 (commit `5da4885ed`)
- **Security fix**: `esc()` escapes `"` → `&quot;` and `'` → `&#39;` (prevents HTML attribute injection)
- **UX consistency**: parent copy wrong count changed from 3 → 5 to match dashboard
- **Stale state fix**: h24Modules element cleared when empty
- +2 regression tests → **45 pass**

### Iteration 17 (commit `25aad6e0e`)
- **Security fix**: exam-sprint `escapeHtml()` missing quote escaping — critical XSS in `data-qid` attribute context
- Audited all 8 escape functions across 8 pages
- +1 regression test → **46 pass**

### Iteration 18 (commit `3592ef3d3`)
- **Practice quality**: `parseFrac()` + `fractionsEqual()` for fraction equivalence via cross-multiplication
- Modified `checkNow()` to accept equivalent fractions with simplification reminder
- +1 regression test → **47 pass**

### Iteration 19 (commit `270c3a242`)
- Added `🔗 去練習模組` deep-link button to each wrong list item using `getTopicLink(w.t)`
- +1 regression test → **48 pass**

### Iteration 20 (commit `adf30d7e1`)
- Added `→ 前往練習模組` deep-link to each detailed analysis (補強方案) card
- +1 regression test → **49 pass**

### Iteration 21 (commit `bc396fe4f`)
- **Critical fix**: Single-practice mode ("再練一題") results were silently lost — only quiz-3 mode called `persistPractice`
- In `goNext()` for non-quiz mode: reset `quizRecorded`, call `persistPractice(isCorrect ? 1 : 0, 1)` per answered question
- Refreshed latest_iteration_report.md to cover iters 17-20
- +1 regression test → **50 pass**

### Iteration 22 (commit `8b8c60fb3`)
- Practice results now write to local `AIMathAttemptTelemetry.appendAttempt()` (before cloud write)
- Events tagged `source: 'parent-report-practice'`, `unit_id: 'parent-report-practice'`
- Uses `getDeviceUid()` for correct identity
- +1 regression test → **51 pass**

### Iteration 23 (commit `581cbcaa6`)
- Added 3 remediation regression tests: priority targeting weakest topic, action text presence, stable links for known topics
- Test count 51 → **54 pass**

### Iteration 24 (commit `54b031ff1`)
- **Critical UX fix**: Practice summary UI update was gated behind cloud write success — if cloud auth unavailable, `renderPracticeSummary()` never fired despite local telemetry being written
- Moved `r.practice.events.push()` + `renderPracticeSummary()` before cloud auth check in `persistPractice()`
- Cloud write is now "bonus persistence" — UI always updates immediately
- +1 regression test → **55 pass**

### Iteration 25 (commit `a28e0fe73`)
- **Feature**: Connected `aggregate.js` ABCD quadrant analysis to parent-report dashboard
- Added `<script src="aggregate.js">` and new "學習象限分析" card in 進階分析 group
- Stacked horizontal bar showing A=獨立答對 / B=提示答對 / C=提示仍錯 / D=無提示答錯 rates from local telemetry (7 days)
- Shows `recommend(stats)` tips below the bar
- +10 regression tests → **65 pass**

### Iteration 26 (commit `2b6502b8c`)
- **Practice quality**: Extended `parseFrac()` to handle mixed numbers (`1 1/2` → `3/2`) and whole numbers (`3` → `3/1`)
- Updated `normAns()` to preserve single spaces for mixed number parsing
- Updated tests with mixed/whole number assertions → **65 pass**

### Iteration 27 (commit `2d4c1c8a2`)
- Added `isComplete` parameter to `persistPractice` — early-exit passes `false`
- Practice events now have `completed: true|false` field
- Practice summary shows `提前結束 N 次` when early exits exist
- +1 regression test → **66 pass**

### Iteration 28 (commit `48f3b718d`)
- **Critical UX fix**: Decimal answers (0.5, 1.25) now equivalent to fractions (1/2, 5/4) using integer arithmetic
- Extended `parseFrac()` to convert decimals to integer fractions (0.5→5/10, no IEEE 754)
- `fractionsEqual('0.5', '1/2')` now returns `true` — unblocks decimal practice modules
- Extended test assertions with decimal↔fraction, decimal↔whole, decimal↔mixed → **66 pass**

### Iteration 29 (commit `5df57f0f2`)
- **Remediation breadth fix**: expanded `practice_from_wrong_engine.js` coverage for the existing bank families that were still falling back to generic remediation
- Added explicit explanation + deterministic practice generation for average, money, discount/percent, ratio, decimal, speed, area/perimeter, time, and multi-step families
- Added 3 regression tests covering family-level explanation coverage, targeted practice generation, and integer-answer safety → **69 pass**

### Iteration 30 (commit `43ceac553`)
- **Commercial remediation coverage fix**: expanded `practice_from_wrong_engine.js` for the remaining commercial and life-bank families still falling through to generic remediation
- Added explicit explanation + deterministic fallback practice for commercial-pack1 fraction-sprint, decimal-unit4 operations, life-applications-g5, interactive-g5-empire `unit_convert`, and interactive-g5-life-pack1-empire conversion/add-sub kinds
- Added 2 bank-backed regression tests that load real `bank.js` payloads and verify these families resolve to non-generic explanations and usable fallback practice → **71 pass**

### Iteration 31 (commit `24919755d`)
- **Full bank audit gate**: expanded remediation coverage for the remaining uncovered kind families and added a repo-wide `bank.js` audit spec
- Added reusable explanation + fallback practice branches for fraction arithmetic basics, fraction comparison, unit conversions, composite volume, line-chart reading, angle geometry, number theory, place value, symmetry, starter algebra, large-number comparison, and division sufficiency across `exam-sprint`, `fraction-g5`, `g5-grand-slam`, `volume-g5`, `interactive-g5-midterm1`, and `interactive-g5-national-bank`
- Added `tests_js/parent-report-bank-audit.spec.mjs`, which scans every current `docs/*/bank.js` file, handles both executable wrappers and literal-array assignment variants, and fails on generic remediation fallthrough or unusable fallback practice → **73 pass**

### Iteration 32 (commit `82dcb479b`)
- **First-screen clarity fix**: surfaced the top 3 weakness concepts directly in the weekly summary area so a parent can see what is weak, why it is weak, and where to start practice without opening deeper sections
- Added a compact weekly weakness summary card that renders from the existing ranked weakness list, reuses `describeWeakReason()` and `nextAction()`, and links straight to targeted practice with a stable CTA
- Added a summary regression test verifying the card exists, is capped at 3 items, explains why the topic is weak, and includes a direct practice CTA → **74 pass**

### Iteration 33 (commit `2878ee355`)
- **First-screen trust signal**: strengthened the weekly weakness summary card with a concrete evidence line so parents can see why the system flagged a weakness without opening deeper sections
- Added `本週證據：錯 N 題，提示 ≥ L2 M 次` to each first-screen weakness card, while preserving the same top-3 cap, reason text, action text, and direct practice CTA
- Strengthened the summary regression test so the first screen must keep both the evidence label and the hint-dependency count → **74 pass**

### Iteration 34 (commit `d283d618d`)
- **Shared logic cleanup**: moved the first-screen weakness evidence sentence into `AIMathWeaknessEngine` so the quick summary no longer owns its own evidence-formatting rule
- Added `buildWeaknessEvidenceText()` to the shared weakness engine, exposed `evidence_text` on ranked rows, and changed parent-report to delegate the summary evidence line to the shared helper instead of assembling it inline
- Extended summary regression coverage with a direct weakness-engine evidence test and a source-level assertion that the page reuses the shared builder → **75 pass**

### Iteration 35 (commit `ba80db8d6`)
- **Deeper evidence alignment**: changed the deeper weakness table and detailed remedial cards to reuse the same shared evidence string as the first-screen summary
- Replaced the deeper weakness table's inline wrong-count and hint-count sentence with `weaknessEvidenceText(w)`, stored shared `evidenceText` on remediation recommendations, and rendered that shared evidence string in detailed remedial cards
- Added a remediation regression test that verifies the page reuses the shared formatter and no longer contains the old inline evidence template → **76 pass**

### Iteration 36 (commit `fc5240021`)
- **P0 frontend token hardening**: removed the parent-report cloud-write token path from bundle/global config and persistent localStorage so the browser only uses a session-scoped runtime token
- Changed `AIMathStudentAuth` cloud sync to read from `sessionStorage`, migrate and clear the legacy localStorage PAT once, and expose `setCloudWriteToken()` / `clearCloudWriteToken()` helpers for explicit runtime use
- Added `tests_js/parent-report-cloud-sync-security.spec.mjs` so the repo fails if `AIMathCloudSyncConfig.gistToken` support or persistent localStorage token lookup returns → **77 pass**

### Iteration 37 (commit `77c68a099`)
- **Backend-owned parent-report sync**: replaced the main browser-owned report/practice write path with a backend registry endpoint while keeping the existing name+PIN UX
- Added `/v1/parent-report/registry/fetch` and `/v1/parent-report/registry/upsert` in `server.py`, storing hashed PIN credentials and report payloads in SQLite so the backend owns verification and writes
- Switched `docs/shared/student_auth.js` and the parent-report page to call the backend registry for sync, unlock, refresh, and practice-result persistence, using a configurable backend base from `AIMATH_PARENT_REPORT_API_BASE`, `AIMATH_API_BASE`, or `?api=`
- Added backend and source-level regression coverage for the new registry path → **78 pass**

### Iteration 38 (commit `working-tree`)
- **Data-ization**: extracted `TOPIC_LINK_MAP` from `recommendation_engine.js` into a shared `topic_link_map.js` data module and `explainWrongDetail` rules from `practice_from_wrong_engine.js` into a shared `wrong_detail_data.js` data module
- Both engines now delegate to the shared data modules with graceful fallback if the data module is not loaded
- Adding a new practice module = 1 line in `topic_link_map.js`; adding a new kind's explanation = 1 entry in `wrong_detail_data.js`
- Added 12 regression tests verifying delegation, fallback, and source-level guards → **90 pass**

### Current Shared Engine Inventory (13 modules)
1. `weakness_engine.js` — `AIMathWeaknessEngine`
2. `topic_link_map.js` — `AIMathTopicLinkMap` (**NEW** — shared topic→link data)
3. `recommendation_engine.js` — `AIMathRecommendationEngine` (delegates to topic_link_map)
4. `report_data_builder.js` — `AIMathReportDataBuilder`
5. `wrong_detail_data.js` — `AIMathWrongDetailData` (**NEW** — shared kind→explanation data, 40 rules)
6. `practice_from_wrong_engine.js` — `AIMathPracticeFromWrongEngine` (delegates to wrong_detail_data)
7. `parent_copy_engine.js` — `AIMathParentCopyEngine` (5-wrong-item limit)
8. `wow_engine.js` — `AIMathWoWEngine`
9. `radar_engine.js` — `AIMathRadarEngine`
10. `progress_trend_engine.js` — `AIMathProgressTrendEngine`
11. `practice_summary_engine.js` — `AIMathPracticeSummaryEngine`
12. `parent_advice_engine.js` — `AIMathParentAdviceEngine`
13. `aggregate.js` — `AIMathReportAggregate` (**connected**: quadrant analysis card in parent-report)

### Test Coverage
- **91 regression tests** across 16 test files, all passing
- **7 backend endpoint tests** for subscription-gated snapshot endpoints
- `validate_all_elementary_banks.py` → 7157 PASS, 0 FAIL
- `verify_all.py` → 4/4 OK (138 files mirrored)

### Remaining Inline Code in parent-report
- All remaining code is **view-layer**: DOM manipulation, event handlers, HTML template rendering
- Domain logic extraction is complete

### Residual Risks
1. ~`aggregate.js` not connected~ — **DONE** (iter 25)
2. ~Mixed number format~ — **DONE** (iter 26)
3. Expand/collapse state not persisted across page reloads
4. Practice events use `unit_id='parent-report-practice'` — separate from real quiz unit_ids in aggregate
5. Remediation coverage is now audited across all current `bank.js` modules, but the rule logic is now in `wrong_detail_data.js` and must grow when new kind families are added
6. The first screen now includes a compact weakness summary as well as deeper weakness/remedial sections; that duplication is acceptable only while both views reuse the same delegates and links
7. The first-screen evidence line depends on the current weakness payload fields (`w`, `h2`, `h3`) staying stable; if the weakness shape changes, the summary should keep degrading gracefully
8. Weakness evidence copy is now shared across the first-screen summary, deeper weakness table, and detailed remedial cards, but the page still owns the HTML layout for those surfaces
9. ~Parent-report cloud writeback still depends on a client-side runtime token~ — **DONE** (iter 37 main path moved to backend registry)
10. ~The hardened parent-report sync path now depends on a configured backend base~ — established in iter 37, further hardened in iter 39
11. ~Remote cross-validation has not been rerun yet~ — pending deployment of subscription-gated path
12. Engines now depend on data modules being loaded before them; if loading order is wrong, engines fall back to defaults silently (by design, but could mask missing data)
13. OpenAI API key still in git history — requires manual `git-filter-repo` + key revocation (documented in SECURITY_MANUAL_ACTIONS.md)
14. Frontend credential provisioning flow (how user gets apiKey+studentId into sessionStorage) is not yet wired to a UI
15. Subscription-gated endpoints fallback from paid→free path is tested at source level but not yet integration-tested with a real frontend flow

### Iteration 39 — Commercial Risk Sprint (Phases 0–4)

**Objective**: Close highest-priority commercial risk: secret containment, writeback abstraction, subscription-gated sync endpoints, frontend paid flow switchover.

**Phase 0 — Secret containment**:
- Untracked `gpt_key_20251110.txt` (live OpenAI key) from git index
- Strengthened `.gitignore` with secret file patterns
- Added `tools/check_no_secrets.py` pre-commit hook
- Created `SECURITY_MANUAL_ACTIONS.md` for human follow-up

**Phase 1 — Writeback abstraction seam**:
- Created `docs/shared/report_sync_adapter.js` as single frontend sync surface
- Refactored parent-report to use adapter for all read/write operations
- 90 JS tests passing

**Phase 2 — Backend subscription-gated snapshot endpoints**:
- Added `ReportSnapshotWriteRequest` / `ReportSnapshotReadRequest` Pydantic models
- Added `report_snapshots` SQLite table
- Added `POST /v1/app/report_snapshots` (write) and `POST /v1/app/report_snapshots/latest` (read) — both gated by X-API-Key → subscription-active → student-ownership
- 7 backend tests covering missing/invalid/inactive/wrong-owner/happy-path/upsert scenarios

**Phase 3 — Frontend paid flow switchover**:
- Extended adapter with sessionStorage-based credential management (`setCredentials`/`clearCredentials`/`hasCredentials`)
- Dual-path routing: paid users → subscription-gated endpoints with X-API-Key; free users → name+PIN registry endpoints
- Automatic fallback from paid to free path on auth/subscription errors (402, 401, 404)

**Phase 4 — Tests, regression, writeback**:
- Added security regression test verifying credentials are session-scoped and paid path is properly gated
- 91 JS tests + 7 backend tests all passing
- `validate_all_elementary_banks.py`: 7157 PASS, 0 FAIL
- `verify_all.py`: 4/4 OK (138 files mirrored)

### Iteration 40 — Gist write-token isolation & deny-by-default hardening
**Date**: 2026-03-19
**Objective**: Close security gaps left by iter 39 — Gist fallback still attached write token and leaked PINs.

**Root Cause**: Iter 39 established the new architecture but did not audit every remaining usage of the legacy Gist auth infrastructure. Two specific gaps:
1. `lookupStudentReport()` Gist fallback still conditionally attached `Authorization: token <write_token>` header to read requests (public Gist doesn't need auth)
2. Gist fallback returned raw `entry.pin` to the browser — sensitive data leakage from uncontrolled data source

**Fixes Applied**:
- Removed `if (hasCloudWriteToken()) headers.Authorization = ...` from Gist fallback read path in `student_auth.js`
- Stripped `pin` field from all Gist fallback return objects (both merged-attempts and raw-entry paths)
- Mirrored all changes to `dist_ai_math_web_pages/docs/shared/student_auth.js`

**Security Regression Tests Added** (5 new, 8 total):
1. Gist fallback read path never attaches a write token
2. Gist fallback read never returns stored PIN to browser
3. No frontend file directly constructs Gist PATCH or write requests
4. `doCloudSync` and `recordPracticeResult` never use direct Gist writes
5. Subscription-gated snapshot endpoints enforce deny-by-default (source-level verification of auth, subscription, and ownership gates)

**Validation Results**:
- 96 JS tests (0 fail) — up from 91
- 7 backend tests (0 fail)
- 7157 bank questions (0 fail)
- verify_all 4/4 OK (138 files mirrored)

**Residual Risks**:
1. ~`setCloudWriteToken`/`clearCloudWriteToken`/`isCloudWriteEnabled` still exported on `window.AIMathStudentAuth`~ — **DONE** (iter 41: removed from exports)
2. OpenAI key still in git history (requires manual git-filter-repo)
3. Credential provisioning UI not yet wired

### Iteration 41 — Backend-owned practice event writeback + dead export cleanup
**Date**: 2026-03-19
**Objective**: Complete the backend-owned writeback seam for paid flow by adding a subscription-gated practice event endpoint, extending the adapter with paid-path routing for practice events, and removing dead cloud-token exports.

**Changes**:

1. **New endpoint `POST /v1/app/practice_events`** (server.py):
   - Full deny-by-default: `get_account_by_api_key` → `ensure_subscription_active` → `_verify_student_ownership` → `_sanitize_practice_event`
   - Appends practice events to the student's `report_snapshots` row, or creates a new snapshot row if none exists
   - Uses `PracticeEventWriteRequest` model (`student_id: int`, `event: dict`)

2. **Adapter `writePracticeEvent` dual-path** (report_sync_adapter.js):
   - Paid path: `_isPaidAndCredentialed()` → `POST /v1/app/practice_events` with X-API-Key
   - Free path: `POST /v1/parent-report/registry/upsert` with name+PIN
   - Automatic fallback from paid to free on any error

3. **Removed dead exports** (student_auth.js):
   - `setCloudWriteToken`, `clearCloudWriteToken`, `isCloudWriteEnabled` removed from `window.AIMathStudentAuth` export block
   - 0 external callers confirmed via source-level grep of all HTML and JS files
   - Internal functions retained for Gist read fallback compatibility

**Tests Added** (8 new, 12 total backend, 11 total security):
- Backend: practice_events missing key (401/422), inactive subscription (402), wrong student (404), happy path creates snapshot, happy path appends to existing snapshot
- JS source-level: cloud-token exports NOT in API surface, adapter has paid path for practice events, practice_events endpoint has deny-by-default gates

**Validation Results**:
- 99 JS tests (0 fail) — up from 96
- 12 backend tests (0 fail) — up from 7
- 7157 bank questions (0 fail)
- verify_all 4/4 OK (138 files mirrored)

**Residual Risks**:
1. Internal cloud-token functions (`getCloudToken`, `buildCloudHeaders`, `setCloudWriteToken`, `clearCloudWriteToken`) still exist as dead internal code
2. OpenAI key still in git history
3. Credential provisioning UI not yet wired
4. Remote cross-validation not yet run

### Iteration 42 (working-tree) — Paid Bootstrap + Dead Code Removal

**Goal**: Wire the paid parent-report bootstrap path so authenticated/subscribed users can use backend-owned writeback. Remove all dead cloud-token internal code.

**Changes**:
1. **parent-report/index.html** — Added `bootstrapPaidSession()` IIFE:
   - Reads `api_key` + `student_id` from URL params
   - Strips credentials from URL immediately via `history.replaceState` (prevents sharing/bookmarking)
   - Stores credentials in sessionStorage via `adapter.setCredentials()`
   - Validates async via `GET /v1/app/auth/whoami` with X-API-Key header
   - On success: calls `syncFromBackend({ status: 'active' })` to enable `isPaid()`
   - On failure: calls `adapter.clearCredentials()` to deny paid path

2. **subscription.js** — Added session-scoped backend entitlement:
   - `syncFromBackend(backendSub)`: sets in-memory `_backendPaidStatus` (NOT localStorage)
   - `clearBackendSync()`: clears in-memory state
   - `getEffectiveSub()`: now checks `_backendPaidStatus` between `UNLIMITED_STUDENT_NAMES` override and localStorage fallback
   - Both functions exported on `window.AIMathSubscription`

3. **student_auth.js** — Removed all dead cloud-token code:
   - Deleted: `getCloudToken()`, `setCloudWriteToken()`, `clearCloudWriteToken()`, `hasCloudWriteToken()`, `buildCloudHeaders()`
   - Deleted: `CLOUD_TOKEN_KEY`, `LEGACY_CLOUD_TOKEN_KEY` constants, `_cloudLegacyTokenWarned` flag
   - Inlined `buildCloudHeaders(false)` in Gist fallback with literal `{ 'Accept': 'application/vnd.github+json' }`

4. **Tests** — Updated + added 2 new:
   - Replaced "session-scoped token" test with "cloud-token fully removed" test
   - New: "paid bootstrap strips credentials from URL and validates via whoami"
   - New: "subscription syncFromBackend is session-scoped (not localStorage)"

**Security Properties**:
- Three independent gates protect the paid path: (1) credentials in sessionStorage, (2) `isPaid()` returns true via in-memory flag, (3) backend rejects invalid keys on every API call
- Credentials are stripped from URL immediately — not shareable via link/bookmark
- Backend entitlement is session-scoped (in-memory, not localStorage) — doesn't persist across page loads
- Whoami failure clears stored credentials — prevents use of invalid/expired keys
- Async whoami gap is safe: credentials stored but `isPaid()` returns false → free path used until whoami completes

**Validation Results**:
- 101 JS tests (0 fail) — up from 99
- 13 security tests (0 fail) — up from 11
- 12 backend tests (0 fail)
- 7157 bank questions (0 fail)
- verify_all 4/4 OK (138 files mirrored)

### Iteration 43 (working-tree) — Bootstrap Token Exchange

**Goal**: Replace raw `api_key` in URL-param bootstrap with a short-lived, single-use bootstrap token exchange. Browser must never receive a long-lived raw `api_key` via URL.

**Changes**:
1. **server.py** — Two new endpoints:
   - `POST /v1/app/auth/bootstrap`: APP calls server-side with X-API-Key + `BootstrapRequest{student_id}`, validates auth+subscription+ownership, generates `secrets.token_urlsafe(32)`, stores in `_bootstrap_tokens` dict (5-min TTL), returns `{bootstrap_token}`
   - `POST /v1/app/auth/exchange`: Frontend calls with `ExchangeRequest{bootstrap_token}`, pops token (single-use), validates TTL, re-validates subscription, returns `{api_key, student_id, subscription}` via POST body only
   - Added `_cleanup_expired_tokens()` garbage collector, runs before each operation
   - Added Pydantic models: `BootstrapRequest`, `ExchangeRequest`

2. **parent-report/index.html** — Rewrote `bootstrapPaidSession()` IIFE:
   - Reads `?bt=` (bootstrap token) from URL params — NOT `api_key`
   - Actively REJECTS raw `api_key` in URL (strips + shows warning "不安全的連結格式已被拒絕")
   - Strips `bt` from URL via `history.replaceState`
   - Exchanges token via `POST /v1/app/auth/exchange`
   - On success: `adapter.setCredentials()` + `syncFromBackend()`
   - On failure: shows warning, falls back to free mode

3. **tests/test_report_snapshot_endpoints.py** — 8 new backend tests:
   - Bootstrap: missing key, invalid key, inactive subscription, wrong student, happy path
   - Exchange: invalid token, replayed (single-use enforcement), expired token, happy path roundtrip
   - Total: 21 backend tests (was 12)

4. **tests_js/parent-report-cloud-sync-security.spec.mjs** — 3 new JS tests (replaced 1):
   - "paid bootstrap uses short-lived token exchange, not raw api_key in URL"
   - "parent-report rejects raw api_key in URL params"
   - "bootstrap/exchange endpoints enforce deny-by-default (source-level)"
   - Total: 15 security tests (was 13)

**Security Properties**:
- Raw `api_key` **never** appears in URL — actively rejected with user warning
- Bootstrap token is opaque, short-lived (5 min), single-use (dict.pop)
- Real credentials arrive only via POST response body — not in URL, headers, or query strings
- Exchange re-validates subscription — stale tokens can't bypass expiry
- `_cleanup_expired_tokens()` prevents memory leak from unused tokens
- Deny-by-default on bootstrap: `get_account_by_api_key` → `ensure_subscription_active` → `_verify_student_ownership`

**Validation Results**:
- 103 JS tests (0 fail) — up from 101
- 15 security tests (0 fail) — up from 13
- 21 backend tests (0 fail) — up from 12
- 7157 bank questions (0 fail)
- verify_all 4/4 OK (138 files mirrored)

**Residual Risks**:
1. Bootstrap tokens stored in-memory — server restart clears all outstanding tokens (acceptable for MVP)
2. No rate limiting on bootstrap/exchange endpoints
3. OpenAI key in git history
4. No login form UI yet — paid bootstrap relies on APP passing `?bt=` in URL
5. Remote cross-validation not yet run

### Iteration 44 (working-tree) — Bootstrap/Exchange Hardening

**Goal**: Add rate limiting, per-account token cap, and abuse-oriented regression coverage to the bootstrap/exchange flow.

**Changes**:
1. **server.py** — Rate limiter + token cap:
   - Added `_check_rate_limit(key, max_requests)`: per-IP sliding window (60s)
   - `_RATE_LIMIT_BOOTSTRAP = 10` requests/min per IP
   - `_RATE_LIMIT_EXCHANGE = 20` requests/min per IP
   - Both endpoints check rate limit BEFORE auth gates (invalid requests count)
   - HTTP 429 with descriptive detail on limit hit
   - Added `_MAX_OUTSTANDING_TOKENS_PER_ACCOUNT = 5`: prevents token flooding
   - Bootstrap refuses new tokens when account already has 5 outstanding (429)
   - Added `Request` parameter to both endpoint signatures for client IP

2. **tests/test_report_snapshot_endpoints.py** — 4 new tests:
   - `test_bootstrap_rate_limit`: verifies 429 after exceeding limit
   - `test_exchange_rate_limit`: verifies 429 after exceeding limit
   - `test_bootstrap_per_account_token_cap`: verifies 429 when cap hit
   - `test_rate_limit_does_not_block_normal_flow`: verifies happy path still works
   - Total: 25 backend tests (was 21)

3. **tests_js/parent-report-cloud-sync-security.spec.mjs** — 1 new test:
   - "bootstrap/exchange endpoints have rate limiting and token cap (source-level)"
   - Updated window sizes for larger endpoint bodies (1500 for bootstrap, 1200 for exchange)
   - Total: 16 security tests (was 15)

**Security Properties**:
- Rate limiting runs BEFORE auth validation — unauthenticated flood constrained
- Per-account token cap runs AFTER auth — prevents authenticated token flooding
- Both return HTTP 429 with clear reason codes
- Normal paid flow (1 bootstrap + 1 exchange) well below any limit
- All prior lifecycle rules preserved: single-use, TTL, replay rejection

**Validation Results**:
- 104 JS tests (0 fail) — up from 103
- 16 security tests (0 fail) — up from 15
- 25 backend tests (0 fail) — up from 21
- 7157 bank questions (0 fail)
- verify_all 4/4 OK (138 files mirrored)

**Residual Risks**:
1. Rate limiter is in-process/in-memory — cleared on restart, not shared across workers
2. IP-based limiting can be bypassed by distributed attackers or proxies
3. Bootstrap tokens stored in-memory — cleared on restart (acceptable for MVP)
4. OpenAI key in git history
5. No login form UI yet
6. Remote cross-validation not yet run

**Residual Risks**:
1. GIST_ID/GIST_API constants remain in student_auth.js for read-only Gist fallback — intentional
2. OpenAI key still in git history
3. whoami validation is async — brief window after page load where free path may be used (graceful degradation)
4. No login form UI yet — paid bootstrap relies on URL params from the APP
5. Remote cross-validation not yet run

### Next Iteration Priorities
1. ~Connect aggregate.js~ — **DONE** (iter 25)
2. ~Mixed number support~ — **DONE** (iter 26)
3. ~Practice early-exit tracking~ — **DONE** (iter 27)
4. ~Replace browser-owned write path with backend-owned endpoint~ — **DONE** (iter 37)
5. ~Subscription-gated snapshot endpoints + paid flow switchover~ — **DONE** (iter 39)
6. ~Gist write-token isolation & deny-by-default hardening~ — **DONE** (iter 40)
7. ~Backend-owned practice event writeback + dead export cleanup~ — **DONE** (iter 41)
8. ~Wire credential provisioning bootstrap for paid users~ — **DONE** (iter 42)
9. ~Remove internal dead cloud-token functions entirely~ — **DONE** (iter 42)
10. ~Replace raw api_key URL bootstrap with token exchange~ — **DONE** (iter 43)
11. ~Rate limiting + token cap for bootstrap/exchange~ — **DONE** (iter 44)
12. ~Move bootstrap tokens + rate limiter to durable DB-backed storage~ — **DONE** (iter 45)
13. Add login form UI for direct parent access (doesn't rely on URL params)
14. Deploy backend and run remote cross-validation for the new sync path
15. Manual: revoke OpenAI key, run git-filter-repo to clean history
16. Consider removing Gist read fallback entirely (GIST_ID/GIST_API)
17. Add failed-attempt logging/alerting for token abuse detection
18. Consider Redis for rate limiting if multi-process deployment needed

### Iteration 45 (working-tree) — Durable Bootstrap Token Store + Rate Limiter

**Goal**: Move bootstrap token lifecycle and rate limiter from in-memory dicts to durable SQLite-backed storage for commercial robustness. Tokens must survive server restarts; rate limiting must be shared across the same DB.

**Changes**:
1. **server.py** — Replaced in-memory stores with DB-backed operations:
   - **Removed**: `_bootstrap_tokens: Dict[str, Dict[str, Any]] = {}` in-memory dict
   - **Removed**: `_rate_limit_store: Dict[str, List[float]] = {}` in-memory dict
   - **Removed**: Old `_cleanup_expired_tokens()` (operated on in-memory dict)
   - **Added**: `_hash_token(raw_token)` — SHA-256 hash of raw token (defense in depth)
   - **Added**: `_store_bootstrap_token(raw_token, api_key, account_id, student_id)` — INSERT into `bootstrap_tokens` table
   - **Added**: `_consume_bootstrap_token(raw_token)` — SELECT by hash, check unconsumed + unexpired, UPDATE `consumed_at` (single-use)
   - **Added**: `_count_outstanding_tokens(account_id)` — COUNT WHERE NOT consumed AND NOT expired
   - **Added**: `_cleanup_expired_tokens_db()` — DELETE rows older than 2×TTL
   - **Refactored**: `_check_rate_limit(key, max_requests)` — DELETE old entries from `rate_limit_events`, COUNT in window, INSERT new entry
   - **Added to `init_db()`**: Two new tables with indexes:
     - `bootstrap_tokens` (id, token_hash, account_id, student_id, api_key, created_at, expires_at, consumed_at)
     - `rate_limit_events` (id, key, ts)
   - Updated `app_auth_bootstrap()` to use `_count_outstanding_tokens()` + `_store_bootstrap_token()`
   - Updated `app_auth_exchange()` to use `_consume_bootstrap_token()` (replaces `_bootstrap_tokens.pop()`)

2. **tests/test_report_snapshot_endpoints.py** — 5 existing tests updated + 1 new:
   - `test_exchange_expired_token`: Changed from `setup_server._bootstrap_tokens[token]["created"] -= 400` to DB UPDATE setting `expires_at` to a past timestamp via `_hash_token()`
   - `test_bootstrap_rate_limit`: Changed `_rate_limit_store.clear()` → `DELETE FROM rate_limit_events`; `_bootstrap_tokens.clear()` → `DELETE FROM bootstrap_tokens`
   - `test_exchange_rate_limit`: Same DB-based cleanup
   - `test_bootstrap_per_account_token_cap`: Same DB-based cleanup
   - `test_rate_limit_does_not_block_normal_flow`: Same DB-based cleanup
   - **NEW** `test_token_survives_server_module_state`: Verifies token exists in DB after bootstrap, verifies `consumed_at` is NULL before exchange and non-NULL after exchange
   - Total: 26 backend tests (was 25)

3. **tests_js/parent-report-cloud-sync-security.spec.mjs** — 1 assertion updated:
   - Changed `_bootstrap_tokens.pop` assertion to `_consume_bootstrap_token` (matches DB-based consumption)
   - Total: 16 security tests (unchanged count)

**Security Properties**:
- Token hashes stored in DB (SHA-256) — raw tokens never persisted at rest
- Tokens survive server restart — no more data loss on process recycle
- Rate limiter state survives restart — consistent abuse protection
- Same external API contract: 200/401/402/404/429 responses unchanged
- Single-use enforcement via `consumed_at` column — set on exchange, checked on SELECT
- Cleanup deletes rows older than 2×TTL (10 min) — prevents unbounded DB growth

**Validation Results**:
- 104 JS tests (0 fail) — unchanged
- 16 security tests (0 fail) — unchanged
- 26 backend tests (0 fail) — up from 25
- 7157 bank questions (0 fail)
- verify_all 4/4 OK (138 files mirrored)

**Residual Risks**:
1. SQLite single-writer constraint may bottleneck under very high concurrent load — acceptable for current scale
2. IP-based rate limiting still bypassable by distributed attackers or proxies
3. OpenAI key in git history
4. No login form UI yet
5. Remote cross-validation not yet run

---

### Iteration 46 — Paid Parent Login UI (2026-03-19)

**Scope**: `paid-parent-login-ui` | **Status**: ✅ Passed

**Objective**: Add minimal paid parent login UI to parent-report login gate so parents with purchased accounts can authenticate directly on the web page (username + password) without needing an external APP to generate a `?bt=` bootstrap URL.

**Changes**:
- Added collapsible "💎 已購買帳號？點此登入" section to login gate (`<details>` element with username, password inputs)
- Added `initPaidLogin()` IIFE: 3-step async flow (login → bootstrap → exchange) → `setCredentials()` + `syncFromBackend()` → auto-load report
- Raw `loginApiKey` stays in closure scope, never stored durably. Password cleared from DOM on success.
- Error handling: 401/402/403 with Chinese messages, button re-enabled on all error paths
- +3 security tests (19 total): 3-step flow verification, no raw key storage, error handling without credential leaks

**Files**: `docs/parent-report/index.html`, `dist_ai_math_web_pages/docs/parent-report/index.html`, `tests_js/parent-report-cloud-sync-security.spec.mjs`

**Validation**: 19 JS security ✅ | 107 JS ✅ | 26 backend ✅ | 7157 bank PASS | verify_all 4/4 OK

**Residual Risks**:
1. No student selector — uses `default_student` only
2. ~~No rate limiting on `/v1/app/auth/login` endpoint~~ → **Fixed in iteration 47**
3. OpenAI key in git history
4. No password recovery flow
5. Remote cross-validation not yet run

---

### Iteration 47 — Login Endpoint Rate Limiting (2026-03-19)

**Scope**: `login-endpoint-rate-limiting` | **Status**: ✅ Passed

**Objective**: Add per-IP rate limiting to `/v1/app/auth/login` to prevent brute-force credential guessing. Reuse existing `_check_rate_limit` infrastructure.

**Changes**:
- Added `_RATE_LIMIT_LOGIN = 5` (stricter than bootstrap 10, exchange 20)
- Added `Request` parameter to `app_auth_login()` for client IP
- Rate limit fires BEFORE credential validation (prevents timing-based username enumeration)
- 429 response is generic ("Too many login attempts") — no credential details leaked
- +3 backend tests (29 total): rate limit enforcement, ordering proof (429 not 401), no-leak proof
- Updated JS source-level test: added `_RATE_LIMIT_LOGIN` assertion + source ordering check

**Files**: `server.py`, `tests/test_report_snapshot_endpoints.py`, `tests_js/parent-report-cloud-sync-security.spec.mjs`

**Validation**: 29 backend ✅ | 19 JS security ✅ | verify_all 4/4 OK (138 files mirrored)

**Residual Risks**:
1. ~~No account-level login lockout (only IP-based rate limiting)~~ → **Fixed in iteration 48**
2. No failed-attempt logging/alerting
3. No student selector UI
4. OpenAI key in git history (manual action)
5. No password recovery flow
6. Remote cross-validation not yet run

### Iteration 48 — Account-Level Login Lockout (2026-03-19)

**Scope**: `account-level-login-lockout` | **Status**: ✅ Passed

**Objective**: Add account-level login lockout to complement per-IP rate limiting. After 5 failed login attempts for the same username within 5 minutes, temporarily lock that account regardless of source IP.

**Changes**:
- Added `_LOGIN_LOCKOUT_THRESHOLD = 5` and `_LOGIN_LOCKOUT_DURATION_S = 300` constants
- Added `login_failures` SQLite table (username, client_ip, ts) with index in `init_db()`
- Added 3 helper functions: `_is_account_locked()`, `_record_login_failure()`, `_clear_login_failures()`
- Modified login flow: IP rate limit (429) → account lockout (423) → credential validation (401/403) → success + clear failures
- Both invalid-username and wrong-password 401s now record failures
- Successful login clears all failure records for that username
- Old failure records auto-pruned (2× lockout window)
- +5 backend tests (34 total): lockout enforcement, expiry, clear-on-success, no cross-account impact, no credential leak
- Updated JS source-level test: +6 assertions for lockout infrastructure and ordering

**Files**: `server.py`, `tests/test_report_snapshot_endpoints.py`, `tests_js/parent-report-cloud-sync-security.spec.mjs`

**Validation**: 34 backend ✅ | 19 JS security ✅ | verify_all 4/4 OK (138 files mirrored)

**Residual Risks**:
1. No CAPTCHA or progressive delay for persistent attackers
2. ~~No admin notification on lockout events~~ → **Logging added in iteration 49**
3. ~~No failed-attempt logging/alerting dashboard~~ → **Admin endpoint added in iteration 49**
4. No student selector UI
5. OpenAI key in git history (manual action)
6. No password recovery flow

### Iteration 49 — Login Failure Logging + Admin Audit (2026-03-19)

**Scope**: `login-failure-logging` | **Status**: ✅ Passed

**Objective**: Add structured Python logging for all login events and an admin-gated endpoint to query recent failures.

**Changes**:
- Added `import logging` and `_auth_logger = logging.getLogger("auth")`
- Failed logins emit WARNING with username, IP, reason (never password)
- Lockout triggers emit WARNING `login_lockout`
- Successful logins emit INFO `login_success`
- Inactive user (403) now also records failure in DB
- Added `GET /v1/app/admin/login-failures` endpoint: X-Admin-Token gated, configurable window (1–1440 min), returns up to 200 recent failures sorted DESC
- Endpoint placed before `app.mount("/")` to avoid static catch-all shadowing
- +3 backend tests (37 total): log emission on failure, log emission on success, admin endpoint auth+response
- +5 JS source-level assertions (19 total): _auth_logger, logging calls, admin endpoint

**Files**: `server.py`, `tests/test_report_snapshot_endpoints.py`, `tests_js/parent-report-cloud-sync-security.spec.mjs`

**Validation**: 37 backend ✅ | 19 JS security ✅ | verify_all 4/4 OK (138 files mirrored)

**Residual Risks**:
1. No log rotation or external log aggregation
2. No alerting threshold (e.g. email on 10+ failures/hour)
3. ~~No student selector UI~~ → **Fixed in iteration 50**
4. OpenAI key in git history (manual action)
5. No password recovery flow

### Iteration 50 — Student Selector for Multi-Student Accounts (2026-03-19)

**Scope**: `student-selector-ui` | **Status**: ✅ Passed

**Objective**: Add student selector UI so paid parents with multi-student accounts can choose which student's report to view, instead of always seeing the first student.

**Changes**:
- Modified login endpoint to return `students` array with all students (was `LIMIT 1`)
- Added `default_student` preserved for backward compatibility
- Added student selector HTML: dropdown + confirm button, hidden by default
- Refactored `initPaidLogin()`: extracted `proceedWithStudent()` helper for bootstrap+exchange
- After login Step 1: if >1 student → show selector; if ≤1 → auto-proceed
- On selector confirm: passes selected `student_id` to bootstrap
- Also added 423 (lockout) error handling in login UI
- +2 backend tests (39 total): multi-student login returns full array, single-student returns array with 1
- +1 JS source-level test (20 total): selector HTML presence, students array usage, auto-proceed logic, proceedWithStudent pattern
- Updated existing "api_key durability" test: widened count to accommodate refactored function parameter passing while adding stricter storage-API check

**Files**: `server.py`, `docs/parent-report/index.html`, `dist_ai_math_web_pages/docs/parent-report/index.html`, `tests/test_report_snapshot_endpoints.py`, `tests_js/parent-report-cloud-sync-security.spec.mjs`

**Validation**: 39 backend ✅ | 20 JS security ✅ | 108 JS total ✅ | verify_all 4/4 OK | 0 bank issues

**Residual Risks**:
1. No log rotation or external log aggregation
2. No alerting threshold
3. OpenAI key in git history (manual action)
4. No password recovery flow
5. Remote cross-validation not yet run (not deployed)
6. Student selector does not persist selection across page reloads (session-scoped, by design)

### Iteration 51 — Remove Gist Read Fallback (2026-03-19)

**Scope**: `remove-gist-fallback` | **Status**: ✅ Passed

**Objective**: Remove all remaining Gist infrastructure (GIST_ID, GIST_API, Gist fetch fallback) from `student_auth.js`. The backend-owned path has been the primary path since iter 37 and was hardened through iter 50. The Gist read fallback is now legacy dead code referencing external GitHub infrastructure.

**Changes**:
- Removed `GIST_ID` and `GIST_API` constants
- Removed Gist fetch fallback block from `lookupStudentReport()` (backend-only now)
- Removed 3 dead Gist-only helpers: `collectAliasEntries`, `getStoredAttempts`, `getPracticeEventsFromData`
- Removed dead `warnMissingCloudToken` function and `_cloudAuthWarned` flag
- Updated stale JSDoc/comments referencing Gist
- Replaced 2 Gist safety tests with 1 comprehensive Gist-removal verification test

**Files**: `docs/shared/student_auth.js`, `dist_ai_math_web_pages/docs/shared/student_auth.js`, `tests_js/parent-report-cloud-sync-security.spec.mjs`

**Validation**: 39 backend ✅ | 19 JS security ✅ | 107 JS total ✅ | verify_all 4/4 OK | 0 bank issues

**Residual Risks**:
1. ~~No log rotation or external log aggregation~~
2. ~~No alerting threshold~~ → **Partially addressed in iteration 52** (anomaly detection added to admin endpoint)
3. OpenAI key in git history (manual action)
4. No password recovery flow
5. Remote cross-validation not yet run (not deployed)

### Iteration 52 — Admin Login-Failure Anomaly Detection (2026-03-19)

**Scope**: `admin-anomaly-detection` | **Status**: ✅ Passed

**Objective**: Extend the existing `GET /v1/app/admin/login-failures` endpoint with summary statistics and an alert level indicator so an admin can quickly assess whether the system is under attack.

**Changes**:
- Extended admin endpoint response with `summary` object containing:
  - `total_failures`: count in the requested time window
  - `unique_ips`: distinct source IPs
  - `unique_usernames`: distinct target usernames
  - `locked_accounts`: list of currently locked account usernames (via `_LOGIN_LOCKOUT_THRESHOLD`)
  - `alert_level`: `"normal"` (<10 failures) | `"elevated"` (10–50) | `"critical"` (>50)
- Added locked account detection query using existing `login_failures` table + lockout threshold
- All additive — no changes to existing response fields or behavior
- +2 backend tests: summary stats with multi-user failures and lockout detection, elevated alert level with synthetic DB entries
- +5 JS source-level assertions: summary object, alert_level, locked_accounts, unique_ips, unique_usernames presence in admin endpoint source

**Files**: `server.py`, `tests/test_report_snapshot_endpoints.py`, `tests_js/parent-report-cloud-sync-security.spec.mjs`

**Validation**: 41 backend ✅ (+2) | 19 JS security ✅ | 107 JS total ✅ | verify_all 4/4 OK (138 files mirrored)

**Residual Risks**:
1. No external alerting integration (email/webhook) — admin must poll the endpoint
2. Alert thresholds are hardcoded (10/50) — not configurable without code change
3. No log rotation or external log aggregation
4. OpenAI key in git history (manual action)
5. No password recovery flow
6. Remote cross-validation not yet run (not deployed)
