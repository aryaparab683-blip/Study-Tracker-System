"""Shared helpers: CSRF protection, input validation, streak calculation."""
import re
import secrets
from datetime import timedelta

from flask import abort, request, session
from flask_login import current_user

from models import Subject, StudySession, utcnow

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

MAX_DURATION_MIN = 24 * 60
MAX_GOAL_TARGET = 1_000_000
MIN_PASSWORD_LEN = 8


# ---------------------------------------------------------------- CSRF
def init_csrf(app):
    """Minimal synchroniser-token CSRF protection for every state-changing request."""

    def csrf_token():
        if "_csrf" not in session:
            session["_csrf"] = secrets.token_hex(16)
        return session["_csrf"]

    @app.before_request
    def _check_csrf():
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            expected = session.get("_csrf")
            sent = request.form.get("csrf_token") or request.headers.get("X-CSRFToken")
            if not expected or not sent or not secrets.compare_digest(expected, sent):
                abort(400, description="Your form expired or was invalid. Please go back, refresh the page and try again.")

    @app.context_processor
    def _inject_csrf():
        return {"csrf_token": csrf_token}


# ---------------------------------------------------------- validation
def form_text(name, max_len, label=None):
    """Return (value, error). Strips whitespace; rejects empty and over-long values."""
    label = label or name.capitalize()
    value = (request.form.get(name) or "").strip()
    if not value:
        return None, f"{label} is required."
    if len(value) > max_len:
        return None, f"{label} must be {max_len} characters or fewer."
    return value, None


def form_int(name, label, minimum, maximum, required=True):
    """Return (value, error) for an integer form field within [minimum, maximum]."""
    raw = (request.form.get(name) or "").strip()
    if raw == "":
        return (None, f"{label} is required.") if required else (None, None)
    try:
        value = int(raw)
    except ValueError:
        return None, f"{label} must be a whole number."
    if value < minimum or value > maximum:
        return None, f"{label} must be between {minimum:,} and {maximum:,}."
    return value, None


def owned_subject_id(field="subject_id"):
    """Return (subject_id | None, error). Only subjects owned by the current user are accepted."""
    raw = (request.form.get(field) or "").strip()
    if not raw:
        return None, None
    if not raw.isdigit():
        return None, "Selected subject is not valid."
    subject = Subject.query.filter_by(id=int(raw), user_id=current_user.id).first()
    if not subject:
        return None, "Selected subject was not found."
    return subject.id, None


def valid_color(value):
    return bool(value and COLOR_RE.match(value))


def subject_name_taken(name, exclude_id=None):
    from sqlalchemy import func
    q = Subject.query.filter(Subject.user_id == current_user.id, func.lower(Subject.name) == name.lower())
    if exclude_id:
        q = q.filter(Subject.id != exclude_id)
    return q.first() is not None


def safe_next_url(target):
    """Only allow same-site relative redirects (prevents open redirects)."""
    if target and target.startswith("/") and not target.startswith("//") and "\\" not in target:
        return target
    return None


# -------------------------------------------------------------- streak
def compute_streak(user_id):
    """Consecutive days (ending today or yesterday) with at least one logged session."""
    days = {
        row[0].date()
        for row in StudySession.query.with_entities(StudySession.created_at).filter_by(user_id=user_id)
    }
    if not days:
        return 0
    today = utcnow().date()
    cursor = today if today in days else today - timedelta(days=1)
    streak = 0
    while cursor in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak
