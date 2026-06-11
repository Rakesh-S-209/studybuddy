"""
wsgi.py - Production entry point

Platforms like Render, Railway, and Gunicorn discover the app via this file.

  gunicorn wsgi:app
  or
  gunicorn "wsgi:app"
"""

import os
from app import create_app

config_name = os.environ.get("FLASK_ENV", "production")
app = create_app(config_name)

if __name__ == "__main__":
    # Local dev fallback: python wsgi.py
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
