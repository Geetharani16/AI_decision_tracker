from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
import sqlite3
import json
import requests
from datetime import datetime
import os
import time

app = Flask(__name__)

# Database initialization
def init_db():
    conn = sqlite3.connect('decisions.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS decisions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT NOT NULL,
                  reasoning TEXT,
                  expected_outcome TEXT,
                  actual_outcome TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

# Initialize database
init_db()

# Function to get database connection
def get_db_connection():
    conn = sqlite3.connect('decisions.db')
    conn.row_factory = sqlite3.Row
    return conn

# Route to serve the main page
@app.route('/')
def index():
    return render_template('index.html')

# Route to get all decisions
@app.route('/decisions')
def get_decisions():
    conn = get_db_connection()
    decisions = conn.execute('SELECT * FROM decisions ORDER BY created_at DESC').fetchall()
    conn.close()
    decisions_list = [dict(decision) for decision in decisions]
    return jsonify(decisions_list)

# Route to add a new decision
@app.route('/add_decision', methods=['POST'])
def add_decision():
    data = request.get_json()
    title = data.get('title')
    reasoning = data.get('reasoning')
    expected_outcome = data.get('expected_outcome')
    actual_outcome = data.get('actual_outcome')
    
    if not title:
        return jsonify({'error': 'Title is required'}), 400
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO decisions (title, reasoning, expected_outcome, actual_outcome) VALUES (?, ?, ?, ?)',
              (title, reasoning, expected_outcome, actual_outcome or None))
    decision_id = c.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({'id': decision_id, 'message': 'Decision added successfully'})

# Route to update an outcome
@app.route('/update_outcome/<int:decision_id>', methods=['POST'])
def update_outcome(decision_id):
    data = request.get_json()
    actual_outcome = data.get('actual_outcome')
    
    if not actual_outcome:
        return jsonify({'error': 'Actual outcome is required'}), 400
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE decisions SET actual_outcome = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
              (actual_outcome, decision_id))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Outcome updated successfully'})

# Route to delete a decision
@app.route('/delete_decision/<int:decision_id>', methods=['DELETE'])
def delete_decision(decision_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM decisions WHERE id = ?', (decision_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Decision deleted successfully'})

# Function to call Ollama API with streaming
def call_ollama_api(prompt):
    try:
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                'model': 'gemma3:1b',
                'prompt': prompt,
                'stream': True
            },
            stream=True
        )
        
        if response.status_code == 200:
            # Stream the response
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    try:
                        json_data = json.loads(decoded_line)
                        if 'response' in json_data:
                            yield json_data['response']
                        if json_data.get('done', False):
                            break
                    except json.JSONDecodeError:
                        continue
        else:
            yield f"Error: {response.status_code} - {response.text}"
    except Exception as e:
        yield f"Error connecting to Ollama: {str(e)}"


# Function to stream AI analysis for a single decision
def stream_analysis_for_decision(decision_id):
    conn = get_db_connection()
    decision = conn.execute('SELECT * FROM decisions WHERE id = ?', (decision_id,)).fetchone()
    conn.close()
    
    if not decision:
        yield json.dumps({'error': 'Decision not found'})
        return
    
    decision_dict = dict(decision)
    
    # Create prompt for AI analysis with context injection
    prompt = f"""
    Analyze this decision and provide a concise, well-formatted response with key insights:
    
    CONTEXT - Decision Details:
    - Title: {decision_dict['title']}
    - Reasoning: {decision_dict['reasoning']}
    - Expected Outcome: {decision_dict['expected_outcome']}
    - Actual Outcome: {decision_dict['actual_outcome'] or 'Not recorded yet'}
    
    INSTRUCTIONS:
    1. Provide a brief but comprehensive analysis
    2. Format the response with clear sections
    3. Highlight key points
    4. Be specific and actionable
    5. Structure the response as follows:
       - COMPARISON: Brief comparison of expected vs actual
       - KEY INSIGHTS: Most important findings
       - LESSONS: Key lessons learned
       - RECOMMENDATIONS: Specific suggestions for future
    
    FORMAT RESPONSE IN MARKDOWN STYLE FOR VISUAL CLARITY:
    **Section Title**: Content here
    
    Keep the response concise but insightful.
    """
    
    full_response = ""
    for chunk in call_ollama_api(prompt):
        full_response += chunk
        yield f"data: {json.dumps({'chunk': chunk})}\n\n"
    
    yield f"data: {json.dumps({'complete': True, 'full_response': full_response})}\n\n"
    yield "data: [DONE]\n\n"


# Function to stream AI analysis for all decisions
def stream_analysis_for_all_decisions():
    conn = get_db_connection()
    decisions = conn.execute('SELECT * FROM decisions ORDER BY created_at DESC').fetchall()
    conn.close()
    
    decisions_list = [dict(decision) for decision in decisions]
    
    if not decisions_list:
        yield json.dumps({'error': 'No decisions found'})
        return
    
    # Create prompt for comprehensive analysis with context injection
    prompt = f"""
    Analyze all these decisions and provide a concise, well-formatted comprehensive analysis:
    
    CONTEXT - All Decisions Data:
    {json.dumps(decisions_list, indent=2, default=str)}
    
    INSTRUCTIONS:
    1. Provide a brief but comprehensive analysis
    2. Format the response with clear sections
    3. Highlight key patterns and insights
    4. Be specific and actionable
    5. Structure the response as follows:
       - OVERALL PATTERNS: Key patterns across decisions
       - SUCCESS RATE: Estimated success rate
       - COMMON THEMES: Recurring themes
       - KEY LEARNINGS: Most important insights
       - RECOMMENDATIONS: Specific suggestions for improvement
    
    FORMAT RESPONSE IN MARKDOWN STYLE FOR VISUAL CLARITY:
    **Section Title**: Content here
    
    Keep the response concise but insightful.
    """
    
    full_response = ""
    for chunk in call_ollama_api(prompt):
        full_response += chunk
        yield f"data: {json.dumps({'chunk': chunk})}\n\n"
    
    yield f"data: {json.dumps({'complete': True, 'full_response': full_response, 'decision_count': len(decisions_list)})}\n\n"
    yield "data: [DONE]\n\n"


# Route for AI analysis of a single decision (streaming)
@app.route('/analyze_decision/<int:decision_id>')
def analyze_decision(decision_id):
    return Response(stream_analysis_for_decision(decision_id), mimetype='text/event-stream')

# Route for AI analysis of all decisions (streaming)
@app.route('/analyze_all_decisions')
def analyze_all_decisions():
    return Response(stream_analysis_for_all_decisions(), mimetype='text/event-stream')

# Route to render decision detail page
@app.route('/decision/<int:decision_id>')
def decision_detail(decision_id):
    conn = get_db_connection()
    decision = conn.execute('SELECT * FROM decisions WHERE id = ?', (decision_id,)).fetchone()
    conn.close()
    
    if not decision:
        return jsonify({'error': 'Decision not found'}), 404
    
    return render_template('decision_detail.html', decision=dict(decision))


# Route to get a single decision by ID (for API calls)
@app.route('/decision_data/<int:decision_id>')
def get_decision(decision_id):
    conn = get_db_connection()
    decision = conn.execute('SELECT * FROM decisions WHERE id = ?', (decision_id,)).fetchone()
    conn.close()
    
    if not decision:
        return jsonify({'error': 'Decision not found'}), 404
    
    return jsonify(dict(decision))

if __name__ == '__main__':
    app.run(debug=True)