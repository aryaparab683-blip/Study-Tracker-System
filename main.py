import os
import secrets

from flask import Flask, flash, redirect, render_template, url_for
from flask_login import LoginManager
from sqlalchemy import event
from sqlalchemy.engine import Engine
from werkzeug.security import generate_password_hash

from models import db, User, Subject, StudySession, Task, Note, Goal, Reminder
from utils import init_csrf, to_local

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"


def _load_secret_key(app):
    """SECRET_KEY from the environment, otherwise a random key persisted in instance/."""
    env_key = os.environ.get("SECRET_KEY")
    if env_key:
        return env_key
    os.makedirs(app.instance_path, exist_ok=True)
    path = os.path.join(app.instance_path, "secret_key")
    if os.path.exists(path):
        with open(path) as fh:
            return fh.read().strip()
    key = secrets.token_hex(32)
    with open(path, "w") as fh:
        fh.write(key)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return key


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Enforce SQLite foreign key constraints on every connection."""
    if type(dbapi_connection).__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = _load_secret_key(app)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///study_tracker.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE") == "1"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024  # reject request bodies over 1 MB

    db.init_app(app)
    login_manager.init_app(app)
    init_csrf(app)
    app.jinja_env.filters["local"] = to_local  # {{ dt|local }} -> user's timezone

    from routes.auth import auth_bp
    from routes.main1 import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    register_error_handlers(app)

    @app.after_request
    def _security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return resp

    with app.app_context():
        db.create_all()
        # The demo account (student@example.com / password) is opt-in only.
        if os.environ.get("STUDY_TRACKER_SEED_DEMO") == "1" and not User.query.first():
            create_sample_data()

    return app


def register_error_handlers(app):
    def render_error(code, title, message):
        return render_template("error.html", code=code, title=title, message=message), code

    @app.errorhandler(400)
    def bad_request(e):
        return render_error(400, "Request couldn't be processed", getattr(e, "description", None) or "Please go back and try again.")

    @app.errorhandler(404)
    def not_found(e):
        return render_error(404, "Page not found", "That page doesn't exist, or it isn't yours to see.")

    @app.errorhandler(413)
    def too_large(e):
        return render_error(413, "Request too large", "That submission is too large. Please shorten it and try again.")

    @app.errorhandler(405)
    def not_allowed(e):
        return render_error(405, "Action not allowed", "That action isn't available this way.")

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return render_error(500, "Something went wrong", "An unexpected error occurred. Your data was not changed.")


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


def create_sample_data():
    sample_user = User(
        name="Study Student",
        email="student@example.com",
        password=generate_password_hash("password", method="pbkdf2:sha256", salt_length=16),
    )
    db.session.add(sample_user)
    db.session.commit()

    subjects = [
        Subject(name="Math", color="#C496A1", user_id=sample_user.id),
        Subject(name="Physics", color="#8E88A3", user_id=sample_user.id),
        Subject(name="Language", color="#919D85", user_id=sample_user.id),
    ]
    db.session.add_all(subjects)
    db.session.commit()

    sessions = [
        StudySession(title="Algebra practice", duration=45, notes="Worked through equations.", subject_id=subjects[0].id, user_id=sample_user.id),
        StudySession(title="Mechanics review", duration=60, notes="Reviewed formulas for motion.", subject_id=subjects[1].id, user_id=sample_user.id),
        StudySession(title="Vocabulary flashcards", duration=30, notes="Added 20 new words.", subject_id=subjects[2].id, user_id=sample_user.id),
    ]
    goals = [
        Goal(title="Finish semester project", progress=40, target=100, user_id=sample_user.id),
        Goal(title="Complete 10 sessions this week", progress=7, target=10, user_id=sample_user.id),
    ]
    tasks = [
        Task(title="Read chapter 5", subject_id=subjects[0].id, user_id=sample_user.id),
        Task(title="Solve practice set", subject_id=subjects[1].id, user_id=sample_user.id),
    ]
    notes = [
        Note(title="Study strategy", content="Mix practice and review sessions for best retention.", user_id=sample_user.id),
    ]
    reminders = [
        Reminder(message="Start your next Pomodoro session", active=True, user_id=sample_user.id),
    ]
    db.session.add_all(sessions + goals + tasks + notes + reminders)
    db.session.commit()


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    # Debug mode exposes the Werkzeug debugger: opt in explicitly with FLASK_DEBUG=1.
    try:
        app.run(debug=os.environ.get("FLASK_DEBUG") == "1", port=port)
    except OSError as e:
        if port == 5000 and getattr(e, "errno", None) == 48:
            print("Port 5000 is already in use (often by macOS AirPlay). Falling back to port 5001...")
            app.run(debug=os.environ.get("FLASK_DEBUG") == "1", port=5001)
        else:
            raise