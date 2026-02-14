# Copilot Promote — Learning Analytics + Remediation Planner (RAGWEB)

This document is a **copy-paste prompt** for VS Code Copilot Agent to implement a learning analytics + remediation recommendation subsystem inside this repository.

It is tailored to this repo’s constraints:
- GitHub Pages static site
- `docs/` and `dist_ai_math_web_pages/docs/` must stay mirrored for web content
- Existing attempt telemetry already exists (localStorage-based)
- Quality gate: run verification/tests and only then commit

---

## Copilot Agent Prompt (paste into Copilot)

You are working in the existing repository `RAGWEB` (Python + static GitHub Pages). Implement a local-first “Learning Analytics + Remediation Planner” subsystem that turns student attempt logs into explainable, actionable learning recommendations, with strong quality gates.

Do NOT change existing question generation, hint logic, or exercise UX; only add analytics/recommendation/reporting capabilities.

### Key repo constraints (must follow)
1) Static site mirroring: any change under `docs/**` must be mirrored to `dist_ai_math_web_pages/docs/**` (identical). Existing verification uses `scripts/verify_all.py`.
2) Data source: the current system already records attempts via shared telemetry (localStorage attempts). Prefer adapting existing attempt telemetry schema rather than inventing a new incompatible one.
3) Quality gate: do not commit unless BOTH pass:
   - `python scripts/verify_all.py`
   - `pytest -q` (or a targeted deterministic subset; document what you run)

### Goal
Build a deterministic, explainable analytics + remediation engine v1 (rule-based, no LLM required) that:
- Aggregates attempts by unit/kind/topic/skill tags and time window (7/14/30/all).
- Computes accuracy, hint dependency, time-spent metrics, and trends over time.
- Detects weak skills using clear thresholds (low accuracy, high hint dependency, repeated “C” quadrant / repeated errors).
- Produces a “Remediation Plan” JSON snapshot + a parent-friendly plain text report.
- Supports dataset plugins (blueprints) for exam focus (e.g., private school entry / mock exams) that reweights priorities, without requiring copyrighted question text.

### Non-goals
- Do not redesign existing pages, filters, or add new UI pages beyond minimal integration to existing report(s).
- Do not scrape, embed, or store copyrighted exam questions. If using external data, ingest only openly licensed/public-domain datasets or store only metadata (topic weights, skill tags, references).

---

## Architecture (minimal, Python-first + browser integration)

### A) Domain schema (normalized internal model)
Define an internal normalized model (even if storage is JSON/telemetry-based):
- `AttemptEvent`: timestamp, `unit_id`, `kind`, `question_id`, `is_correct`, `duration_ms`, `hints_viewed_count`, `hint_depth` / `steps_shown_solution`, optional `mistake_code` (concept/calculation/unit/reading/careless), optional extra tags.
- `AnalyticsResult`: computed metrics per dimension and per time window.
- `RemediationPlan`: top weak skills + evidence + suggested practice sequence + application mapping.

### B) Storage & adapters
- Provide an adapter that converts the existing telemetry attempt objects into the normalized `AttemptEvent`.
- Do not change telemetry writing in exercise pages.
- Provide two ingestion modes:
  1) **Browser**: use existing `listAttempts()` results and adapt in JS (for report page usage).
  2) **Offline analysis**: a Python script that reads exported attempts JSON and outputs analytics + plan + plain text report.

### C) Analytics engine (deterministic)
Implement functions:
- `compute_analytics(events, window_days)` → KPIs + breakdowns + trends
- `detect_weak_skills(analytics)` → top 3 weaknesses with evidence
- `build_remediation_plan(analytics, blueprint=None)` → explainable recommendations

### D) Dataset plugin (blueprint)
Create a plugin format under a new folder (choose the most consistent location for this repo):
- `datasets/<name>/manifest.json`
- `datasets/<name>/blueprint.json` (topic/skill weights, priority boosts, optional references)

Implement loader + merge logic:
- Default weights when no blueprint
- Blueprint boosts reprioritize weak skills / recommended practice focus

Provide one sample dataset `datasets/mock_exam_g5/` to prove the pipeline.

### E) Integration (minimal UI change)
Integrate into existing `docs/report/index.html` (and mirrored dist file) by adding:
- A “Generate Remediation Plan” button (or auto-run on refresh) that shows:
  - Top 3 weak skills + evidence
  - Suggested next practice focus + application mapping examples
- A “Plain text parent report” output (textarea + download) if not already present; reuse existing.

Keep the UI minimal and consistent with existing style.

### F) Tests
Add pytest tests (small fixtures) to ensure:
- Telemetry adapter correctness (time parsing, hint count, status mapping)
- Analytics metrics correctness (accuracy, hint dependency, trend)
- Weak-skill detection determinism (given fixtures → expected top weaknesses)
- Blueprint merge logic determinism

Add snapshot/golden tests for `RemediationPlan` JSON output stability.

### G) Commands / automation
- Add a script `scripts/precommit_check.py` (or similar) that runs:
  - `python scripts/verify_all.py`
  - `pytest -q`
  and exits non-zero on failure.

Optionally add a `.pre-commit-config.yaml` if the repo already uses pre-commit; otherwise keep it simple with the script.

---

## Implementation process
1) Inspect repo for existing telemetry schema, report aggregation logic, and test setup.
2) Propose minimal file changes and folder structure consistent with repo style.
3) Implement adapter + analytics + plan generator + dataset loader + tests.
4) Wire minimal UI integration.
5) Run verification + tests; only then commit.
6) Ensure docs/dist mirror stays identical and verification passes.

---

## Repo quality gate (must pass before commit)

This repo includes a one-command quality gate script:

- Run: `python scripts/precommit_check.py`

It executes:
- `python scripts/verify_all.py` (docs/dist mirror + endpoint health)
- `pytest -q` (deterministic test suite)

Do **not** commit unless it prints `OK: precommit_check` and exits with code 0.

---

## Acceptance criteria
- Analytics and remediation plan generated from real attempt telemetry without modifying exercise flows.
- Deterministic output for same inputs (tests enforce this).
- `python scripts/verify_all.py` passes.
- `pytest -q` passes.
- Final commit contains only relevant changes with clear message(s).
