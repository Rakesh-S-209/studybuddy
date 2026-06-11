# StudyBuddy — AI-Powered Quiz Generator

A production-ready Flask web app that turns your study notes into personalised multiple-choice quizzes using a cloud LLM. Built with MVC architecture, user authentication, and a full progress dashboard.

---

## Features

- **User accounts** — Signup, login, logout with bcrypt-hashed passwords
- **AI quiz generation** — Upload a PDF/TXT or paste text; get 10 MCQs with explanations in seconds
- **Dashboard** — View all your quizzes, attempt history, average score, and best scores
- **Retake quizzes** — Every saved quiz can be retaken as many times as you like
- **Cloud-ready** — Deploys to Render, Railway, or any platform supporting Gunicorn + Postgres

---

## Tech Stack

| Layer      | Technology                                      |
|------------|-------------------------------------------------|
| Backend    | Python 3.10+, Flask 3, Flask-SQLAlchemy, Flask-Login |
| Database   | SQLite (dev) / PostgreSQL (prod)                |
| AI         | Any OpenAI-compatible endpoint (Groq, Together AI, OpenAI) |
| Frontend   | Jinja2 templates, vanilla HTML/CSS/JS           |
| Server     | Gunicorn (production)                           |

---

## Project Structure

```
StudyBuddy/
├── app/
│   ├── __init__.py          # App factory
│   ├── database.py          # db + login_manager instances
│   ├── models.py            # User, Quiz, Question, Attempt
│   ├── controllers/
│   │   ├── auth.py          # /login  /register  /logout
│   │   ├── main.py          # /  /dashboard
│   │   └── quiz.py          # /quiz/new  /quiz/<id>/take  /quiz/<id>/submit …
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html       # Public landing page
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── dashboard.html
│   │   ├── new_quiz.html
│   │   ├── view_quiz.html
│   │   └── review.html
│   └── static/
│       ├── css/style.css
│       └── js/quiz.js
├── config.py                # Config classes (dev / prod / test)
├── wsgi.py                  # Gunicorn / production entry point
├── requirements.txt
├── .env.example             # Environment variable template
└── README.md
```

---

## Setup (Local Development)

### 1. Clone & create a virtual environment

```bash
git clone <repo-url>
cd StudyBuddy
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
copy .env.example .env        # Windows
# cp .env.example .env        # macOS / Linux
```

Edit `.env` and fill in at minimum:

```env
SECRET_KEY=your-random-secret-key
LLM_API_KEY=gsk_...           # Your Groq (or OpenAI) API key
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL_NAME=llama3-8b-8192
```

Get a free Groq key at https://console.groq.com

### 4. Run

```bash
python wsgi.py
```

Open **http://localhost:5000** in your browser.

---

## Deployment (Render / Railway)

1. Push to GitHub
2. Create a new **Web Service** pointing to your repo
3. Set **Build command**: `pip install -r requirements.txt`
4. Set **Start command**: `gunicorn wsgi:app`
5. Add all environment variables from `.env.example` in the platform dashboard
6. For production, set `DATABASE_URL` to a PostgreSQL connection string

---

## Environment Variables Reference

| Variable         | Required | Default                              | Description                         |
|------------------|----------|--------------------------------------|-------------------------------------|
| `SECRET_KEY`     | Yes      | `change-me-in-production`            | Flask session signing key           |
| `DATABASE_URL`   | No       | `sqlite:///studybuddy.db`            | SQLAlchemy connection string        |
| `LLM_API_KEY`    | Yes      | —                                    | API key for your LLM provider       |
| `LLM_BASE_URL`   | No       | `https://api.groq.com/openai/v1`     | OpenAI-compatible base URL          |
| `LLM_MODEL_NAME` | No       | `llama3-8b-8192`                     | Model to use for quiz generation    |
| `FLASK_ENV`      | No       | `production`                         | `development` or `production`       |
