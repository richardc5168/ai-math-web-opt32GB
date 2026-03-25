# Iteration R57 — Cross-Device Backend Base Detection and Status Hardening

## Objective
Reduce cross-device parent-report failure risk so a student on one device and a parent on another device can reliably tell whether cloud sync is active, while preserving the existing backend-owned registry flow.

## Root Cause Summary
The backend registry and round-trip tests already worked. The remaining failure mode was frontend-side: when no backend base had been configured, the browser silently stayed in local-only mode. That made the cross-device promise appear broken even though the core endpoints were correct.

## Problem Severity
High for trust and usability. A parent on another device could interpret "no data" as product failure when the real issue was missing backend configuration on the page.

## Affected Files
- docs/shared/student_auth.js
- docs/parent-report/index.html
- docs/backend-config.json
- dist_ai_math_web_pages/docs/shared/student_auth.js
- dist_ai_math_web_pages/docs/parent-report/index.html
- dist_ai_math_web_pages/docs/backend-config.json
- tests_js/parent-report-cloud-sync-security.spec.mjs

## Previous Logic
- Sync depended on one of three manual configuration paths: injected globals, `?api=`, or stored localStorage value.
- If none existed, cloud sync logged a console warning and stopped.
- Student pages did not clearly show whether sync was cloud-connected.
- Parent-report page did not clearly show whether the current device was actually connected to the backend.

## New Logic
- student_auth.js now resolves backend base in this order:
  1. injected globals
  2. `?api=` query parameter
  3. stored localStorage value
  4. same-origin fallback for non-GitHub hosts
  5. runtime probe of backend-config.json
- Sync and fetch paths now retry once after backend auto-detection instead of failing immediately.
- Student login UI now shows explicit cloud status: connected vs local-only.
- Student-side parent-report link now carries the resolved `api` value when available.
- Parent-report login gate now shows whether the page is actually connected to the cloud backend.
- Added backend-config.json as a deployment hook for publishing the production backend URL without rewriting frontend code.

## Validation Plan
- Re-run parent-report source-level security and sync tests.
- Re-run backend registry round-trip tests.
- Re-run elementary bank validation.
- Re-run repo verify_all and record whether failures are related or pre-existing.

## Validation Result
- `node --test tests_js/parent-report-cloud-sync-security.spec.mjs`: 20/20 pass
- `pytest tests/test_cross_device_data_flow.py tests/test_parent_report_registry_endpoint.py -q`: 11/11 pass
- `python tools/validate_all_elementary_banks.py`: 7157 PASS, 0 FAIL
- `python scripts/verify_all.py`: still NOT OK, but failure is unrelated to this iteration. Current baseline mismatch remains in shared/attempt_telemetry.js, shared/hint_engine.js, and shared/report/report_data_builder.js, plus docs-only files outside this change set.

## Residual Risks
- If production is hosted on GitHub Pages and the backend lives on a separate domain, cross-device sync still requires a real backend URL to be published in backend-config.json or injected as a global.
- This iteration removes silent failure and adds discovery hooks, but it cannot infer a production backend host that the repository does not declare.
- verify_all.py is still not green due to unrelated repo baseline issues.

## Next Iteration Recommendation
1. Set the real production backend URL in docs/backend-config.json and its dist mirror.
2. Deploy and run `node tools/cross_validate_remote.cjs` once local and remote are aligned.
3. Clean the unrelated docs/dist mirror drift so verify_all.py returns to a green baseline.
