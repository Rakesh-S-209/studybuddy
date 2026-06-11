"""
app/database.py - Shared database extension instances

Keeping db and login_manager here (instead of directly in __init__.py)
breaks the circular-import problem: models import db, __init__ imports
models, but db itself lives here and has no app-level imports.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# SQLAlchemy instance — will be bound to the app in create_app()
db = SQLAlchemy()

# Flask-Login instance
login_manager = LoginManager()

# Where unauthenticated users are redirected
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "info"
