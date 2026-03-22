# Data Model: School-first

## Core Entities

### School
- `school_id`
- `name`
- `school_code`
- `max_seats`
- `active`

### RoleAssignment
- `account_id`
- `role`
- `school_id`

### Class
- `class_id`
- `school_id`
- `teacher_account_id`
- `name`
- `grade`

### Student
- `student_id`
- `account_id`
- `class_id` or class membership via join table
- `display_name`
- `grade`
- `parent_account_id` or parent relation in fixtures/event layer

### QuestionMetadata
- `question_id`
- `topic`
- `subtopic`
- `skill_tag`
- `knowledge_point`
- `difficulty`
- `pattern_type`
- `equivalent_group_id`

### Assessment
- `assessment_id`
- `student_id`
- `class_id`
- `assessment_type` (`pre_test`, `post_test`, `practice`)
- `assigned_at`
- `started_at`
- `completed_at`

### AnswerRecord
- `assessment_id`
- `student_id`
- `class_id`
- `question_id`
- `answer`
- `correctness`
- `response_time`
- `hint_used`
- `attempt_count`
- `error_type`
- `timestamp`

### InterventionRecord
- `intervention_id`
- `class_id`
- `teacher_id`
- `date`
- `target_students`
- `target_skills`
- `teaching_method`
- `notes`
- `linked_pretest_id`
- `linked_posttest_id`

## Comparison Model

Before/after comparisons may use different question ids, but must align on:

- `equivalent_group_id`
- `skill_tag`
- `knowledge_point`
- comparable difficulty bucket

## Output Views

- Parent child report
- Teacher class dashboard
- Admin platform dashboard
- Individual before/after summary
- Class before/after summary