from datetime import datetime, timedelta, timezone
from tests.test_base import BaseTestCase
from models import db, Subject, StudySession, utcnow
from utils import local_day_start_utc, local_today, to_local
from routes.main1 import get_week_comparison, compute_dashboard_insights


class DashboardAnalyticsTestCase(BaseTestCase):
    """Tests for Batch 3: Dashboard & Analytics, week-over-week comparisons, and habit insights."""

    def setUp(self):
        super().setUp()
        self.user = self.create_user(name="Dana Student", email="dana@test.com", password="password123")
        self.login_user(email="dana@test.com", password="password123")
        self.subject_os = Subject(name="Operating Systems", color="#8E88A3", user_id=self.user.id)
        self.subject_algo = Subject(name="Algorithms", color="#D9B56A", user_id=self.user.id)
        db.session.add_all([self.subject_os, self.subject_algo])
        db.session.commit()

    def test_empty_dashboard_renders_cleanly(self):
        """Zero sessions user gets 200 OK with safe zeros and graceful insight placeholders."""
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")

        self.assertIn("Welcome back, Dana", html)
        self.assertIn("0 <span class=\"metric-unit\">min</span>", html)
        self.assertIn("0 <span class=\"metric-unit\">sessions</span>", html)
        self.assertIn("Study Intelligence &amp; Habits", html)
        self.assertIn("Log your first study session", html)
        self.assertIn("Complete at least 2 sessions", html)

    def test_week_comparison_increase(self):
        """User studying more this week than last week shows positive diff and trend-up badge."""
        today = local_today()
        sunday = today - timedelta(days=(today.weekday() + 1) % 7)

        # 1 session of 60 mins last week (Wednesday of last week)
        last_week_dt = local_day_start_utc(sunday - timedelta(days=4)) + timedelta(hours=10)
        s1 = StudySession(title="Last Week Block", duration=60, user_id=self.user.id, created_at=last_week_dt)

        # 1 session of 120 mins this week (Sunday noon)
        this_week_dt = local_day_start_utc(sunday) + timedelta(hours=12)
        s2 = StudySession(title="This Week Block", duration=120, user_id=self.user.id, created_at=this_week_dt)

        db.session.add_all([s1, s2])
        db.session.commit()

        comp = get_week_comparison(self.user.id, sunday, 120)
        self.assertEqual(comp["this_week_minutes"], 120)
        self.assertEqual(comp["last_week_minutes"], 60)
        self.assertEqual(comp["diff_minutes"], 60)
        self.assertEqual(comp["diff_hours"], 1.0)
        self.assertEqual(comp["pct_change"], 100)
        self.assertEqual(comp["trend"], "up")
        self.assertTrue(comp["has_last_week"])

        # Check rendered HTML
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")
        self.assertIn("trend-up", html)
        self.assertIn("+1.0h vs last week", html)

    def test_week_comparison_decrease(self):
        """User studying less this week than last week shows negative diff and trend-down badge."""
        today = local_today()
        sunday = today - timedelta(days=(today.weekday() + 1) % 7)

        # 120 mins last week
        last_week_dt = local_day_start_utc(sunday - timedelta(days=3)) + timedelta(hours=14)
        s1 = StudySession(title="Heavy Last Week", duration=120, user_id=self.user.id, created_at=last_week_dt)

        # 45 mins this week
        this_week_dt = local_day_start_utc(sunday) + timedelta(hours=10)
        s2 = StudySession(title="Light This Week", duration=45, user_id=self.user.id, created_at=this_week_dt)

        db.session.add_all([s1, s2])
        db.session.commit()

        comp = get_week_comparison(self.user.id, sunday, 45)
        self.assertEqual(comp["this_week_minutes"], 45)
        self.assertEqual(comp["last_week_minutes"], 120)
        self.assertEqual(comp["diff_minutes"], -75)
        self.assertEqual(comp["trend"], "down")
        self.assertEqual(comp["diff_hours"], 1.2)

        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")
        self.assertIn("trend-down", html)
        self.assertIn("-1.2h vs last week", html)

    def test_week_comparison_first_active_week(self):
        """Zero last week and >0 this week renders 'First active week' cleanly without error."""
        today = local_today()
        sunday = today - timedelta(days=(today.weekday() + 1) % 7)

        this_week_dt = local_day_start_utc(sunday) + timedelta(hours=11)
        s = StudySession(title="First Ever Session", duration=50, user_id=self.user.id, created_at=this_week_dt)
        db.session.add(s)
        db.session.commit()

        comp = get_week_comparison(self.user.id, sunday, 50)
        self.assertEqual(comp["last_week_minutes"], 0)
        self.assertEqual(comp["this_week_minutes"], 50)
        self.assertFalse(comp["has_last_week"])

        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")
        self.assertIn("First active week", html)

    def test_week_boundary_exact_precision(self):
        """Sessions at Saturday 23:55 vs Sunday 00:05 bucket into separate weeks without overlap."""
        today = local_today()
        sunday = today - timedelta(days=(today.weekday() + 1) % 7)

        # Saturday 23:55 (5 minutes before this week began)
        sat_night_utc = local_day_start_utc(sunday) - timedelta(minutes=5)
        s_sat = StudySession(title="Saturday Night", duration=40, user_id=self.user.id, created_at=sat_night_utc)

        # Sunday 00:05 (5 minutes after this week began)
        sun_morning_utc = local_day_start_utc(sunday) + timedelta(minutes=5)
        s_sun = StudySession(title="Sunday Morning", duration=50, user_id=self.user.id, created_at=sun_morning_utc)

        db.session.add_all([s_sat, s_sun])
        db.session.commit()

        comp = get_week_comparison(self.user.id, sunday, 50)
        self.assertEqual(comp["last_week_minutes"], 40)
        self.assertEqual(comp["this_week_minutes"], 50)

    def test_analytics_user_isolation(self):
        """User A's dashboard analytics never include User B's study minutes, subjects, or insights."""
        # Create User B (Bob) with big activity
        bob = self.create_user(name="Bob Private", email="bob_analytics@test.com", password="password123")
        bob_subj = Subject(name="Confidential Robotics", color="#FF0000", user_id=bob.id)
        db.session.add(bob_subj)
        db.session.commit()

        today = local_today()
        sunday = today - timedelta(days=(today.weekday() + 1) % 7)
        bob_session = StudySession(
            title="Bob Secret Session",
            duration=300,
            subject_id=bob_subj.id,
            user_id=bob.id,
            created_at=local_day_start_utc(sunday) + timedelta(hours=9),
        )
        db.session.add(bob_session)
        db.session.commit()

        # Dana (logged in) visits /dashboard
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")

        self.assertNotIn("Confidential Robotics", html)
        self.assertNotIn("Bob Secret Session", html)
        self.assertIn("0 <span class=\"metric-unit\">min</span>", html)

    def test_top_subject_insight(self):
        """Top subject insight identifies the subject with highest study time."""
        today = local_today()
        sunday = today - timedelta(days=(today.weekday() + 1) % 7)

        # 90m of OS, 30m of Algo this week
        s1 = StudySession(
            title="OS Kernel", duration=90, subject_id=self.subject_os.id,
            user_id=self.user.id, created_at=local_day_start_utc(sunday) + timedelta(hours=10)
        )
        s2 = StudySession(
            title="Algo Dynamic Programming", duration=30, subject_id=self.subject_algo.id,
            user_id=self.user.id, created_at=local_day_start_utc(sunday) + timedelta(hours=14)
        )
        db.session.add_all([s1, s2])
        db.session.commit()

        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")

        self.assertIn("Operating Systems", html)
        self.assertIn("most studied subject this week", html)
        self.assertIn("90m", html)

    def test_peak_productivity_time_insight(self):
        """Sessions logged in morning hours result in Morning being highlighted as peak focus time."""
        today = local_today()
        sunday = today - timedelta(days=(today.weekday() + 1) % 7)

        # 2 morning sessions (e.g. 8 AM and 10 AM local)
        s1 = StudySession(
            title="Morning Focus 1", duration=45, user_id=self.user.id,
            created_at=local_day_start_utc(today) + timedelta(hours=8)
        )
        s2 = StudySession(
            title="Morning Focus 2", duration=50, user_id=self.user.id,
            created_at=local_day_start_utc(today) + timedelta(hours=10)
        )
        db.session.add_all([s1, s2])
        db.session.commit()

        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")

        self.assertIn("Primary Focus Window", html)
        self.assertIn("Morning (5 AM – 12 PM)", html)

    def test_pomodoro_and_manual_sessions_counted_consistently(self):
        """Manual sessions and Pomodoro sessions contribute identically to week totals without double counting."""
        # 1. Manual session via POST /sessions
        csrf1 = self.get_csrf("/sessions")
        resp1 = self.client.post("/sessions", data={
            "csrf_token": csrf1,
            "title": "Manual Reading",
            "duration": 40,
            "subject_id": str(self.subject_os.id),
        }, follow_redirects=True)
        self.assertEqual(resp1.status_code, 200)

        # 2. Pomodoro session via POST /api/pomodoro/log
        csrf2 = self.get_csrf("/dashboard")
        resp2 = self.client.post("/api/pomodoro/log", data={
            "csrf_token": csrf2,
            "token": "pomo_dash_consistency_test",
            "duration": 25,
            "subject_id": str(self.subject_algo.id),
        })
        self.assertEqual(resp2.status_code, 201)
        data2 = resp2.get_json()

        # Both sessions should sum to 65 minutes this week
        self.assertEqual(data2["stats"]["week_minutes"], 65)
        self.assertEqual(data2["stats"]["total_sessions"], 2)

        # Check GET /dashboard reflects exact 65 minutes
        dash_resp = self.client.get("/dashboard")
        self.assertEqual(dash_resp.status_code, 200)
        html = dash_resp.data.decode("utf-8")
        self.assertIn("65 <span class=\"metric-unit\">min</span>", html)
        self.assertIn("Manual Reading", html)
        self.assertIn("Focus: Algorithms", html)
