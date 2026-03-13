# Copilot Instructions — ai-math-web (Stability First)

## Role
You are an engineering agent working in this repo (`ai-math-web`). The product is an elementary math content supply chain. Stability and 100% correctness are top priority.

## MUST READ (Strict Workflow)
Before proposing ANY changes, you **MUST** read and follow the "AI Agent Workflow Instructions" in `README.md`.
For `exam-sprint` changes, also read `README.md` section **"Agent 快速問題點（Exam Sprint）"** first.

## Non-negotiables (do not violate)
1) **Stability First**: Do not break existing pipeline.
2) **No Hint Leaks**: Ensure NO Level 3 hint contains the final answer verbatim. Hints must guide, not solve.
3) **Strict Validation**:
   - **Local Check**: MUST pass `python tools/validate_all_elementary_banks.py` before any commit.
   - **Remote Check**: MUST pass `node tools/cross_validate_remote.cjs` after deployment.
4) **No Silent Failures**: Any invalid item must fail with explicit question id + reason.

## Definition of Done (DoD)
A change is complete ONLY when:
- **Local Validation**: `tools/validate_all_elementary_banks.py` outputs "ALL CHECKS PASSED".
- **Documentation**: Verify `README.md` instructions are followed.
- **Remote Verification**: Verify `tools/cross_validate_remote.cjs` passes (clean baseline or post-deployment).

## Atomic Changes Policy
- Make small, atomic changes. One commit should do one thing.
- If modifying validators/solver, add regression tests to prevent hint leaks.

---
**CRITICAL**: Always check `README.md` for the latest validation commands.

## Bank Expansion Optimization Memory (Auto-learned)
Before expanding any question bank (adding questions, increasing module counts), **MUST** consult the **Bank Expansion Playbook** in repo memory (`/memories/repo/bank-expansion-playbook.md`). It contains:
- Proven expansion script template (read→generate→verify→write to docs/ + dist/)
- L3 hint leak detection patterns and fixes (8 known leak types + template strategy per kind category)
- IEEE 754 precision avoidance (NEVER use `parseFloat()` for decimal answers)
- Bank format variations by module (meta, answer_mode, tags differ per module)
- ID naming conventions, answer format conventions
- Dashboard count update procedure
- Commit workflow with pre-commit hook gotchas
- Anti-patterns registry (AP-EXP-001 through AP-EXP-007)
- L3 hint template strategy by kind category (forward/reverse/conversion/decimal/composite)
- Iterative leak fix strategy (expect 2-5 iterations per 100-question expansion)

### Expansion Checklist:
1. Read playbook → understand the target module's format
2. Inspect first question's keys via `node -e` before writing code
3. Generate with integer arithmetic, verify L3 leaks in-script
4. Write to BOTH `docs/` and `dist_ai_math_web_pages/docs/`
5. Run `validate_all_elementary_banks.py` → must be 0 FAIL
6. Update dashboard counts if crossing a hundred boundary
7. Commit with descriptive message, push

## Hint/Diagram Optimization Memory (Auto-learned)
Before modifying `docs/shared/hint_engine.js` or any diagram rendering, **MUST** consult `tools/hint_diagram_known_issues.json` for past issues and anti-patterns. After every fix, update the registry.

### Known Anti-Patterns (DO NOT reintroduce):
1. **AP-001**: Never use `extractIntegers()[2]` as height for volume diagrams — use `parseVolumeDims(text, kind)`.
2. **AP-002**: Never render `buildFractionBarSVG` (remainder diagram) for fraction addition word problems — check `isFracAddition` first.
3. **AP-003**: Every SVG dimension label must have a colour-coded arrow marker (not bare text).
4. **AP-004**: Pure calculations (`isPureCalculation()`) must skip diagrams and show text-based steps.

### Validation Gate:
- Run `node tools/audit_hint_diagrams.cjs` before committing any hint_engine.js changes.
- This audit is also run automatically in the 12h autonomous runner (Phase 4).
- After editing `docs/shared/hint_engine.js`, always sync to `dist_ai_math_web_pages/docs/shared/hint_engine.js`.

## Mathgen System — Compounding Iteration Rules (Auto-learned)
Before modifying ANY file under `mathgen/`, you **MUST** follow these rules:

### Pre-flight (MUST DO before any change):
1. Read `mathgen/logs/lessons_learned.jsonl` — accumulated lessons from all past iterations
2. Read `mathgen/logs/change_history.jsonl` — anti-repeat: check if your planned fix was recently tried
3. Read `mathgen/logs/last_pass_rate.json` — current baseline (DO NOT regress)
4. Run `python mathgen/scripts/run_full_cycle.py` to confirm current state

### During Change:
5. ONE error category per iteration — never batch multiple fix types
6. Add benchmark case BEFORE fixing the generator (test-first)
7. All arithmetic MUST use integer operations (IEEE 754 avoidance)
8. Hints MUST NOT contain the final answer verbatim (leak check)
9. If a fix approach was recently tried (per change_history), try a DIFFERENT strategy

### Post-flight (MUST DO after every change):
10. Run `python mathgen/scripts/run_full_cycle.py --changes "description of change"`
11. Verify exit code 0 (all benchmarks pass, no regression)
12. The full cycle script auto-records lessons, updates baseline, generates iteration report
13. Only then commit: `git add mathgen/ && git commit`

### Key Files:
- `mathgen/logs/lessons_learned.jsonl` — structured learning ledger (auto-accumulates)
- `mathgen/logs/change_history.jsonl` — anti-repeat mechanism
- `mathgen/logs/last_pass_rate.json` — regression gate baseline
- `mathgen/reports/latest_iteration_report.md` — latest iteration report
- `mathgen/reports/history/` — all past iteration reports
- `mathgen/docs/` — schema, hint rules, error taxonomy, model policy

### Architecture:
- 4 generators: fraction_word_problem, decimal_word_problem, average_word_problem, unit_conversion
- 3 validators: schema, hint_ladder, report
- Error taxonomy: 13 known error codes + auto-classifier
- Gold bank: 5 exemplar questions per topic
- Benchmark: 10 cases per topic (40 total)
- Pre-commit gate: auto-runs benchmarks when mathgen/ files are staged
