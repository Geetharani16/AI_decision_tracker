from flask import (
    Flask, render_template, request, redirect,
    url_for, jsonify, Response, session
)
from functools import wraps
import sqlite3
import json
import requests
from datetime import datetime
import os
import time

app = Flask(__name__)

# --------------------------------------------------
# FLASK CONFIGURATION
# --------------------------------------------------

app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "development-key-change-before-deployment"
)

DEMO_USERNAME = os.environ.get("APP_USERNAME", "admin")
DEMO_PASSWORD = os.environ.get("APP_PASSWORD", "Decision@123")

# Keep the existing database filename
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "decisions.db")


# --------------------------------------------------
# DATABASE INITIALIZATION
# --------------------------------------------------

def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            reasoning TEXT,
            expected_outcome TEXT,
            actual_outcome TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


init_db()


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# --------------------------------------------------
# LOGIN AUTHENTICATION
# --------------------------------------------------

def login_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return view_function(*args, **kwargs)

    return wrapped_view


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("index"))

    error = None

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if username == DEMO_USERNAME and password == DEMO_PASSWORD:
            session.clear()
            session["logged_in"] = True
            return redirect(url_for("index"))

        error = "Invalid username or password."

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# --------------------------------------------------
# MAIN DASHBOARD
# --------------------------------------------------

@app.route("/")
@login_required
def index():
    return render_template("index.html")


# --------------------------------------------------
# GET ALL DECISIONS
# --------------------------------------------------

@app.route("/decisions")
@login_required
def get_decisions():
    conn = get_db_connection()

    decisions = conn.execute(
        "SELECT * FROM decisions ORDER BY created_at DESC"
    ).fetchall()

    conn.close()

    decisions_list = [dict(decision) for decision in decisions]

    return jsonify(decisions_list)


# --------------------------------------------------
# ADD A DECISION
# --------------------------------------------------

@app.route("/add_decision", methods=["POST"])
@login_required
def add_decision():
    data = request.get_json(silent=True) or {}

    title = data.get("title")
    reasoning = data.get("reasoning")
    expected_outcome = data.get("expected_outcome")
    actual_outcome = data.get("actual_outcome")

    if not title:
        return jsonify({"error": "Title is required"}), 400

    conn = get_db_connection()

    c = conn.cursor()

    c.execute(
        """
        INSERT INTO decisions
        (title, reasoning, expected_outcome, actual_outcome)
        VALUES (?, ?, ?, ?)
        """,
        (
            title,
            reasoning,
            expected_outcome,
            actual_outcome or None
        )
    )

    decision_id = c.lastrowid

    conn.commit()
    conn.close()

    return jsonify({
        "id": decision_id,
        "message": "Decision added successfully"
    })


# --------------------------------------------------
# UPDATE A DECISION OUTCOME
# --------------------------------------------------

@app.route("/update_outcome/<int:decision_id>", methods=["POST"])
@login_required
def update_outcome(decision_id):
    data = request.get_json(silent=True) or {}

    actual_outcome = data.get("actual_outcome")

    if not actual_outcome:
        return jsonify({
            "error": "Actual outcome is required"
        }), 400

    conn = get_db_connection()

    c = conn.cursor()

    c.execute(
        """
        UPDATE decisions
        SET actual_outcome = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (actual_outcome, decision_id)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Outcome updated successfully"
    })


# --------------------------------------------------
# DELETE A DECISION
# --------------------------------------------------

@app.route("/delete_decision/<int:decision_id>", methods=["DELETE"])
@login_required
def delete_decision(decision_id):
    conn = get_db_connection()

    c = conn.cursor()

    c.execute(
        "DELETE FROM decisions WHERE id = ?",
        (decision_id,)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Decision deleted successfully"
    })


# --------------------------------------------------
# OLLAMA AI API WITH STREAMING
# --------------------------------------------------

def call_ollama_api(prompt):
    try:
        with requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "gemma3:1b",
                "prompt": prompt,
                "stream": True
            },
            stream=True,
            timeout=(10, 300)
        ) as response:

            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode("utf-8")

                        try:
                            json_data = json.loads(decoded_line)

                            if "response" in json_data:
                                yield json_data["response"]

                            if json_data.get("done", False):
                                break

                        except json.JSONDecodeError:
                            continue

            else:
                yield (
                    f"Error: {response.status_code} - "
                    f"{response.text}"
                )

    except Exception as e:
        yield f"Error connecting to Ollama: {str(e)}"


# --------------------------------------------------
# ANALYZE A SINGLE DECISION
# --------------------------------------------------

def stream_analysis_for_decision(decision_id):
    conn = get_db_connection()

    decision = conn.execute(
        "SELECT * FROM decisions WHERE id = ?",
        (decision_id,)
    ).fetchone()

    conn.close()

    if not decision:
        yield f"data: {json.dumps({'error': 'Decision not found'})}\n\n"
        return

    decision_dict = dict(decision)

    prompt = f"""
Analyze this decision and provide a concise, well-formatted response
with key insights.

CONTEXT - Decision Details:
- Title: {decision_dict['title']}
- Reasoning: {decision_dict['reasoning']}
- Expected Outcome: {decision_dict['expected_outcome']}
- Actual Outcome: {decision_dict['actual_outcome'] or 'Not recorded yet'}

INSTRUCTIONS:
1. Provide a brief but comprehensive analysis.
2. Format the response with clear sections.
3. Highlight key points.
4. Give specific and actionable suggestions.
5. Structure the response as follows:
   - COMPARISON: Expected versus actual outcome
   - KEY INSIGHTS: Important findings
   - LESSONS: Lessons learned
   - RECOMMENDATIONS: Suggestions for the future

Format the response using Markdown.
Keep the response concise but insightful.
"""

    full_response = ""

    for chunk in call_ollama_api(prompt):
        full_response += chunk

        yield (
            f"data: {json.dumps({'chunk': chunk})}\n\n"
        )

    yield (
        "data: "
        + json.dumps({
            "complete": True,
            "full_response": full_response
        })
        + "\n\n"
    )

    yield "data: [DONE]\n\n"


# --------------------------------------------------
# ANALYZE ALL DECISIONS
# --------------------------------------------------

def stream_analysis_for_all_decisions():
    conn = get_db_connection()

    decisions = conn.execute(
        "SELECT * FROM decisions ORDER BY created_at DESC"
    ).fetchall()

    conn.close()

    decisions_list = [dict(decision) for decision in decisions]

    if not decisions_list:
        yield (
            f"data: {json.dumps({'error': 'No decisions found'})}\n\n"
        )
        return

    prompt = f"""
Analyze all these decisions and provide a concise, comprehensive analysis.

CONTEXT - All Decisions Data:
{json.dumps(decisions_list, indent=2, default=str)}

INSTRUCTIONS:
1. Identify important patterns across decisions.
2. Estimate the success rate where possible.
3. Identify common themes.
4. Explain key learnings.
5. Provide actionable recommendations.

Structure the response as follows:
- OVERALL PATTERNS
- SUCCESS RATE
- COMMON THEMES
- KEY LEARNINGS
- RECOMMENDATIONS

Format the response using Markdown.
Keep it concise but insightful.
"""

    full_response = ""

    for chunk in call_ollama_api(prompt):
        full_response += chunk

        yield (
            f"data: {json.dumps({'chunk': chunk})}\n\n"
        )

    yield (
        "data: "
        + json.dumps({
            "complete": True,
            "full_response": full_response,
            "decision_count": len(decisions_list)
        })
        + "\n\n"
    )

    yield "data: [DONE]\n\n"


# --------------------------------------------------
# AI ANALYSIS ROUTES
# --------------------------------------------------

@app.route("/analyze_decision/<int:decision_id>")
@login_required
def analyze_decision(decision_id):
    return Response(
        stream_analysis_for_decision(decision_id),
        mimetype="text/event-stream"
    )


@app.route("/analyze_all_decisions")
@login_required
def analyze_all_decisions():
    return Response(
        stream_analysis_for_all_decisions(),
        mimetype="text/event-stream"
    )


# --------------------------------------------------
# DECISION DETAILS PAGE
# --------------------------------------------------

@app.route("/decision/<int:decision_id>")
@login_required
def decision_detail(decision_id):
    conn = get_db_connection()

    decision = conn.execute(
        "SELECT * FROM decisions WHERE id = ?",
        (decision_id,)
    ).fetchone()

    conn.close()

    if not decision:
        return jsonify({
            "error": "Decision not found"
        }), 404

    return render_template(
        "decision_detail.html",
        decision=dict(decision)
    )


# --------------------------------------------------
# GET A SINGLE DECISION AS JSON
# --------------------------------------------------

@app.route("/decision_data/<int:decision_id>")
@login_required
def get_decision(decision_id):
    conn = get_db_connection()

    decision = conn.execute(
        "SELECT * FROM decisions WHERE id = ?",
        (decision_id,)
    ).fetchone()

    conn.close()

    if not decision:
        return jsonify({
            "error": "Decision not found"
        }), 404

    return jsonify(dict(decision))


# --------------------------------------------------
# RUN THE APPLICATION
# --------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)