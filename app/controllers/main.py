"""
app/controllers/main.py - Main / public pages blueprint

Routes:
  GET  /            — public landing page
  GET  /dashboard   — authenticated user dashboard
"""

from flask import Blueprint, render_template
from flask_login import login_required, current_user
from sqlalchemy import func

from app.models import Quiz, Attempt

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Public landing page."""
    return render_template("index.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    """
    User dashboard.

    Aggregates:
      - Total quizzes created by the user
      - Total attempts (across all quizzes)
      - Average score percentage
      - List of quizzes with latest attempt data
    """
    # All quizzes owned by the current user, newest first
    quizzes = (
        Quiz.query.filter_by(user_id=current_user.id)
        .order_by(Quiz.created_at.desc())
        .all()
    )

    # Total attempts made by the current user
    total_attempts = Attempt.query.filter_by(user_id=current_user.id).count()

    # Average score percentage across all attempts
    avg_result = (
        Attempt.query.with_entities(
            func.avg(Attempt.score * 100.0 / Attempt.total)
        )
        .filter_by(user_id=current_user.id)
        .scalar()
    )
    avg_score = round(avg_result, 1) if avg_result is not None else None

    # Build per-quiz summary: latest attempt + best attempt
    quiz_data = []
    for quiz in quizzes:
        latest = (
            Attempt.query.filter_by(user_id=current_user.id, quiz_id=quiz.id)
            .order_by(Attempt.completed_at.desc())
            .first()
        )
        best = (
            Attempt.query.filter_by(user_id=current_user.id, quiz_id=quiz.id)
            .order_by(Attempt.score.desc())
            .first()
        )
        quiz_data.append(
            {
                "quiz": quiz,
                "latest_attempt": latest,
                "best_attempt": best,
            }
        )

    stats = {
        "total_quizzes": len(quizzes),
        "total_attempts": total_attempts,
        "avg_score": avg_score,
    }

    return render_template("dashboard.html", quiz_data=quiz_data, stats=stats)
