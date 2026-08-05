"""
Thin data-access layer over SQLite. All queries are plain SQL on purpose —
this is a portfolio piece about SQL/analytics fluency, not ORM abstraction.
Swap the connect() function for psycopg2/pyodbc if you move to Postgres/SQL Server.
"""
import sqlite3
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(__file__).parent / "eval_platform.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

METRICS = ["accuracy", "helpfulness", "safety", "clarity", "completeness", "reasoning"]


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_conn():
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA_PATH.read_text())


def insert_prompt(prompt_text: str, response_text: str, model: str, category: str | None) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO prompts (prompt_text, response_text, model, category) VALUES (?, ?, ?, ?)",
            (prompt_text, response_text, model, category),
        )
        return cur.lastrowid


def get_prompt(prompt_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM prompts WHERE id = ?", (prompt_id,)).fetchone()


def insert_evaluation(prompt_id: int, scores: dict, hallucination_detected: bool,
                       hallucination_notes: str, evaluator_notes: str) -> int:
    overall = sum(scores[m] for m in METRICS) / len(METRICS)
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO evaluations
               (prompt_id, accuracy, helpfulness, safety, clarity, completeness, reasoning,
                hallucination_detected, hallucination_notes, overall_score, evaluator_notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (prompt_id, scores["accuracy"], scores["helpfulness"], scores["safety"],
             scores["clarity"], scores["completeness"], scores["reasoning"],
             int(hallucination_detected), hallucination_notes, overall, evaluator_notes),
        )
        return cur.lastrowid


def get_dashboard_stats():
    with get_conn() as conn:
        summary = conn.execute("""
            SELECT
                COUNT(*)                                              AS total_evaluations,
                ROUND(AVG(overall_score), 2)                          AS avg_quality_score,
                ROUND(100.0 * SUM(hallucination_detected) / COUNT(*), 1) AS hallucination_rate,
                ROUND(AVG(accuracy), 2)      AS avg_accuracy,
                ROUND(AVG(helpfulness), 2)   AS avg_helpfulness,
                ROUND(AVG(safety), 2)        AS avg_safety,
                ROUND(AVG(clarity), 2)       AS avg_clarity,
                ROUND(AVG(completeness), 2)  AS avg_completeness,
                ROUND(AVG(reasoning), 2)     AS avg_reasoning
            FROM evaluations
        """).fetchone()

        best = conn.execute("""
            SELECT p.id, p.prompt_text, p.model, p.category, e.overall_score, e.hallucination_detected
            FROM prompts p JOIN evaluations e ON e.prompt_id = p.id
            ORDER BY e.overall_score DESC, e.created_at DESC
            LIMIT 5
        """).fetchall()

        worst = conn.execute("""
            SELECT p.id, p.prompt_text, p.model, p.category, e.overall_score, e.hallucination_detected
            FROM prompts p JOIN evaluations e ON e.prompt_id = p.id
            ORDER BY e.overall_score ASC, e.created_at DESC
            LIMIT 5
        """).fetchall()

        by_category = conn.execute("""
            SELECT COALESCE(p.category, 'Uncategorized') AS category,
                   COUNT(*) AS n,
                   ROUND(AVG(e.overall_score), 2) AS avg_score,
                   ROUND(100.0 * SUM(e.hallucination_detected) / COUNT(*), 1) AS hallucination_rate
            FROM prompts p JOIN evaluations e ON e.prompt_id = p.id
            GROUP BY category
            ORDER BY avg_score DESC
        """).fetchall()

        trend = conn.execute("""
            SELECT DATE(e.created_at) AS day,
                   ROUND(AVG(e.overall_score), 2) AS avg_score,
                   COUNT(*) AS n
            FROM evaluations e
            GROUP BY DATE(e.created_at)
            ORDER BY day
        """).fetchall()

        return {
            "summary": summary,
            "best": best,
            "worst": worst,
            "by_category": by_category,
            "trend": [dict(r) for r in trend],  # plain dicts so Jinja's |tojson can serialize them
        }


def get_history():
    with get_conn() as conn:
        return conn.execute("""
            SELECT p.id, p.prompt_text, p.response_text, p.model, p.category, p.created_at,
                   e.accuracy, e.helpfulness, e.safety, e.clarity, e.completeness, e.reasoning,
                   e.hallucination_detected, e.overall_score, e.evaluator_notes
            FROM prompts p JOIN evaluations e ON e.prompt_id = p.id
            ORDER BY e.created_at DESC
        """).fetchall()


def export_rows_as_dicts():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM v_evaluation_report ORDER BY evaluated_at").fetchall()
        return [dict(r) for r in rows]
