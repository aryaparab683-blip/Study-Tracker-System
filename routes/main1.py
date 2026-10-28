import re
from datetime import datetime, time, timedelta

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import login_required, current_user
from sqlalchemy import case, func

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
def get_week_comparison(uid, sunday, week_minutes):
    """Calculates study time comparison between current week (Sunday-now) and previous week."""
    last_week_start = sunday - timedelta(days=7)
    last_week_end = sunday
    last_week_minutes = (
        db.session.query(func.coalesce(func.sum(StudySession.duration), 0))
        .filter(
            StudySession.user_id == uid,
            StudySession.created_at >= local_day_start_utc(last_week_start),
            StudySession.created_at < local_day_start_utc(last_week_end),
        )
        .scalar()
    ) or 0
    week_minutes = week_minutes or 0

    diff_minutes = week_minutes - last_week_minutes
    if last_week_minutes > 0:
        pct_change = round((diff_minutes / last_week_minutes) * 100)
    else:
        pct_change = 100 if week_minutes > 0 else 0

    return {
        "this_week_minutes": week_minutes,
        "this_week_hours": round(week_minutes / 60, 1),
        "last_week_minutes": last_week_minutes,
        "last_week_hours": round(last_week_minutes / 60, 1),
        "diff_minutes": diff_minutes,
        "diff_hours": round(abs(diff_minutes) / 60, 1),
        "pct_change": pct_change,
        "trend": "up" if diff_minutes > 0 else ("down" if diff_minutes < 0 else "same"),
        "has_last_week": last_week_minutes > 0,
    }


def compute_dashboard_insights(uid, sunday, week_minutes, seven_days, subjects):
    """Derives honest, transparent, data-driven study habit insights strictly from user's sessions."""
    insights = []

    # 1. Top Focus Subject (This week if available, else all-time)
    this_week_subj = (
        db.session.query(StudySession.subject_id, func.sum(StudySession.duration))
        .filter(StudySession.user_id == uid, StudySession.created_at >= local_day_start_utc(sunday))
        .group_by(StudySession.subject_id)
        .order_by(func.sum(StudySession.duration).desc())
        .first()
    )

    subj_map = {s.id: s.name for s in subjects}
    if this_week_subj and (this_week_subj[1] or 0) > 0:
        sid, mins = this_week_subj
        sname = subj_map.get(sid, "General")
        pct = round((mins / week_minutes) * 100) if week_minutes > 0 else 100
        insights.append({
            "icon": "📚",
            "title": "Top Focus Subject",
            "text": f"{sname} is your most studied subject this week ({mins}m, {pct}% of weekly study time).",
        })
    else:
        # Check all-time top subject
        all_time_subj = (
            db.session.query(StudySession.subject_id, func.sum(StudySession.duration))
            .filter(StudySession.user_id == uid)
            .group_by(StudySession.subject_id)
            .order_by(func.sum(StudySession.duration).desc())
            .first()
        )
        if all_time_subj and (all_time_subj[1] or 0) > 0:
            sid, mins = all_time_subj
            sname = subj_map.get(sid, "General")
            insights.append({
                "icon": "📚",
                "title": "Top Focus Subject",
                "text": f"{sname} is your all-time top focus subject ({mins}m logged across your sessions).",
            })
        else:
            insights.append({
                "icon": "📚",
                "title": "Top Focus Subject",
                "text": "Log your first study session to reveal your subject distribution patterns.",
            })

    # 2. Observed Study Window / Time-of-Day Pattern
    all_sessions = (
        StudySession.query.with_entities(StudySession.created_at, StudySession.duration)
        .filter_by(user_id=uid)
        .all()
    )
    valid_sessions = [s for s in all_sessions if s[0] and (s[1] or 0) > 0]
    if len(valid_sessions) >= 2:
        slots = {
            "Morning (5 AM – 12 PM)": 0,
            "Afternoon (12 PM – 5 PM)": 0,
            "Evening (5 PM – 10 PM)": 0,
            "Night (10 PM – 5 AM)": 0,
        }
        total_focus = 0
        for created_at, duration in valid_sessions:
            dur = duration or 0
            try:
                h = to_local(created_at).hour
            except Exception:
                continue
            total_focus += dur
            if 5 <= h < 12:
                slots["Morning (5 AM – 12 PM)"] += dur
            elif 12 <= h < 17:
                slots["Afternoon (12 PM – 5 PM)"] += dur
            elif 17 <= h < 22:
                slots["Evening (5 PM – 10 PM)"] += dur
            else:
                slots["Night (10 PM – 5 AM)"] += dur

        best_slot, best_dur = max(slots.items(), key=lambda item: item[1])
        if total_focus > 0 and best_dur > 0:
            pct = round((best_dur / total_focus) * 100)
            insights.append({
                "icon": "⏰",
                "title": "Primary Focus Window",
                "text": f"Observed pattern: {pct}% of your recorded study time is logged in the {best_slot}.",
            })
        else:
            insights.append({
                "icon": "⏰",
                "title": "Primary Focus Window",
                "text": "Complete a few focus sessions to observe your typical study-hour patterns.",
            })
    else:
        insights.append({
            "icon": "⏰",
            "title": "Primary Focus Window",
            "text": "Complete at least 2 sessions to observe your typical study-hour patterns.",
        })

    # 3. Weekly Consistency & Pace
    active_days = sum(1 for d in seven_days if d["minutes"] > 0)
    seven_day_total = sum(d["minutes"] for d in seven_days)
    if active_days >= 5:
        insights.append({
            "icon": "🔥",
            "title": "Weekly Study Rhythm",
            "text": f"High consistency! Active on {active_days} of the past 7 days ({seven_day_total}m total). Great momentum!",
        })
    elif active_days >= 2:
        avg_active = round(seven_day_total / active_days)
        insights.append({
            "icon": "⚡",
            "title": "Weekly Study Rhythm",
            "text": f"Steady progress: Active on {active_days} of the past 7 days, averaging {avg_active}m per active day.",
        })
    elif active_days == 1:
        insights.append({
            "icon": "🌱",
            "title": "Weekly Study Rhythm",
            "text": "You logged 1 active day in the past week. Start a 25m focus timer today to build momentum!",
        })
    else:
        insights.append({
            "icon": "💡",
            "title": "Weekly Study Rhythm",
            "text": "No sessions logged in the last 7 days. Start with a short Pomodoro session today!",
        })

    return insights


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
    overdue_task_count = open_tasks_q.filter(Task.due_date < today).count()
    prio_order = case((Task.priority == "High", 1), (Task.priority == "Medium", 2), (Task.priority == "Low", 3), else_=4)
    open_tasks = (
        open_tasks_q
        .order_by(
            Task.due_date.asc().nullslast(),
            prio_order.asc(),
            Task.created_at.desc(),
        )
        .limit(5)
        .all()
    )
    for t in open_tasks:
        t.due_info = format_task_due_status(t, today)

    total_sessions = StudySession.query.filter_by(user_id=uid).count()
    total_time = db.session.query(func.coalesce(func.sum(StudySession.duration), 0)).filter(StudySession.user_id == uid).scalar()

    counts = dict(
        db.session.query(StudySession.subject_id, func.count(StudySession.id))
        .filter(StudySession.user_id == uid)
        .group_by(StudySession.subject_id)
        .all()
    )
    subject_breakdown = [
        {"name": s.name, "count": counts.get(s.id, 0), "color": s.color or "#8E88A3"}
        for s in subjects if counts.get(s.id, 0) > 0
    ]
    if counts.get(None, 0) > 0:
        subject_breakdown.append({"name": "General", "count": counts[None], "color": "#A89F91"})

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

    week_comparison = get_week_comparison(uid, sunday, week_minutes)
    dashboard_insights = compute_dashboard_insights(uid, sunday, week_minutes, seven_days, subjects)

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
        week_comparison=week_comparison,
        dashboard_insights=dashboard_insights,
        open_tasks=open_tasks,
        open_task_count=open_task_count,
        overdue_task_count=overdue_task_count,
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


@main_bp.route("/api/pomodoro/log", methods=["POST"])
@login_required
def log_pomodoro():
    # 1. Validate idempotency token
    token = (request.form.get("token") or "").strip()
    if not token or len(token) > 64 or not re.match(r"^[A-Za-z0-9_-]+$", token):
        return jsonify({"error": "Invalid or missing session token."}), 400

    # 2. Check for duplicate submission using the token
    token_tag = f"[token:{token}]"
    existing = StudySession.query.filter(
        StudySession.user_id == current_user.id,
        StudySession.notes.like(f"%{token_tag}%"),
    ).first()
    if existing:
        return jsonify({
            "status": "already_logged",
            "message": "Session was already recorded.",
            "session": {
                "id": existing.id,
                "title": existing.title,
                "duration": existing.duration,
            },
        }), 200

    # 3. Validate duration (bounded to reasonable focus block: 1 to 180 minutes)
    duration, dur_err = form_int("duration", "Duration", 1, 180)
    if dur_err:
        return jsonify({"error": dur_err}), 400

    # 4. Validate subject ownership
    subject_id, subj_err = owned_subject_id()
    if subj_err:
        return jsonify({"error": subj_err}), 400

    # 5. Determine title
    title = (request.form.get("title") or "").strip()
    subject_obj = None
    if subject_id:
        subject_obj = db.session.get(Subject, subject_id)
    if not title:
        title = f"Focus: {subject_obj.name}" if subject_obj else "Focus Session"
    if len(title) > 120:
        title = title[:120]

    # 6. Create StudySession record
    notes = f"Pomodoro focus session. {token_tag}"
    new_session = StudySession(
        title=title,
        duration=duration,
        notes=notes,
        subject_id=subject_id,
        created_at=utcnow(),
        user_id=current_user.id,
    )
    db.session.add(new_session)
    db.session.commit()

    # 7. Compute updated stats for live UI update without full reload
    uid = current_user.id
    today = local_today()
    sunday = today - timedelta(days=(today.weekday() + 1) % 7)
    week_minutes = (
        db.session.query(func.coalesce(func.sum(StudySession.duration), 0))
        .filter(StudySession.user_id == uid, StudySession.created_at >= local_day_start_utc(sunday))
        .scalar()
    )
    total_sessions = StudySession.query.filter_by(user_id=uid).count()
    total_time = db.session.query(func.coalesce(func.sum(StudySession.duration), 0)).filter(StudySession.user_id == uid).scalar()
    week_comp = get_week_comparison(uid, sunday, week_minutes)

    return jsonify({
        "status": "success",
        "message": f"Recorded {duration}m focus session!",
        "session": {
            "id": new_session.id,
            "title": new_session.title,
            "duration": new_session.duration,
            "subject_name": subject_obj.name if subject_obj else "General",
            "subject_color": subject_obj.color if subject_obj else "#A89F91",
            "date": to_local(new_session.created_at).strftime("%b %d"),
        },
        "stats": {
            "week_minutes": week_minutes,
            "week_hours": round(week_minutes / 60, 1),
            "last_week_minutes": week_comp["last_week_minutes"],
            "week_diff_minutes": week_comp["diff_minutes"],
            "week_diff_hours": week_comp["diff_hours"],
            "week_trend": week_comp["trend"],
            "total_sessions": total_sessions,
            "total_hours": round(total_time / 60, 1) if total_time else 0,
            "streak": compute_streak(uid),
        },
    }), 201


# ------------------------------------------------------------------- subjects
@main_bp.route("/subjects", methods=["GET", "POST"])
@login_required
def subjects():
    if request.method == "POST":
        name, error = form_text("name", 80, "Subject name")
        color = request.form.get("color") or "#8E88A3"
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
def parse_task_due_date(field_name="due_date"):
    """Optional 'due_date' field for tasks. Returns (date_obj or None, error or None)."""
    raw = (request.form.get(field_name) or "").strip()
    if not raw:
        return None, None
    try:
        chosen = datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None, "Due date must be a valid date in YYYY-MM-DD format."
    if chosen.year < 2000 or chosen.year > 2100:
        return None, "Due date year must be between 2000 and 2100."
    return chosen, None


def parse_task_priority(field_name="priority", default="Medium"):
    raw = (request.form.get(field_name) or default).strip().capitalize()
    if raw not in ("Low", "Medium", "High"):
        return None, "Priority must be Low, Medium, or High."
    return raw, None


def format_task_due_status(task, today):
    """Calculates relative due status and badge presentation for tasks."""
    if not task.due_date:
        return {
            "status": "none",
            "badge_class": "",
            "label": "",
            "is_overdue": False,
            "is_due_today": False,
        }
    delta = (task.due_date - today).days
    if task.completed:
        return {
            "status": "completed",
            "badge_class": "badge-due-muted",
            "label": f"Due {task.due_date.strftime('%b %d')}",
            "is_overdue": False,
            "is_due_today": False,
        }
    if delta < 0:
        days_over = abs(delta)
        return {
            "status": "overdue",
            "badge_class": "badge-due-overdue",
            "label": f"Overdue ({days_over}d)" if days_over > 1 else "Overdue (1d)",
            "is_overdue": True,
            "is_due_today": False,
        }
    elif delta == 0:
        return {
            "status": "due_today",
            "badge_class": "badge-due-today",
            "label": "Due today",
            "is_overdue": False,
            "is_due_today": True,
        }
    elif delta <= 7:
        return {
            "status": "upcoming",
            "badge_class": "badge-due-soon",
            "label": f"In {delta}d ({task.due_date.strftime('%b %d')})",
            "is_overdue": False,
            "is_due_today": False,
        }
    else:
        return {
            "status": "future",
            "badge_class": "badge-due-future",
            "label": f"Due {task.due_date.strftime('%b %d')}",
            "is_overdue": False,
            "is_due_today": False,
        }


@main_bp.route("/tasks", methods=["GET", "POST"])
@login_required
def tasks():
    subjects = Subject.query.filter_by(user_id=current_user.id).all()
    today = local_today()

    if request.method == "POST":
        title, e1 = form_text("title", 120, "Task title")
        subject_id, e2 = owned_subject_id()
        priority, e3 = parse_task_priority()
        due_date, e4 = parse_task_due_date()
        error = e1 or e2 or e3 or e4
        if error:
            flash(error, "error")
        else:
            db.session.add(Task(
                title=title,
                subject_id=subject_id,
                priority=priority,
                due_date=due_date,
                user_id=current_user.id,
            ))
            db.session.commit()
            flash("Task created.", "success")
            return redirect(url_for("main.tasks"))

    # Parse and sanitize filters with safe fallbacks
    raw_status = (request.args.get("status") or "all").lower()
    status_filter = raw_status if raw_status in ("all", "pending", "completed") else "all"

    raw_priority = (request.args.get("priority") or "all").capitalize()
    priority_filter = raw_priority if raw_priority in ("All", "Low", "Medium", "High") else "All"

    raw_subject = (request.args.get("subject_id") or "").strip()
    subject_filter = None
    if raw_subject.isdigit():
        subj_id_val = int(raw_subject)
        if any(s.id == subj_id_val for s in subjects):
            subject_filter = subj_id_val

    overdue_only = request.args.get("overdue") == "1"

    raw_sort = (request.args.get("sort") or "created").lower()
    sort_by = raw_sort if raw_sort in ("created", "due_date", "priority") else "created"

    # Base query restricted strictly to authenticated user
    query = Task.query.filter_by(user_id=current_user.id)

    # Apply filters
    if status_filter == "pending":
        query = query.filter(Task.completed == False)
    elif status_filter == "completed":
        query = query.filter(Task.completed == True)

    if priority_filter in ("Low", "Medium", "High"):
        query = query.filter(Task.priority == priority_filter)

    if subject_filter is not None:
        query = query.filter(Task.subject_id == subject_filter)

    if overdue_only:
        query = query.filter(Task.completed == False, Task.due_date < today)

    # Apply sort
    prio_order = case((Task.priority == "High", 1), (Task.priority == "Medium", 2), (Task.priority == "Low", 3), else_=4)
    if sort_by == "due_date":
        query = query.order_by(Task.completed.asc(), Task.due_date.asc().nullslast(), prio_order.asc(), Task.created_at.desc())
    elif sort_by == "priority":
        query = query.order_by(Task.completed.asc(), prio_order.asc(), Task.due_date.asc().nullslast(), Task.created_at.desc())
    else:
        query = query.order_by(Task.completed.asc(), Task.created_at.desc())

    items = query.all()
    for t in items:
        t.due_info = format_task_due_status(t, today)

    # Counts for tab badges
    all_user_tasks = Task.query.filter_by(user_id=current_user.id).all()
    total_count = len(all_user_tasks)
    pending_count = sum(1 for t in all_user_tasks if not t.completed)
    completed_count = sum(1 for t in all_user_tasks if t.completed)
    overdue_count = sum(1 for t in all_user_tasks if not t.completed and t.due_date and t.due_date < today)

    current_filters = {
        "status": status_filter,
        "priority": priority_filter,
        "subject_id": subject_filter or "",
        "overdue": overdue_only,
        "sort": sort_by,
        "total_count": total_count,
        "pending_count": pending_count,
        "completed_count": completed_count,
        "overdue_count": overdue_count,
    }

    return render_template(
        "tasks.html",
        tasks=items,
        subjects=subjects,
        filters=current_filters,
        today=today.isoformat(),
    )


@main_bp.route("/tasks/edit/<int:task_id>", methods=["GET", "POST"])
@login_required
def edit_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    subjects = Subject.query.filter_by(user_id=current_user.id).all()
    today = local_today()

    if request.method == "POST":
        title, e1 = form_text("title", 120, "Task title")
        subject_id, e2 = owned_subject_id()
        priority, e3 = parse_task_priority()
        due_date, e4 = parse_task_due_date()
        error = e1 or e2 or e3 or e4
        if error:
            flash(error, "error")
        else:
            task.title = title
            task.subject_id = subject_id
            task.priority = priority
            task.due_date = due_date
            if "completed" in request.form:
                task.completed = request.form.get("completed") == "1"
            db.session.commit()
            flash("Task updated.", "success")
            return redirect(url_for("main.tasks"))

    return render_template(
        "edit_task.html",
        task=task,
        subjects=subjects,
        today=today.isoformat(),
    )


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