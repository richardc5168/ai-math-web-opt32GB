# Event Model: School-first

## Required Events

### assessment_assigned
- `event_id`
- `assessment_id`
- `student_id`
- `class_id`
- `teacher_id`
- `timestamp`

### assessment_started
- `event_id`
- `assessment_id`
- `student_id`
- `timestamp`

### answer_submitted
- `event_id`
- `assessment_id`
- `student_id`
- `class_id`
- `question_id`
- `correctness`
- `hint_used`
- `attempt_count`
- `error_type`
- `response_time`
- `timestamp`

### assessment_completed
- `event_id`
- `assessment_id`
- `student_id`
- `class_id`
- `score`
- `timestamp`

### intervention_created
- `event_id`
- `intervention_id`
- `class_id`
- `teacher_id`
- `target_students`
- `target_skills`
- `timestamp`

### parent_report_generated
- `event_id`
- `student_id`
- `parent_account_id`
- `source_assessment_ids`
- `timestamp`

### before_after_report_generated
- `event_id`
- `scope` (`student` or `class`)
- `subject_id`
- `pre_assessment_ids`
- `post_assessment_ids`
- `comparison_basis`
- `timestamp`

## Traceability Rules

1. Every generated report must carry source ids.
2. Every remediation summary must reference source weak-skill evidence or intervention events.
3. Comparisons across different questions must declare uncertainty when equivalence is approximate rather than exact.