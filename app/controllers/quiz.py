"""
app/controllers/quiz.py - Quiz generation, taking, and grading blueprint

Routes:
  GET/POST  /quiz/new            — upload material and trigger generation
  GET       /quiz/<id>/take      — interactive quiz page
  POST      /quiz/<id>/submit    — grade a submission, save attempt
  GET       /quiz/<id>/review    — post-attempt review / score summary
  GET       /quiz/<id>/delete    — delete a quiz (owner only)

  POST      /api/generate-quiz   — AJAX endpoint called from the upload page
"""

import json
import logging
import time
from io import BytesIO

import requests as http_requests
from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from PyPDF2 import PdfReader

from app.database import db
from app.models import Attempt, Question, Quiz

quiz_bp = Blueprint("quiz", __name__, url_prefix="/quiz")
logger = logging.getLogger(__name__)


# ===========================================================================
# LLM helper
# ===========================================================================

def _call_llm(text: str) -> list[dict]:
    """
    Send text to the configured cloud LLM and return a list of question dicts.

    Each dict in the returned list has the shape:
      {
        "question": str,
        "options": {"A": str, "B": str, "C": str, "D": str},
        "correct_answer": "A"|"B"|"C"|"D",
        "explanation": str          # optional
      }

    Raises:
      RuntimeError  — if the API call fails or the response can't be parsed.
    """
    api_key = current_app.config["LLM_API_KEY"]
    base_url = current_app.config["LLM_BASE_URL"]
    model = current_app.config["LLM_MODEL_NAME"]

    if not api_key:
        raise RuntimeError(
            "LLM_API_KEY is not set. Add it to your .env file."
        )

    # Trim source text to keep token usage manageable
    source = text[:4000] if len(text) > 4000 else text

    system_prompt = (
        "You are a quiz generation assistant. "
        "Always respond with ONLY a valid JSON array — no prose, no markdown fences."
    )

    user_prompt = f"""Generate exactly 10 multiple-choice questions from the notes below.

Return a JSON array with exactly 10 objects. Each object must follow this exact schema:
{{
  "question": "<question text>",
  "options": {{
    "A": "<option A text>",
    "B": "<option B text>",
    "C": "<option C text>",
    "D": "<option D text>"
  }},
  "correct_answer": "<A|B|C|D>",
  "explanation": "<one-sentence explanation of why the answer is correct>"
}}

Rules:
- Return ONLY the JSON array. No extra text.
- All four options must be plausible and distinct.
- correct_answer must be exactly one of: A, B, C, D.

Notes:
{source}"""

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 3000,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        # OpenRouter requires these; harmless for other providers
        "HTTP-Referer": "http://localhost:5000",
        "X-Title": "StudyBuddy",
    }

    try:
        response = http_requests.post(
            f"{base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=120,
        )
        response.raise_for_status()
    except http_requests.exceptions.ConnectionError as exc:
        raise RuntimeError(f"Cannot reach LLM endpoint: {base_url}") from exc
    except http_requests.exceptions.Timeout:
        raise RuntimeError("LLM request timed out after 120 seconds.")
    except http_requests.exceptions.HTTPError as exc:
        raise RuntimeError(
            f"LLM API returned an error: {exc.response.status_code} — "
            f"{exc.response.text[:300]}"
        ) from exc

    raw = response.json()["choices"][0]["message"]["content"].strip()

    # Strip accidental markdown fences if the model includes them
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        questions = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("LLM returned invalid JSON: %s", raw[:500])
        raise RuntimeError("The AI returned an invalid response. Please try again.") from exc

    if not isinstance(questions, list) or len(questions) == 0:
        raise RuntimeError("The AI response didn't contain any questions.")

    return questions


# ===========================================================================
# Text extraction helpers
# ===========================================================================

def _extract_text_from_file(file) -> str:
    """
    Extract plain text from an uploaded PDF or TXT file object.

    Args:
        file: Werkzeug FileStorage object.

    Returns:
        Extracted text string.

    Raises:
        ValueError  — unsupported format or extraction failure.
    """
    filename = file.filename.lower()

    if filename.endswith(".pdf"):
        try:
            reader = PdfReader(BytesIO(file.read()))
            return "\n".join(
                page.extract_text() or "" for page in reader.pages
            )
        except Exception as exc:
            raise ValueError(f"Could not read PDF: {exc}") from exc

    if filename.endswith(".txt"):
        return file.read().decode("utf-8", errors="ignore")

    raise ValueError("Only PDF and TXT files are supported.")


# ===========================================================================
# Routes
# ===========================================================================

@quiz_bp.route("/new", methods=["GET"])
@login_required
def new_quiz():
    """Render the quiz creation / upload page."""
    return render_template("new_quiz.html")


@quiz_bp.route("/generate", methods=["POST"])
@login_required
def generate():
    """
    AJAX endpoint — receives form data, calls the LLM, saves the quiz,
    and returns JSON with the new quiz ID.
    """
    start = time.time()

    # --- extract text ---
    text = ""
    if "file" in request.files and request.files["file"].filename:
        try:
            text = _extract_text_from_file(request.files["file"])
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
    elif request.form.get("text", "").strip():
        text = request.form["text"].strip()
    else:
        return jsonify({"error": "Please upload a file or paste study notes."}), 400

    if len(text) < 50:
        return jsonify({"error": "Please provide at least 50 characters of text."}), 400

    # --- call LLM ---
    try:
        raw_questions = _call_llm(text)
    except RuntimeError as exc:
        logger.exception("LLM call failed")
        return jsonify({"error": str(exc)}), 500

    # --- build a title from the first sentence / 60 chars ---
    title = text.strip().split("\n")[0][:60].strip() or "Untitled Quiz"

    # --- persist quiz + questions ---
    quiz = Quiz(
        user_id=current_user.id,
        title=title,
        source_summary=text[:300],
    )
    db.session.add(quiz)
    db.session.flush()  # get quiz.id before committing

    for item in raw_questions:
        options = item.get("options", {})
        # Accept both dict-style {"A":...} and list-style ["opt1", ...]
        if isinstance(options, list):
            opt_map = {
                "A": options[0] if len(options) > 0 else "",
                "B": options[1] if len(options) > 1 else "",
                "C": options[2] if len(options) > 2 else "",
                "D": options[3] if len(options) > 3 else "",
            }
        else:
            opt_map = {k: options.get(k, "") for k in ("A", "B", "C", "D")}

        # Normalise correct_answer to uppercase single letter
        correct = str(item.get("correct_answer", "A")).strip().upper()[:1]
        if correct not in ("A", "B", "C", "D"):
            correct = "A"

        question = Question(
            quiz_id=quiz.id,
            question_text=item.get("question", ""),
            option_a=opt_map["A"],
            option_b=opt_map["B"],
            option_c=opt_map["C"],
            option_d=opt_map["D"],
            correct_answer=correct,
            explanation=item.get("explanation", ""),
        )
        db.session.add(question)

    db.session.commit()

    elapsed = round(time.time() - start, 2)
    logger.info("Quiz %d generated in %ss", quiz.id, elapsed)

    return jsonify({"quiz_id": quiz.id, "elapsed": elapsed})


@quiz_bp.route("/<int:quiz_id>/take", methods=["GET"])
@login_required
def take_quiz(quiz_id: int):
    """Interactive quiz page."""
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = quiz.questions.all()
    return render_template("view_quiz.html", quiz=quiz, questions=questions)


@quiz_bp.route("/<int:quiz_id>/submit", methods=["POST"])
@login_required
def submit_quiz(quiz_id: int):
    """
    Grade a submitted quiz.

    Expects form fields: answer_<question_id> = "A"|"B"|"C"|"D"
    """
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = quiz.questions.all()

    score = 0
    answers: dict[int, str] = {}

    for q in questions:
        key = f"answer_{q.id}"
        chosen = request.form.get(key, "").strip().upper()[:1]
        answers[q.id] = chosen
        if chosen == q.correct_answer:
            score += 1

    # Save attempt
    attempt = Attempt(
        user_id=current_user.id,
        quiz_id=quiz.id,
        score=score,
        total=len(questions),
    )
    db.session.add(attempt)
    db.session.commit()

    return redirect(
        url_for("quiz.review_quiz", quiz_id=quiz.id, attempt_id=attempt.id)
    )


@quiz_bp.route("/<int:quiz_id>/review/<int:attempt_id>", methods=["GET"])
@login_required
def review_quiz(quiz_id: int, attempt_id: int):
    """Post-attempt review: score summary and per-question analysis."""
    quiz = Quiz.query.get_or_404(quiz_id)
    attempt = Attempt.query.get_or_404(attempt_id)

    # Security: only the attempt owner can view the review
    if attempt.user_id != current_user.id:
        abort(403)

    questions = quiz.questions.all()

    return render_template(
        "review.html",
        quiz=quiz,
        attempt=attempt,
        questions=questions,
    )


@quiz_bp.route("/<int:quiz_id>/delete", methods=["POST"])
@login_required
def delete_quiz(quiz_id: int):
    """Delete a quiz (only the owner can do this)."""
    quiz = Quiz.query.get_or_404(quiz_id)

    if quiz.user_id != current_user.id:
        abort(403)

    db.session.delete(quiz)
    db.session.commit()
    flash("Quiz deleted.", "info")
    return redirect(url_for("main.dashboard"))
