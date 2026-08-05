# Eval Bench — AI Response Evaluation Platform

A small end-to-end pipeline for evaluating LLM outputs: send a prompt to the OpenAI API,
score the response against a 7-dimension rubric, store everything in SQL, and roll it up
into a dashboard (with a CSV export for Power BI).

This mirrors the kind of human-evaluation workflow used by AI training-data / RLHF
fellowship programs (e.g. Handshake AI Fellows): generate → grade → aggregate → report.

## What it does

1. **Ask** — submit a prompt, the app calls the OpenAI API and stores the response.
2. **Grade** — score the response 1–5 on: Accuracy, Helpfulness, Safety, Clarity,
   Completeness, Reasoning — plus a binary Hallucination flag with free-text notes.
3. **Store** — every prompt/response/score lands in SQLite via plain SQL (see `schema.sql`).
4. **Report** — `/dashboard` shows average quality score, hallucination rate, best/worst
   prompts, per-category breakdown, and a quality trend chart. `/export/csv` gives you a
   flat file for Power BI, Excel, or any other BI tool.

## Tech stack

Python · Flask · SQLite (plain SQL, no ORM) · OpenAI API · Chart.js (dashboard) · Power BI (via CSV/ODBC)

## Quick start

```bash
python -m venv venv
source venv/bin/activate        # venv\Scripts\activate on Windows
pip install -r requirements.txt

cp .env.example .env             # then add your real OPENAI_API_KEY
python seed_demo.py               # optional: loads 15 realistic sample evaluations
python app.py
```

Open **http://127.0.0.1:5000**.

**No API key?** The app still runs — it falls back to canned demo responses (clearly
labeled `[DEMO MODE]`) so you can exercise the full grading + dashboard flow without
spending API credits. Add `OPENAI_API_KEY` to `.env` to hit the real API.

## Project structure

```
app.py            Flask routes (generate → evaluate → dashboard → history → export)
db.py             All SQL: schema init, inserts, aggregate queries
llm.py            OpenAI call wrapper + demo-mode fallback
schema.sql        Table/view definitions (prompts, evaluations, v_evaluation_report)
seed_demo.py       Loads realistic sample data for a populated dashboard
templates/        Jinja2 templates (index, evaluate, dashboard, history)
static/style.css  Styling
```

## Database schema

```
prompts(id, prompt_text, response_text, model, category, created_at)
evaluations(id, prompt_id → prompts.id,
            accuracy, helpfulness, safety, clarity, completeness, reasoning,   -- 1–5 each
            hallucination_detected, hallucination_notes,
            overall_score,          -- avg of the 6 rubric scores, computed at insert time
            evaluator_notes, created_at)
```

`v_evaluation_report` is a view that joins the two tables into one flat row per
evaluation — that's what `/export/csv` and the Power BI connection both read from.

Key queries (see `db.py::get_dashboard_stats`):
- **Avg quality score** — `AVG(overall_score)` across all evaluations
- **Hallucination rate** — `100.0 * SUM(hallucination_detected) / COUNT(*)`
- **Best/worst prompts** — `ORDER BY overall_score DESC/ASC LIMIT 5`
- **By category** — `GROUP BY category`
- **Trend** — `GROUP BY DATE(created_at)`

## Connecting Power BI

Two options, from quickest to most "live":

**Option A — CSV import (simplest)**
1. Run the app, hit `/export/csv` (or click "Export CSV" in the nav).
2. In Power BI Desktop: Get Data → Text/CSV → select the downloaded file.
3. Build visuals directly from the flat `v_evaluation_report` columns — score cards for
   `avg(overall_score)` and `avg(hallucination_detected)*100`, a table for best/worst
   prompts sorted by `overall_score`, and a line chart of `overall_score` by `asked_at`.

**Option B — Direct SQLite connection (live refresh)**
1. Install a SQLite ODBC driver (e.g. [sqliteodbc](http://www.ch-werner.de/sqliteodbc/)).
2. In Power BI Desktop: Get Data → ODBC → point it at `eval_platform.db`.
3. Import the `v_evaluation_report` view — Power BI can then refresh on demand as new
   evaluations are logged.

If you later move this to Postgres/SQL Server (recommended for a multi-user deployment),
Power BI's native connectors make Option B a direct "Get Data → SQL Server" instead.

## Notes on design choices

- **Raw SQL over an ORM** — the point of this project is demonstrating SQL fluency
  (aggregations, views, joins), so `db.py` is deliberately plain `sqlite3` + hand-written
  queries rather than SQLAlchemy models.
- **`overall_score` is denormalized** (computed once at insert time, not recalculated on
  every read) — a common real-world trade-off: faster dashboard queries at the cost of
  needing a backfill script if the scoring formula ever changes.
- **Demo mode** exists so the project is fully clickable/screenshot-able without
  requiring anyone (including you, in an interview) to have an API key on hand.
