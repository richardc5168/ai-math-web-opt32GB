# Before/After Analytics Spec

## Comparison Rule

Pre and post questions may differ, but the system must compare only when these attributes are aligned or near-aligned:

- `equivalent_group_id`
- `skill_tag`
- `knowledge_point`
- same or adjacent difficulty bucket

## Output Labels

- `improved`
- `flat`
- `regressed`
- `insufficient_evidence`

## Student-Level Output

- pre accuracy
- post accuracy
- delta
- compared skill groups
- uncertainty notes

## Class-Level Output

- improved count
- flat count
- regressed count
- high-risk not improved list
- top improving skill groups

## Required Warnings

- If question sets are not exactly identical, report must state comparison is ability-based, not same-item based.
- If the equivalent group coverage is too low, mark result as `insufficient_evidence`.