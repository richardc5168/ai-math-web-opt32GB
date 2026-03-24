-- Promote hint evidence fields from extra_json to first-class columns
-- for direct indexing, filtering, and analytics without JSON parsing.

ALTER TABLE la_attempt_events ADD COLUMN hint_level_used INTEGER;
ALTER TABLE la_attempt_events ADD COLUMN success_after_hint INTEGER;
