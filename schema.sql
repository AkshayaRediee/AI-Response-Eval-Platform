-- Response Evaluation Platform schema
-- SQLite (portable to Postgres/MySQL with minor type changes)

CREATE TABLE IF NOT EXISTS prompts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_text   TEXT NOT NULL,
    response_text TEXT NOT NULL,
    model         TEXT NOT NULL DEFAULT 'gpt-4o-mini',
    category      TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS evaluations (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_id               INTEGER NOT NULL REFERENCES prompts(id) ON DELETE CASCADE,
    accuracy                INTEGER NOT NULL CHECK (accuracy BETWEEN 1 AND 5),
    helpfulness             INTEGER NOT NULL CHECK (helpfulness BETWEEN 1 AND 5),
    safety                  INTEGER NOT NULL CHECK (safety BETWEEN 1 AND 5),
    clarity                 INTEGER NOT NULL CHECK (clarity BETWEEN 1 AND 5),
    completeness            INTEGER NOT NULL CHECK (completeness BETWEEN 1 AND 5),
    reasoning               INTEGER NOT NULL CHECK (reasoning BETWEEN 1 AND 5),
    hallucination_detected  INTEGER NOT NULL DEFAULT 0 CHECK (hallucination_detected IN (0, 1)),
    hallucination_notes     TEXT,
    overall_score           REAL NOT NULL,
    evaluator_notes         TEXT,
    created_at              TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_evaluations_prompt_id ON evaluations(prompt_id);
CREATE INDEX IF NOT EXISTS idx_evaluations_created_at ON evaluations(created_at);

-- Handy view: one row per evaluated prompt, ready for BI tools
CREATE VIEW IF NOT EXISTS v_evaluation_report AS
SELECT
    p.id               AS prompt_id,
    p.prompt_text,
    p.response_text,
    p.model,
    p.category,
    p.created_at       AS asked_at,
    e.accuracy, e.helpfulness, e.safety, e.clarity, e.completeness, e.reasoning,
    e.hallucination_detected,
    e.hallucination_notes,
    e.overall_score,
    e.evaluator_notes,
    e.created_at        AS evaluated_at
FROM prompts p
JOIN evaluations e ON e.prompt_id = p.id;
