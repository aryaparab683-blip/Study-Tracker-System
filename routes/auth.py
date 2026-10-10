import time
from collections import defaultdict, deque

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash

from models import db, User
from utils import EMAIL_RE, MIN_PASSWORD_LEN, safe_next_url

auth_bp = Blueprint("auth", __name__, url_prefix="")

# Simple in-memory brute-force throttle (per process). Use Redis/Flask-Limiter when deploying behind several workers.
MAX_FAILURES = 5
WINDOW_SECONDS = 600
_failures = defaultdict(deque)


def _throttle_key(email):
    return (request.remote_addr or "?", email)


def _is_locked(key):
    now = time.time()
    attempts = _failures[key]
    while attempts and now - attempts[0] > WINDOW_SECONDS:
        attempts.popleft()
    return len(attempts) >= MAX_FAILURES


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    email = ""
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        key = _throttle_key(email)
        if _is_locked(key):
            flash("Too many failed attempts. Please wait a few minutes and try again.", "error")
        else:
            user = User.query.filter(func.lower(User.email) == email).first() if email else None
            if user and check_password_hash(user.password, password):
                _failures.pop(key, None)
                login_user(user)
                return redirect(safe_next_url(request.args.get("next")) or url_for("main.dashboard"))
            _failures[key].append(time.time())
            flash("Invalid email or password.", "error")
    return render_template("login.html", email=email)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    form = {"name": "", "email": ""}
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm") or ""
        form = {"name": name, "email": email}

        error = None
        if not name or not email or not password:
            error = "Please fill in all fields."
        elif len(name) > 80:
            error = "Name must be 80 characters or fewer."
        elif len(email) > 120 or not EMAIL_RE.match(email):
            error = "Please enter a valid email address."
        elif len(password) < MIN_PASSWORD_LEN:
            error = f"Password must be at least {MIN_PASSWORD_LEN} characters."
        elif len(password) > 128:
            error = "Password must be 128 characters or fewer."
        elif password != confirm:
            error = "Passwords do not match."
        elif User.query.filter(func.lower(User.email) == email).first():
            error = "An account with that email already exists."

        if error:
            flash(error, "error")
        else:
            user = User(
                name=name,
                email=email,
                password=generate_password_hash(password, method="pbkdf2:sha256", salt_length=16),
            )
            db.session.add(user)
            db.session.commit()
            flash("Account created successfully. Please log in.", "success")
            return redirect(url_for("auth.login"))
    return render_template("register.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))
