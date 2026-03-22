# Teacher Dashboard MVP

## Required Panels

1. Class overview
2. Student list (58 students target)
3. Risk-ranked students
4. Skill / knowledge point performance table
5. Pre-test summary
6. Intervention recommendations
7. Post-test summary
8. Before/after chart
9. Student drill-down

## MVP Data Strategy

- Phase 1-4: mock-first with fixture-backed rendering
- Phase 5+: real backend class report endpoint

## Teacher Questions This Page Must Answer

- Which students are high risk right now?
- Which skills are weakest for the class?
- Which intervention should I assign next?
- Did the class improve after intervention?

## Server-side Entitlement Requirement

All class data requests must be filtered by teacher-owned class scope in backend SQL, never by frontend-only filtering.