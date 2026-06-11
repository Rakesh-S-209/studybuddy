"""
app/models.py - SQLAlchemy ORM models

Tables:
  User      — registered accounts
  Quiz      — a generated quiz tied to a user
  Question  — one MCQ inside a quiz
  Attempt   — a completed quiz attempt with a score
"""

from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.database import db, login_manager


# ---------------------------------------------------------------------------
# User loader callback required by Flask-Login
# ---------------------------------------------------------------------------
@login_manager.user_loader
def load_user(user_id: str):
    return User.query.get(int(user_id))


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
class User(UserMixin, db.Model):
    """Registered user account."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    quizzes = db.relationship("Quiz", backref="owner", lazy="dynamic", cascade="all, delete-orphan")
    attempts = db.relationship("Attempt", backref="user", lazy="dynamic", cascade="all, delete-orphan")

    # ------------------------------------------------------------------
    # Password helpers — never store plaintext passwords
    # ------------------------------------------------------------------
    def set_password(self, password: str) -> None:
        """Hash and store the password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Return True if the provided password matches the stored hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User {self.username}>"


# ---------------------------------------------------------------------------
# Quiz
# ---------------------------------------------------------------------------
class Quiz(db.Model):
    """A quiz generated from a user's uploaded material."""

    __tablename__ = "quizzes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    # Short summary / first 300 chars of the source text shown on dashboard
    source_summary = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    questions = db.relationship(
        "Question", backref="quiz", lazy="dynamic", cascade="all, delete-orphan"
    )
    attempts = db.relationship(
        "Attempt", backref="quiz", lazy="dynamic", cascade="all, delete-orphan"
    )

    @property
    def question_count(self) -> int:
        return self.questions.count()

    @property
    def attempt_count(self) -> int:
        return self.attempts.count()

    def best_score(self) -> int | None:
        """Return the highest score the owner achieved on this quiz."""
        attempt = (
            self.attempts.filter_by(user_id=self.user_id)
            .order_by(Attempt.score.desc())
            .first()
        )
        return attempt.score if attempt else None

    def __repr__(self) -> str:
        return f"<Quiz {self.id}: {self.title}>"


# ---------------------------------------------------------------------------
# Question
# ---------------------------------------------------------------------------
class Question(db.Model):
    """A single multiple-choice question belonging to a Quiz."""

    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quizzes.id"), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(500), nullable=False)
    option_b = db.Column(db.String(500), nullable=False)
    option_c = db.Column(db.String(500), nullable=False)
    option_d = db.Column(db.String(500), nullable=False)
    correct_answer = db.Column(db.String(1), nullable=False)   # "A" | "B" | "C" | "D"
    explanation = db.Column(db.Text, nullable=True)

    @property
    def options(self) -> dict:
        """Return all options as a labelled dict for easy template iteration."""
        return {
            "A": self.option_a,
            "B": self.option_b,
            "C": self.option_c,
            "D": self.option_d,
        }

    @property
    def correct_text(self) -> str:
        """Return the full text of the correct answer."""
        return self.options.get(self.correct_answer, "")

    def __repr__(self) -> str:
        return f"<Question {self.id} (Quiz {self.quiz_id})>"


# ---------------------------------------------------------------------------
# Attempt
# ---------------------------------------------------------------------------
class Attempt(db.Model):
    """Records a single completed quiz attempt with score."""

    __tablename__ = "attempts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quizzes.id"), nullable=False)
    score = db.Column(db.Integer, nullable=False, default=0)
    total = db.Column(db.Integer, nullable=False, default=10)
    # JSON string: {"<question_id>": "A"|"B"|"C"|"D", ...}
    answers_json = db.Column(db.Text, nullable=True)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @property
    def percentage(self) -> float:
        """Return score as a percentage (0–100)."""
        if self.total == 0:
            return 0.0
        return round((self.score / self.total) * 100, 1)

    @property
    def answers(self) -> dict:
        """Return submitted answers as {question_id (int): letter (str)}."""
        if not self.answers_json:
            return {}
        import json
        try:
            # Keys are stored as strings in JSON; cast back to int
            return {int(k): v for k, v in json.loads(self.answers_json).items()}
        except (ValueError, TypeError):
            return {}

    def __repr__(self) -> str:
        return f"<Attempt {self.id}: {self.score}/{self.total}>"
