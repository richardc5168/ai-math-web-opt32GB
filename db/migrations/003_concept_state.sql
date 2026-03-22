-- Student per-concept mastery state

CREATE TABLE IF NOT EXISTS la_student_concept_state (
  student_id TEXT NOT NULL,
  concept_id TEXT NOT NULL,
  mastery_level TEXT NOT NULL DEFAULT 'unbuilt',
  mastery_score REAL NOT NULL DEFAULT 0.0,
  recent_accuracy REAL,
  hint_dependency REAL DEFAULT 0.0,
  avg_response_time_sec REAL,
  attempts_total INTEGER DEFAULT 0,
  correct_total INTEGER DEFAULT 0,
  correct_no_hint INTEGER DEFAULT 0,
  correct_with_hint INTEGER DEFAULT 0,
  consecutive_correct INTEGER DEFAULT 0,
  consecutive_wrong INTEGER DEFAULT 0,
  transfer_success_count INTEGER DEFAULT 0,
  delayed_review_status TEXT DEFAULT 'none',
  needs_review INTEGER DEFAULT 0,
  last_seen_at TEXT,
  last_mastered_at TEXT,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (student_id, concept_id)
);

CREATE INDEX IF NOT EXISTS idx_la_concept_state_student ON la_student_concept_state(student_id);
CREATE INDEX IF NOT EXISTS idx_la_concept_state_level ON la_student_concept_state(mastery_level);
CREATE INDEX IF NOT EXISTS idx_la_concept_state_review ON la_student_concept_state(needs_review);
