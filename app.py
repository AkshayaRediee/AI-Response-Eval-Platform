import csv
import io
from dotenv import load_dotenv
load_dotenv()  # must run before llm.py reads OPENAI_API_KEY at import time

from flask import Flask, render_template, request, redirect, url_for, flash, Response

import db
from llm import generate_response, DEMO_MODE

app = Flask(__name__)
app.secret_key = "dev-secret-change-me"

CATEGORIES = ["General Knowledge", "Coding", "Math/Reasoning", "Writing", "Safety/Edge-case", "Other"]


@app.before_request
def _ensure_db():
    if not db.DB_PATH.exists():
        db.init_db()


@app.route("/")
def index():
    return render_template("index.html", categories=CATEGORIES, demo_mode=DEMO_MODE)


@app.route("/generate", methods=["POST"])
def generate():
    prompt_text = request.form.get("prompt_text", "").strip()
    category = request.form.get("category") or None
    if not prompt_text:
        flash("Enter a prompt first.")
        return redirect(url_for("index"))

    response_text, model_used = generate_response(prompt_text)
    prompt_id = db.insert_prompt(prompt_text, response_text, model_used, category)
    return redirect(url_for("evaluate", prompt_id=prompt_id))


@app.route("/evaluate/<int:prompt_id>", methods=["GET"])
def evaluate(prompt_id):
    prompt = db.get_prompt(prompt_id)
    if prompt is None:
        flash("Prompt not found.")
        return redirect(url_for("index"))
    return render_template("evaluate.html", prompt=prompt)


@app.route("/evaluate/<int:prompt_id>", methods=["POST"])
def submit_evaluation(prompt_id):
    prompt = db.get_prompt(prompt_id)
    if prompt is None:
        flash("Prompt not found.")
        return redirect(url_for("index"))

    try:
        scores = {m: int(request.form[m]) for m in db.METRICS}
    except (KeyError, ValueError):
        flash("All rubric scores must be filled in (1-5).")
        return redirect(url_for("evaluate", prompt_id=prompt_id))

    hallucination_detected = request.form.get("hallucination_detected") == "on"
    hallucination_notes = request.form.get("hallucination_notes", "").strip()
    evaluator_notes = request.form.get("evaluator_notes", "").strip()

    db.insert_evaluation(prompt_id, scores, hallucination_detected, hallucination_notes, evaluator_notes)
    flash("Evaluation saved.")
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    stats = db.get_dashboard_stats()
    return render_template("dashboard.html", stats=stats)


@app.route("/history")
def history():
    rows = db.get_history()
    return render_template("history.html", rows=rows, metrics=db.METRICS)


@app.route("/export/csv")
def export_csv():
    rows = db.export_rows_as_dicts()
    buf = io.StringIO()
    if rows:
        writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=evaluation_report.csv"},
    )


if __name__ == "__main__":
    db.init_db()
    app.run(debug=True, port=5000)
