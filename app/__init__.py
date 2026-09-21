import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import config_by_name

# Initialize Flask extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, default_limits=["300 per day", "100 per hour"])


def create_app(config_name=None):
    """Application factory for the Personal Finance Advisor Bot."""
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)
    config_obj = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(config_obj)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # Flask-Login configuration
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"

    # Context processors (inject current currency symbol and profile helpers)
    @app.context_processor
    def inject_context():
        from flask_login import current_user
        currency_map = {
            "INR": "₹",
            "USD": "$",
            "EUR": "€",
            "GBP": "£"
        }
        if current_user.is_authenticated:
            currency_symbol = currency_map.get(current_user.currency, "₹")
            return {
                "currency_symbol": currency_symbol,
                "current_currency": current_user.currency,
                "user_profile_type": current_user.profile_type,
            }
        return {
            "currency_symbol": "₹",
            "current_currency": "INR",
            "user_profile_type": "salaried",
        }

    # Register Blueprints
    from app.auth.routes import auth_bp
    from app.tracking.routes import tracking_bp
    from app.budget.routes import budget_bp
    from app.insights.routes import insights_bp
    from app.reports.routes import reports_bp
    from app.api.routes import api_bp
    from app.dashboard.routes import dashboard_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(tracking_bp)
    app.register_blueprint(budget_bp)
    app.register_blueprint(insights_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(dashboard_bp)

    # Register error handlers
    register_error_handlers(app)

    return app


def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request_error(error):
        return render_template("errors/400.html", error=error), 400

    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template("errors/403.html", error=error), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template("errors/404.html", error=error), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template("errors/500.html", error=error), 500
