"""
app/controllers/auth.py - Authentication blueprint

Routes:
  GET/POST  /register   — create a new account
  GET/POST  /login      — log in
  GET       /logout     — log out
"""

import re
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from app.database import db
from app.models import User

auth_bp = Blueprint("auth", __name__)

# Simple email regex for basic server-side validation
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        # --- validation ---
        error = None
        if not username or len(username) < 3:
            error = "Username must be at least 3 characters."
        elif not _EMAIL_RE.match(email):
            error = "Please enter a valid email address."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        elif password != confirm:
            error = "Passwords do not match."
        elif User.query.filter_by(username=username).first():
            error = "That username is already taken."
        elif User.query.filter_by(email=email).first():
            error = "An account with that email already exists."

        if error:
            flash(error, "danger")
            return render_template("register.html")

        # --- create user ---
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash("Account created! Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()  # email or username
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        # Look up by email first, then by username
        user = User.query.filter_by(email=identifier.lower()).first()
        if user is None:
            user = User.query.filter_by(username=identifier).first()

        if user is None or not user.check_password(password):
            flash("Invalid credentials. Please try again.", "danger")
            return render_template("login.html")

        login_user(user, remember=remember)
        # Redirect to the page the user was trying to reach (or dashboard)
        next_page = request.args.get("next")
        return redirect(next_page or url_for("main.dashboard"))

    return render_template("login.html")


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------
@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))
