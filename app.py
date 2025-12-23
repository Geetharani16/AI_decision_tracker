from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import requests
import os

app = Flask(__name__)

# -------------------------------------------------
# Database Connection
# -------------------------------------------------
def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

# -------------------------------------------------
# Database Initialization
# -------------------------------------------------
def init_db():
    """Initialize the database with the decisions table"""
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    # Create the decisions table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            reasoning TEXT NOT NULL,
            expected_outcome TEXT NOT NULL,
            actual_outcome TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

# -------------------------------------------------
# Home Page
# -------------------------------------------------
@app.route("/")
def home():
    return render_template("home.html")

# -------------------------------------------------
# Add Decision
# -------------------------------------------------
@app.route("/add-decision", methods=["GET", "POST"])
def add_decision():
    if request.method == "POST":
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO decisions (title, reasoning, expected_outcome) VALUES (?, ?, ?)",
            (
                request.form["title"],
                request.form["reasoning"],
                request.form["expected_outcome"],
            ),
        )
        conn.commit()
        conn.close()
        return redirect(url_for("history"))
    return render_template("add_decision.html")

# -------------------------------------------------
# History Page
# -------------------------------------------------
@app.route("/history")
def history():
    conn = get_db_connection()
    decisions = conn.execute("SELECT * FROM decisions").fetchall()
    conn.close()
    return render_template("history.html", decisions=decisions)

# -------------------------------------------------
# Add Actual Outcome
# -------------------------------------------------
@app.route("/add-outcome/<int:decision_id>", methods=["GET", "POST"])
def add_outcome(decision_id):
    if request.method == "POST":
        conn = get_db_connection()
        conn.execute(
            "UPDATE decisions SET actual_outcome=? WHERE id=?",
            (request.form["actual_outcome"], decision_id),
        )
        conn.commit()
        conn.close()
        return redirect(url_for("history"))
    return render_template("add_outcome.html", decision_id=decision_id)

# -------------------------------------------------
# AI ANALYZE ALL DECISIONS ✅ (Using Ollama)
# -------------------------------------------------
@app.route("/analyze-all")
def analyze_all():
    conn = get_db_connection()
    decisions = conn.execute(
        "SELECT * FROM decisions WHERE actual_outcome IS NOT NULL"
    ).fetchall()
    conn.close()

    if not decisions:
        return render_template(
            "analysis_all.html",
            analysis="<p>No decisions with actual outcomes yet.</p>",
        )

    prompt = """
You are an AI assistant that helps users learn from past decisions.

For each decision, analyze:
- Comparison Analysis
- Invalid Assumptions
- Lessons Learned
- Future Suggestions

Use clear bullet points.
"""

    for d in decisions:
        prompt += f"""
Title: {d['title']}
Reasoning: {d['reasoning']}
Expected Outcome: {d['expected_outcome']}
Actual Outcome: {d['actual_outcome']}
---
"""

    # Ollama API call
    ollama_url = "http://localhost:11434/api/generate"
    
    data = {
        "model": "gemma3:1b",
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(
            ollama_url,
            json=data,
        )
        
        if response.status_code != 200:
            analysis = f"Ollama Error {response.status_code}<br>{response.text}"
        else:
            response_json = response.json()
            analysis = response_json.get("response", "No response from Ollama")
            
    except requests.exceptions.ConnectionError:
        analysis = "Error: Could not connect to Ollama. Please make sure Ollama is running on localhost:11434 and the gemma3:1b model is available."

    return render_template("analysis_all.html", analysis=analysis)

# -------------------------------------------------
# AI ANALYZE SINGLE DECISION ✅ (Using Ollama)
# -------------------------------------------------
@app.route("/analyze/<int:decision_id>")
def analyze_single(decision_id):
    conn = get_db_connection()
    decision = conn.execute(
        "SELECT * FROM decisions WHERE id=?",
        (decision_id,),
    ).fetchone()
    conn.close()

    if decision is None or decision["actual_outcome"] is None:
        return render_template(
            "analysis_single.html",
            analysis="Decision not found or actual outcome not added.",
            decision=decision,
        )

    prompt = f"""
Analyze this decision.

<h3>Comparison Analysis</h3>
<ul>
<li>Expected: {decision['expected_outcome']}</li>
<li>Actual: {decision['actual_outcome']}</li>
</ul>

<h3>Invalid Assumptions</h3>
<ul><li>Identify wrong assumptions</li></ul>

<h3>Lessons Learned</h3>
<ul><li>Key takeaways</li></ul>

<h3>Future Suggestions</h3>
<ul><li>How to improve future decisions</li></ul>
"""

    # Ollama API call
    ollama_url = "http://localhost:11434/api/generate"
    
    data = {
        "model": "gemma3:1b",
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(
            ollama_url,
            json=data,
        )
        
        if response.status_code != 200:
            analysis = f"Ollama Error {response.status_code}<br>{response.text}"
        else:
            response_json = response.json()
            analysis = response_json.get("response", "No response from Ollama")
            
    except requests.exceptions.ConnectionError:
        analysis = "Error: Could not connect to Ollama. Please make sure Ollama is running on localhost:11434 and the gemma3:1b model is available."

    return render_template(
        "analysis_single.html",
        analysis=analysis,
        decision=decision,
    )

# -------------------------------------------------
# Delete Decision
# -------------------------------------------------
@app.route("/delete/<int:decision_id>")
def delete_decision(decision_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM decisions WHERE id=?", (decision_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("history"))

# -------------------------------------------------
# Run App
# -------------------------------------------------
if __name__ == "__main__":
    init_db()  # Initialize database on startup
    app.run(debug=True)