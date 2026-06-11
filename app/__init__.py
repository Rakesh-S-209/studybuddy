"""
app/__init__.py - Application factory

Using the factory pattern keeps the app fully configurable and testable
without module-level side effects.
"""

from flask import Flask

from app.database import db, login_manager
from config import config_map


def create_app(config_name: str = "development") -> Flask:
    """
    Create and configure the Flask application.

    Args:
        config_name: One of 'development', 'production', 'testing'.

    Returns:
        Configured Flask app instance.
    """
    import os
    base = os.path.dirname(os.path.abspath(__file__))
    app = Flask(
        __name__,
        template_folder=os.path.join(base, "templates"),
        static_folder=os.path.join(base, "static"),
    )

    # ------------------------------------------------------------------
    # Load configuration
    # ------------------------------------------------------------------
    cfg = config_map.get(config_name)
    if cfg is None:
        raise ValueError(
            f"Unknown config '{config_name}'. "
            f"Valid options: {list(config_map.keys())}"
        )
    app.config.from_object(cfg)

    # ------------------------------------------------------------------
    # Initialise extensions
    # ------------------------------------------------------------------
    db.init_app(app)
    login_manager.init_app(app)

    # ------------------------------------------------------------------
    # Register blueprints
    # ------------------------------------------------------------------
    from app.controllers.auth import auth_bp
    from app.controllers.main import main_bp
    from app.controllers.quiz import quiz_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(quiz_bp)

    # ------------------------------------------------------------------
    # Create database tables if they don't exist yet
    # ------------------------------------------------------------------
    with app.app_context():
        db.create_all()

    return app
