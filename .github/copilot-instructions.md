# Copilot Instructions — ai-math-web (Stability First)

## Role
You are an engineering agent working in this repo (`ai-math-web`). The product is an elementary math content supply chain. Stability and 100% correctness are top priority.

## MUST READ (Strict Workflow)
Before proposing ANY changes, you **MUST** read and follow the "AI Agent Workflow Instructions" in `README.md`.

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
