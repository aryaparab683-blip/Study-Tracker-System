from datetime import datetime, time, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy import func

from models import db, Subject, StudySession, Task, Note, Goal, Reminder, utcnow
from utils import (
    MAX_DURATION_MIN, MAX_GOAL_TARGET, compute_streak, form_int, form_text,
    local_day_start_utc, local_noon_utc, local_today, owned_subject_id,
    subject_name_taken, to_local, tz_known, valid_color,
)

main_bp = Blueprint("main", __name__, url_prefix="")


def parse_session_datetime(existing=None):
    """Optional 'date' field lets users log sessions for a past day. Returns (datetime, error)."""
    raw = (request.form.get("date") or "").strip()
    if not raw:
        return (existing or utcnow()), None
    try:
        chosen = datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None, "Date is not valid."
    today = local_today()
    slack = timedelta(days=0 if tz_known() else 1)  # unknown timezone: allow users ahead of UTC
    if chosen > today + slack:
        return None, "Date can't be in the future."
    if chosen.year < 2000:
        return None, "Date is too far in the past."
    if existing and to_local(existing).date() == chosen:
        return existing, None
    if chosen >= today:
        return utcnow(), None
    return local_noon_utc(chosen), None


# ------------------------------------------------------------------ landing & dashboard
@main_bp.route("/")
def index():
    if not current_user.is_authenticated:
        return render_template("landing.html")
    return dashboard_view()


@main_bp.route("/landing")
def landing():
    return render_template("landing.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    return dashboard_view()


def dashboard_view():
    uid = current_user.id
    subjects = Subject.query.filter_by(user_id=uid).all()
    recent_sessions = StudySession.query.filter_by(user_id=uid).order_by(StudySession.created_at.desc()).limit(5).all()
    notes = Note.query.filter_by(user_id=uid).order_by(Note.created_at.desc()).limit(4).all()
    goals = Goal.query.filter_by(user_id=uid).all()
    reminders = Reminder.query.filter_by(user_id=uid, active=True).all()

    today = local_today()
    sunday = today - timedelta(days=(today.weekday() + 1) % 7)
    week_minutes = (
        db.session.query(func.coalesce(func.sum(StudySession.duration), 0))
        .filter(StudySession.user_id == uid, StudySession.created_at >= local_day_start_utc(sunday))
        .scalar()
    )
    open_tasks_q = Task.query.filter_by(user_id=uid, completed=False)
    open_task_count = open_tasks_q.count()
    open_tasks = open_tasks_q.order_by(Task.created_at.desc()).limit(5).all()

    total_sessions = StudySession.query.filter_by(user_id=uid).count()
    total_time = db.session.query(func.coalesce(func.sum(StudySession.duration), 0)).filter(StudySession.user_id == uid).scalar()

    counts = dict(
        db.session.query(StudySession.subject_id, func.count(StudySession.id))
        .filter(StudySession.user_id == uid)
        .group_by(StudySession.subject_id)
        .all()
    )
    subject_breakdown = [
        {"name": s.name, "count": counts.get(s.id, 0), "color": s.color or "#6366f1"}
        for s in subjects if counts.get(s.id, 0) > 0
    ]
    if counts.get(None, 0) > 0:
        subject_breakdown.append({"name": "General", "count": counts[None], "color": "#94a3b8"})

    # --- 16-Week Heatmap grid (starts on a Sunday) and per-day totals, bucketed by the user's local day ---
    total_heatmap_days = 16 * 7  # 112 days
    raw_start = today - timedelta(days=total_heatmap_days - 1)
    heatmap_grid_start = raw_start - timedelta(days=(raw_start.weekday() + 1) % 7)

    rows = (
        StudySession.query.with_entities(StudySession.created_at, StudySession.duration)
        .filter(StudySession.user_id == uid, StudySession.created_at >= local_day_start_utc(heatmap_grid_start))
        .all()
    )
    daily_stats = {}
    for created_at, duration in rows:
        ds = to_local(created_at).date().isoformat()
        entry = daily_stats.setdefault(ds, {"minutes": 0, "count": 0})
        entry["minutes"] += duration or 0
        entry["count"] += 1

    # --- 7-Day Bar Chart Data (past 7 days ending today) ---
    seven_days = []
    seven_day_total = 0
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        d_mins = daily_stats.get(d.isoformat(), {"minutes": 0})["minutes"]
        seven_day_total += d_mins
        seven_days.append({
            "date": d.isoformat(),
            "label": d.strftime("%a"),
            "full_date": d.strftime("%b %d"),
            "minutes": int(d_mins),
            "is_today": d == today,
        })
    seven_day_avg = round(seven_day_total / 7, 1)

    heatmap_weeks = []
    cursor = heatmap_grid_start
    total_active_days = 0
    heatmap_total_minutes = 0

    while cursor <= today:
        week = []
        for _ in range(7):
            ds = cursor.isoformat()
            data = daily_stats.get(ds, {"minutes": 0, "count": 0})
            m = data["minutes"]
            c = data["count"]
            if m > 0:
                total_active_days += 1
                heatmap_total_minutes += m

            if m == 0:
                level = 0
            elif m <= 30:
                level = 1
            elif m <= 60:
                level = 2
            elif m <= 120:
                level = 3
            else:
                level = 4

            week.append({
                "date": ds,
                "label": cursor.strftime("%b %d"),
                "day_name": cursor.strftime("%a"),
                "minutes": m,
                "count": c,
                "level": level,
                "is_today": cursor == today,
                "future": cursor > today,
            })
            cursor += timedelta(days=1)
        heatmap_weeks.append(week)

    return render_template(
        "dashboard.html",
        subjects=subjects,
        sessions=recent_sessions,
        notes=notes,
        goals=goals,
        reminders=reminders,
        total_sessions=total_sessions,
        total_time=total_time,
        week_minutes=week_minutes,
        open_tasks=open_tasks,
        open_task_count=open_task_count,
        streak=compute_streak(uid),
        subject_breakdown=subject_breakdown,
        seven_days=seven_days,
        seven_day_total=seven_day_total,
        seven_day_avg=seven_day_avg,
        heatmap_weeks=heatmap_weeks,
        total_active_days=total_active_days,
        heatmap_total_minutes=heatmap_total_minutes,
    )


# ------------------------------------------------------------------- sessions
@main_bp.route("/sessions", methods=["GET", "POST"])
@login_required
def sessions():
    subjects = Subject.query.filter_by(user_id=current_user.id).all()
    form = {}
    if request.method == "POST":
        form = request.form
        title, e1 = form_text("title", 120, "Session title")
        duration, e2 = form_int("duration", "Duration", 1, MAX_DURATION_MIN)
        subject_id, e3 = owned_subject_id()
        when, e4 = parse_session_datetime()
        notes = (request.form.get("notes") or "").strip()
        error = e1 or e2 or e3 or e4 or (None if len(notes) <= 5000 else "Notes must be 5,000 characters or fewer.")
        if error:
            flash(error, "error")
        else:
            db.session.add(StudySession(
                title=title, duration=duration, notes=notes, subject_id=subject_id,
                created_at=when, user_id=current_user.id,
            ))
            db.session.commit()
            flash("Study session logged.", "success")
            return redirect(url_for("main.sessions"))

    all_sessions = StudySession.query.filter_by(user_id=current_user.id).order_by(StudySession.created_at.desc()).all()
    return render_template("sessions.html", sessions=all_sessions, subjects=subjects, form=form, today=local_today().isoformat())


@main_bp.route("/sessions/edit/<int:session_id>", methods=["GET", "POST"])
@login_required
def edit_session(session_id):
    study = StudySession.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
    subjects = Subject.query.filter_by(user_id=current_user.id).all()
    if request.method == "POST":
        title, e1 = form_text("title", 120, "Session title")
        duration, e2 = form_int("duration", "Duration", 1, MAX_DURATION_MIN)
        subject_id, e3 = owned_subject_id()
        when, e4 = parse_session_datetime(existing=study.created_at)
        notes = (request.form.get("notes") or "").strip()
        error = e1 or e2 or e3 or e4 or (None if len(notes) <= 5000 else "Notes must be 5,000 characters or fewer.")
        if error:
            flash(error, "error")
        else:
            study.title, study.duration, study.subject_id = title, duration, subject_id
            study.notes, study.created_at = notes, when
            db.session.commit()
            flash("Study session updated.", "success")
            return redirect(url_for("main.sessions"))
    return render_template("edit_session.html", session=study, subjects=subjects, today=local_today().isoformat())


@main_bp.route("/sessions/delete/<int:session_id>", methods=["POST"])
@login_required
def delete_session(session_id):
    study = StudySession.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
    db.session.delete(study)
    db.session.commit()
    flash("Study session deleted.", "success")
    return redirect(url_for("main.sessions"))


# ------------------------------------------------------------------- subjects
@main_bp.route("/subjects", methods=["GET", "POST"])
@login_required
def subjects():
    if request.method == "POST":
        name, error = form_text("name", 80, "Subject name")
        color = request.form.get("color") or "#6366f1"
        if not error and not valid_color(color):
            error = "Please choose a valid color."
        if not error and subject_name_taken(name):
            error = f"You already have a subject named \"{name}\"."
        if error:
            flash(error, "error")
        else:
            db.session.add(Subject(name=name, color=color, user_id=current_user.id))
            db.session.commit()
            flash("Subject saved.", "success")
            return redirect(url_for("main.subjects"))
    items = Subject.query.filter_by(user_id=current_user.id).all()
    return render_template("subjects.html", subjects=items)


@main_bp.route("/subjects/edit/<int:subject_id>", methods=["POST"])
@login_required
def edit_subject(subject_id):
    subject = Subject.query.filter_by(id=subject_id, user_id=current_user.id).first_or_404()
    name, error = form_text("name", 80, "Subject name")
    color = request.form.get("color") or subject.color
    if not error and not valid_color(color):
        error = "Please choose a valid color."
    if not error and subject_name_taken(name, exclude_id=subject.id):
        error = f"You already have a subject named \"{name}\"."
    if error:
        flash(error, "error")
    else:
        subject.name, subject.color = name, color
        db.session.commit()
        flash("Subject updated.", "success")
    return redirect(url_for("main.subjects"))


@main_bp.route("/subjects/delete/<int:subject_id>", methods=["POST"])
@login_required
def delete_subject(subject_id):
    subject = Subject.query.filter_by(id=subject_id, user_id=current_user.id).first_or_404()
    affected = len(subject.sessions) + len(subject.tasks)
    db.session.delete(subject)
    db.session.commit()
    if affected:
        flash(f"Subject deleted. {affected} linked session(s)/task(s) are now unassigned.", "success")
    else:
        flash("Subject deleted.", "success")
    return redirect(url_for("main.subjects"))


# ---------------------------------------------------------------------- tasks
@main_bp.route("/tasks", methods=["GET", "POST"])
@login_required
def tasks():
    subjects = Subject.query.filter_by(user_id=current_user.id).all()
    if request.method == "POST":
        title, e1 = form_text("title", 120, "Task title")
        subject_id, e2 = owned_subject_id()
        error = e1 or e2
        if error:
            flash(error, "error")
        else:
            db.session.add(Task(title=title, subject_id=subject_id, user_id=current_user.id))
            db.session.commit()
            flash("Task created.", "success")
            return redirect(url_for("main.tasks"))
    items = (Task.query.filter_by(user_id=current_user.id)
             .order_by(Task.completed.asc(), Task.created_at.desc()).all())
    return render_template("tasks.html", tasks=items, subjects=subjects)


@main_bp.route("/tasks/toggle/<int:task_id>", methods=["POST"])
@login_required
def toggle_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    task.completed = not task.completed
    db.session.commit()
    return redirect(url_for("main.tasks"))


@main_bp.route("/tasks/delete/<int:task_id>", methods=["POST"])
@login_required
def delete_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    db.session.delete(task)
    db.session.commit()
    flash("Task removed.", "success")
    return redirect(url_for("main.tasks"))


# ---------------------------------------------------------------------- notes
@main_bp.route("/notes", methods=["GET", "POST"])
@login_required
def notes():
    if request.method == "POST":
        title, e1 = form_text("title", 120, "Title")
        content, e2 = form_text("content", 10000, "Content")
        error = e1 or e2
        if error:
            flash(error, "error")
        else:
            db.session.add(Note(title=title, content=content, user_id=current_user.id))
            db.session.commit()
            flash("Note saved.", "success")
            return redirect(url_for("main.notes"))
    items = Note.query.filter_by(user_id=current_user.id).order_by(Note.created_at.desc()).all()
    return render_template("notes.html", notes=items)


@main_bp.route("/notes/delete/<int:note_id>", methods=["POST"])
@login_required
def delete_note(note_id):
    note = Note.query.filter_by(id=note_id, user_id=current_user.id).first_or_404()
    db.session.delete(note)
    db.session.commit()
    flash("Note deleted.", "success")
    return redirect(url_for("main.notes"))


# ---------------------------------------------------------------------- goals
@main_bp.route("/goals", methods=["GET", "POST"])
@login_required
def goals():
    if request.method == "POST":
        title, e1 = form_text("title", 120, "Goal title")
        target, e2 = form_int("target", "Target", 1, MAX_GOAL_TARGET)
        progress, e3 = form_int("progress", "Progress", 0, target if target else MAX_GOAL_TARGET, required=False)
        error = e1 or e2 or e3
        if error:
            flash(error, "error")
        else:
            db.session.add(Goal(title=title, progress=progress or 0, target=target, user_id=current_user.id))
            db.session.commit()
            flash("Goal added.", "success")
            return redirect(url_for("main.goals"))
    items = Goal.query.filter_by(user_id=current_user.id).all()
    return render_template("goals.html", goals=items)


@main_bp.route("/goals/update/<int:goal_id>", methods=["POST"])
@login_required
def update_goal(goal_id):
    goal = Goal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()
    progress, error = form_int("progress", "Progress", 0, goal.target)
    if error:
        flash(error, "error")
    else:
        goal.progress = progress
        db.session.commit()
        flash("Goal progress updated.", "success")
    return redirect(url_for("main.goals"))


@main_bp.route("/goals/delete/<int:goal_id>", methods=["POST"])
@login_required
def delete_goal(goal_id):
    goal = Goal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()
    db.session.delete(goal)
    db.session.commit()
    flash("Goal deleted.", "success")
    return redirect(url_for("main.goals"))


# ------------------------------------------------------------------- calendar
@main_bp.route("/calendar")
@login_required
def calendar():
    offset = max(-520, min(520, request.args.get("week", 0, type=int)))
    today = local_today()
    sunday = today - timedelta(days=(today.weekday() + 1) % 7)  # week starts on Sunday
    start = sunday + timedelta(weeks=offset)
    end = start + timedelta(days=7)

    week_sessions = (
        StudySession.query
        .filter(StudySession.user_id == current_user.id,
                StudySession.created_at >= local_day_start_utc(start),
                StudySession.created_at < local_day_start_utc(end))
        .order_by(StudySession.created_at.asc())
        .all()
    )
    days = []
    for i in range(7):
        day = start + timedelta(days=i)
        days.append({
            "date": day,
            "is_today": day == today,
            "sessions": [s for s in week_sessions if to_local(s.created_at).date() == day],
        })
    return render_template(
        "calendar.html", days=days, week_start=start, week_end=end - timedelta(days=1),
        offset=offset, total_minutes=sum(s.duration or 0 for s in week_sessions),
    )


@main_bp.route("/profile")
@login_required
def profile():
    return render_template("profile.html", streak=compute_streak(current_user.id))