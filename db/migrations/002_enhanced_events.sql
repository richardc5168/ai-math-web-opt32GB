-- Enhanced answer event logging (backward-compatible additions)
-- All new columns are NULLABLE or have DEFAULT values
-- Note: SQLite ignores duplicate ADD COLUMN errors when run via executescript

-- Create a temp table to track which columns exist, then add missing ones.
-- SQLite has no IF NOT EXISTS for ALTER TABLE, so we use a helper approach:
-- The migration system only runs this file once (tracked in schema_migrations).

ALTER TABLE la_attempt_events ADD COLUMN started_at TEXT;
ALTER TABLE la_attempt_events ADD COLUMN first_answer TEXT;
ALTER TABLE la_attempt_events ADD COLUMN attempts_count INTEGER DEFAULT 1;
ALTER TABLE la_attempt_events ADD COLUMN changed_answer INTEGER DEFAULT 0;
ALTER TABLE la_attempt_events ADD COLUMN selection_reason TEXT;
ALTER TABLE la_attempt_events ADD COLUMN concept_ids_json TEXT DEFAULT '[]';
ALTER TABLE la_attempt_events ADD COLUMN remediation_triggered INTEGER DEFAULT 0;
ALTER TABLE la_attempt_events ADD COLUMN prerequisite_fallback INTEGER DEFAULT 0;
ALTER TABLE la_attempt_events ADD COLUMN error_type TEXT;
