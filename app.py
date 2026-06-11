from flask import Flask, render_template, request, jsonify
import requests
import json
import os
from PyPDF2 import PdfReader
from io import BytesIO
import sys
from datetime import datetime
import time

# Create necessary directories
os.makedirs('templates', exist_ok=True)
os.makedirs('static', exist_ok=True)

app = Flask(__name__)

def log(message):
    """Print status messages to console with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] [StudyBuddy] {message}", flush=True)
    sys.stdout.flush()

# Ollama API configuration
OLLAMA_API = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:3b"

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/generate-quiz', methods=['POST'])
def generate_quiz():
    """
    Endpoint to generate quiz from uploaded file or pasted text
    Accepts: PDF, TXT files, or plain text
    """
    start_time = time.time()
    try:
        log("Quiz generation request received")
        text = ""
        
        # Check if file is uploaded
        if 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                log("No file selected")
                return jsonify({"error": "No file selected"}), 400
            
            log(f"Processing file: {file.filename}")
            
            # Extract text from PDF
            if file.filename.endswith('.pdf'):
                try:
                    log("Reading PDF...")
                    pdf_reader = PdfReader(file)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text()
                    log(f"PDF read successfully: {len(text)} characters extracted")
                except Exception as e:
                    log(f"ERROR: Failed to read PDF: {str(e)}")
                    return jsonify({"error": f"Failed to read PDF: {str(e)}"}), 400
            
            # Extract text from TXT
            elif file.filename.endswith('.txt'):
                log("Reading TXT file...")
                text = file.read().decode('utf-8', errors='ignore')
                log(f"TXT read successfully: {len(text)} characters extracted")
            
            else:
                log("ERROR: Unsupported file format")
                return jsonify({"error": "Only PDF and TXT files are supported"}), 400
        
        # Check if text is pasted
        elif 'text' in request.form:
            text = request.form.get('text', '').strip()
            log(f"Text pasted: {len(text)} characters")
        
        else:
            log("ERROR: No file or text provided")
            return jsonify({"error": "No file or text provided"}), 400
        
        # Validate text length
        if not text or len(text) < 50:
            log("ERROR: Text too short (minimum 50 characters required)")
            return jsonify({"error": "Please provide at least 50 characters of text"}), 400
        
        # Limit text to avoid overwhelming the LLM
        original_len = len(text)
        if len(text) > 3000:
            text = text[:3000]
            log(f"Text trimmed: {original_len} -> 3000 characters")
        else:
            log(f"Text length OK: {len(text)} characters")
        
        # Create prompt for Ollama
        log("Creating prompt for AI model...")
        prompt = f"""Generate a quiz from the following notes.
Create exactly 10 multiple choice questions.
Each question must have:
- question
- options array with 4 options
- correct_answer (should be one of the options)

Strict rules:
- Return only valid JSON.
- Do not include markdown, code fences, explanations, or any extra text.
- Use a unique, varied set of 4 answer options for every question.
- Do not repeat the same option pattern across questions.
- Make each set of options plausible and clearly different from the others.

Return ONLY valid JSON in this format, no markdown code blocks:

{{
  "questions": [
    {{
      "question": "...",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "Option A"
    }}
  ]
}}

Notes:
{text}"""
        
        # Call Ollama API
        log("Sending request to Ollama (generating 10 MCQs - this may take 15-30 seconds)...")
        ollama_start = time.time()
        try:
            response = requests.post(
                OLLAMA_API,
                json={
                    "model": MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.7
                },
                timeout=600
            )
            ollama_elapsed = time.time() - ollama_start
            log(f"Response received from Ollama (took {ollama_elapsed:.2f}s)")
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            log("ERROR: Cannot connect to Ollama at http://localhost:11434")
            return jsonify({"error": "Cannot connect to Ollama. Make sure it's running on http://localhost:11434"}), 500
        except requests.exceptions.Timeout:
            log("ERROR: Ollama request timed out after 600 seconds (model may be overwhelmed)")
            return jsonify({"error": "Ollama request timed out - try again or restart ollama serve"}), 500
        
        # Parse Ollama response
        log("Parsing response from Ollama...")
        ollama_response = response.json()
        generated_text = ollama_response.get('response', '')
        log(f"Response length: {len(generated_text)} characters")
        
        # Extract JSON from response
        try:
            log("Extracting JSON from response...")
            # Try to find JSON in the response
            json_start = generated_text.find('{')
            json_end = generated_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                log("ERROR: No JSON found in response")
                return jsonify({"error": "Failed to generate valid quiz"}), 500
            
            json_str = generated_text[json_start:json_end]
            log(f"JSON extracted: {len(json_str)} characters")
            quiz_data = json.loads(json_str)
            log("JSON parsed successfully")
            
            # Validate quiz structure
            if 'questions' not in quiz_data or len(quiz_data['questions']) == 0:
                log("ERROR: No questions found in response")
                return jsonify({"error": "Failed to generate questions"}), 500
            
            num_questions = len(quiz_data['questions'])
            log(f"Validating {num_questions} questions...")
            
            # Log each question
            for i, q in enumerate(quiz_data['questions'], 1):
                if 'question' in q and 'options' in q and 'correct_answer' in q:
                    log(f"  Question {i}: '{q['question'][:50]}...' ({len(q['options'])} options)")
                else:
                    log(f"  Question {i}: INVALID structure")
            
            log(f"SUCCESS: Quiz generated with {num_questions} questions")
            total_elapsed = time.time() - start_time
            log(f"TOTAL TIME: {total_elapsed:.2f}s")
            return jsonify(quiz_data)
        
        except json.JSONDecodeError as e:
            log(f"ERROR: Failed to parse JSON: {str(e)}")
            return jsonify({"error": "Failed to parse generated quiz"}), 500
    
    except Exception as e:
        elapsed = time.time() - start_time
        log(f"ERROR: Server error: {str(e)} (elapsed time: {elapsed:.2f}s)")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

if __name__ == '__main__':
    log("Starting StudyBuddy application")
    log(f"Ollama API endpoint: {OLLAMA_API}")
    log(f"Model: {MODEL}")
    log("Server running at http://localhost:5000")
    app.run(debug=True, port=5000)
