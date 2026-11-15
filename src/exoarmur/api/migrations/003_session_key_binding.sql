-- Bind operator sessions to the exact API-key record that issued them.
-- Sessions created before this binding existed cannot be trusted to a
-- specific key and are invalidated.

ALTER TABLE operator_sessions
    ADD COLUMN IF NOT EXISTS key_hash TEXT;

DELETE FROM operator_sessions WHERE key_hash IS NULL;
