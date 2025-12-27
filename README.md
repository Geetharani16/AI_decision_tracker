# AI Decision Justification Tracker

A Flask web application that helps users learn from past decisions by analyzing assumptions versus outcomes retrospectively using AI-powered analysis with the Gemma3:1b model.

## Features

- **Decision Logging**: Add decisions with titles, reasoning, and expected outcomes
- **Outcome Tracking**: Record actual outcomes for decisions made later
- **AI Analysis**: Get AI-powered insights comparing expected vs. actual outcomes
- **Retrospective Reasoning**: Focus on analyzing what happened vs. what was expected
- **Historical Analysis**: Analyze all decisions at once for comprehensive insights
- **Lessons Learned**: Generate insights from invalid assumptions and outcomes
- **Future Suggestions**: Recommendations based on past decision patterns
- **Modern UI**: Clean, responsive interface with ChatGPT-like streaming experience
- **Interactive Dashboard**: Individual and comprehensive analysis tabs

## Technology Stack

- **Backend**: Python Flask
- **Database**: SQLite
- **Frontend**: HTML, CSS, JavaScript
- **AI Integration**: Ollama with Gemma3:1b model

## Prerequisites

- Python 3.8+
- Ollama installed and running
- Gemma3:1b model installed in Ollama

## Installation

1. Clone or download the repository
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install and start Ollama:
   - Download from [ollama.com](https://ollama.com)
   - Pull the required model:
   ```bash
   ollama pull gemma3:1b
   ```
4. Start Ollama service (typically runs on `http://localhost:11434`)

## Usage

1. Run the application:
   ```bash
   python app.py
   ```
2. Open your browser and navigate to `http://127.0.0.1:5000`
3. Add decisions using the "Add Decision" form (title, reasoning, expected outcome, and optionally actual outcome)
4. Add outcomes to completed decisions later using the "Add Outcome" button
5. Use "AI Analyze" to get AI-powered insights for individual decisions
6. Use "Analyze All Decisions" to get comprehensive analysis of all decisions

## How It Works

1. **Log Decision**: Enter decision title, reasoning, and expected outcome
2. **Log Actual Outcome Later**: Record what actually happened after the decision was made
3. **AI Compares Expectation vs Reality**: The application sends decision data to Ollama for analysis
4. **Generate Lessons Learned and Future Suggestions**: Receive structured analysis with:
   - **Comparison Analysis**: How actual outcomes compared to expected ones
   - **Invalid Assumptions**: Which assumptions proved incorrect
   - **Lessons Learned**: Key insights from the decision
   - **Future Suggestions**: Recommendations for similar future decisions

## Architecture

- **Frontend**: HTML templates with CSS styling and JavaScript for enhanced UX
- **Backend**: Flask routes handling requests and responses
- **Database**: SQLite for storing decision data
- **AI Integration**: Streaming API calls to local Ollama service

## AI Value

The AI component provides valuable retrospective analysis by:
- Comparing expected vs. actual outcomes to identify gaps
- Identifying invalid assumptions that led to unexpected results
- Generating actionable lessons learned from past decisions
- Providing personalized suggestions for future decision-making
- Analyzing patterns across multiple decisions to improve overall decision quality

## Customization

- Change the AI model by modifying the model name in `app.py`
- Customize the UI by modifying the template in the `templates` directory
- Update prompts in `app.py` to change AI analysis behavior
- Modify the analysis format to focus on different aspects

## Troubleshooting

- Ensure Ollama is running on `http://localhost:11434`
- Verify the gemma3:1b model is available in Ollama
- Check that all Python dependencies are installed
- Look at the console for any error messages when running the app

## Contributing

Feel free to fork this repository and submit pull requests for improvements.

## License

This project is open source and available under the MIT License.