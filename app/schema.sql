-- Schéma de la to-do list. Idempotent : peut être rejoué sans perdre de données
-- (aucun DROP TABLE, les tâches ne sont jamais supprimées).
CREATE TABLE IF NOT EXISTS tasks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT    NOT NULL CHECK (length(trim(title)) > 0),
    status       TEXT    NOT NULL DEFAULT 'todo' CHECK (status IN ('todo', 'done')),
    created_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_tasks_status_created ON tasks (status, created_at, id);
