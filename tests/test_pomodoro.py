from tests.test_base import BaseTestCase
from models import db, Subject, StudySession


class PomodoroIntegrationTestCase(BaseTestCase):
    """Tests the Pomodoro backend logging endpoint and state validations."""

    def setUp(self):
        super().setUp()
        self.user = self.create_user(email="pomo_user@test.com", password="password123")
        self.login_user(email="pomo_user@test.com", password="password123")

        self.subject = Subject(name="Operating Systems", color="#8E88A3", user_id=self.user.id)
        db.session.add(self.subject)
        db.session.commit()

    def test_focus_session_persisted_successfully(self):
        """A valid completed focus session is saved to StudySession."""
        csrf = self.get_csrf("/dashboard")
        response = self.client.post("/api/pomodoro/log", data={
            "csrf_token": csrf,
            "token": "pomo_1730164800_abc1",
            "duration": 25,
            "subject_id": str(self.subject.id),
        })
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["session"]["duration"], 25)

        # Check in DB
        session = db.session.get(StudySession, data["session"]["id"])
        self.assertIsNotNone(session)
        self.assertEqual(session.user_id, self.user.id)
        self.assertEqual(session.subject_id, self.subject.id)
        self.assertIn("Focus: Operating Systems", session.title)
        self.assertIn("[token:pomo_1730164800_abc1]", session.notes)

    def test_session_without_subject_defaults_to_general(self):
        """Focus session without subject assigns subject_id=None and General title."""
        csrf = self.get_csrf("/dashboard")
        response = self.client.post("/api/pomodoro/log", data={
            "csrf_token": csrf,
            "token": "pomo_1730164800_abc2",
            "duration": 25,
            "subject_id": "",
        })
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data["session"]["subject_name"], "General")

        session = db.session.get(StudySession, data["session"]["id"])
        self.assertIsNone(session.subject_id)
        self.assertEqual(session.title, "Focus Session")

    def test_unauthenticated_request_rejected(self):
        """Unauthenticated call to /api/pomodoro/log must redirect to /login."""
        # Log out first
        csrf = self.get_csrf("/dashboard")
        self.client.post("/logout", data={"csrf_token": csrf})

        # Fetch fresh CSRF token while unauthenticated
        login_csrf = self.get_csrf("/login")

        response = self.client.post("/api/pomodoro/log", data={
            "csrf_token": login_csrf,
            "token": "pomo_1730164800_anon",
            "duration": 25,
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers.get("Location", ""))
        self.assertIn("/login", response.headers.get("Location", ""))

    def test_missing_or_invalid_csrf_token_rejected(self):
        """Missing or forged CSRF token returns 400 Bad Request."""
        # No CSRF token
        resp1 = self.client.post("/api/pomodoro/log", data={
            "token": "pomo_1730164800_badcsrf1",
            "duration": 25,
        })
        self.assertEqual(resp1.status_code, 400)

        # Invalid CSRF token
        resp2 = self.client.post("/api/pomodoro/log", data={
            "csrf_token": "forged_token_value",
            "token": "pomo_1730164800_badcsrf2",
            "duration": 25,
        })
        self.assertEqual(resp2.status_code, 400)

    def test_another_users_subject_rejected(self):
        """Selecting another student's subject is rejected with an error."""
        bob = self.create_user(email="bob_pomo@test.com", password="password123")
        bob_subject = Subject(name="Bob Subject", color="#C496A1", user_id=bob.id)
        db.session.add(bob_subject)
        db.session.commit()

        csrf = self.get_csrf("/dashboard")
        response = self.client.post("/api/pomodoro/log", data={
            "csrf_token": csrf,
            "token": "pomo_1730164800_steal",
            "duration": 25,
            "subject_id": str(bob_subject.id),
        })
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("not found", data["error"])

    def test_invalid_duration_rejected(self):
        """Duration <= 0 or > 180 is rejected."""
        csrf = self.get_csrf("/dashboard")

        # Zero duration
        resp1 = self.client.post("/api/pomodoro/log", data={
            "csrf_token": csrf,
            "token": "pomo_1730164800_zero",
            "duration": 0,
        })
        self.assertEqual(resp1.status_code, 400)

        # Negative duration
        resp2 = self.client.post("/api/pomodoro/log", data={
            "csrf_token": csrf,
            "token": "pomo_1730164800_neg",
            "duration": -10,
        })
        self.assertEqual(resp2.status_code, 400)

        # Excessive duration (>180 min focus block)
        resp3 = self.client.post("/api/pomodoro/log", data={
            "csrf_token": csrf,
            "token": "pomo_1730164800_excess",
            "duration": 500,
        })
        self.assertEqual(resp3.status_code, 400)

    def test_duplicate_completion_requests_do_not_duplicate_records(self):
        """Duplicate POST requests with the same token are idempotent and do not create 2 records."""
        csrf = self.get_csrf("/dashboard")
        token = "pomo_idempotency_test_123"

        # First request
        resp1 = self.client.post("/api/pomodoro/log", data={
            "csrf_token": csrf,
            "token": token,
            "duration": 25,
        })
        self.assertEqual(resp1.status_code, 201)

        # Second request with identical token
        resp2 = self.client.post("/api/pomodoro/log", data={
            "csrf_token": csrf,
            "token": token,
            "duration": 25,
        })
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.get_json()
        self.assertEqual(data2["status"], "already_logged")

        # Verify only 1 record exists in the database with this token
        matching = StudySession.query.filter(
            StudySession.user_id == self.user.id,
            StudySession.notes.like(f"%[token:{token}]%")
        ).all()
        self.assertEqual(len(matching), 1)

    def test_dashboard_totals_reflect_saved_focus_session(self):
        """A saved focus session immediately increments week_minutes and total_sessions."""
        csrf = self.get_csrf("/dashboard")
        resp = self.client.post("/api/pomodoro/log", data={
            "csrf_token": csrf,
            "token": "pomo_dashboard_metrics_test",
            "duration": 25,
            "subject_id": str(self.subject.id),
        })
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertGreaterEqual(data["stats"]["week_minutes"], 25)
        self.assertGreaterEqual(data["stats"]["total_sessions"], 1)

        # Verify GET /dashboard contains the session
        dash_resp = self.client.get("/dashboard")
        self.assertEqual(dash_resp.status_code, 200)
        html = dash_resp.data.decode("utf-8")
        self.assertIn("Focus: Operating Systems", html)

    def test_existing_manual_session_logging_remains_functional(self):
        """The existing /sessions route continues to work normally."""
        csrf = self.get_csrf("/sessions")
        resp = self.client.post("/sessions", data={
            "csrf_token": csrf,
            "title": "Manual Study Block",
            "duration": 40,
            "subject_id": str(self.subject.id),
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Study session logged", resp.data.decode("utf-8"))
        saved = StudySession.query.filter_by(title="Manual Study Block").first()
        self.assertIsNotNone(saved)
        self.assertEqual(saved.duration, 40)
