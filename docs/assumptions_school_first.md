# Assumptions: School-first

## Active Assumptions

1. School-first work must preserve current parent-report, login, subscription, and snapshot flows.
Why: These are already hardened and tested.
Impact: New work stays additive.

2. Teacher uses the existing purchased-account auth path (`X-API-Key` + app user login) for MVP.
Why: Lowest-risk reuse of existing server-side identity.
Impact: No parallel auth system introduced in Phase 0-4.

3. Each teacher initially owns exactly one account and one or more classes under one school.
Why: Simplifies MVP scope enforcement.
Impact: Role/school/class schema can stay additive while still allowing future school_admin growth.

4. Before/after analytics are mock-first in early phases because current production schema does not yet store first-class pre/post/intervention records.
Why: User explicitly required mock-first sequencing.
Impact: Phase 1-4 deliver working mock evidence and analytics spec before real-data coupling.

5. `equivalent_group_id`, `skill_tag`, `knowledge_point`, and difficulty proximity are sufficient for same-ability comparison in MVP.
Why: Matches requested business rule for different-question comparison.
Impact: Reports must expose uncertainty and not overclaim exact equivalence.

6. UI MVP correctness is more important than visual polish.
Why: User explicitly prioritized function over aesthetics.
Impact: Simple, readable layouts are acceptable in this iteration.