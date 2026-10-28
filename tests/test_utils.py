from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from tests.test_base import BaseTestCase
from models import db, StudySession
from utils import (
    compute_streak, local_day_start_utc, local_today, safe_next_url, to_local,
)


class UtilsTestCase(BaseTestCase):
    def test_csrf_protection_blocks_post_without_token(self):
        user = self.create_user(email="csrf@test.com", password="password123")
        self.login_user(email="csrf@test.com", password="password123")
        # Direct POST without csrf_token parameter
        response = self.client.post("/sessions", data={
            "title": "Hacked Session",
            "duration": 30,
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("form expired or was invalid", response.data.decode("utf-8"))

    def test_safe_next_url_validation(self):
        self.assertEqual(safe_next_url("/dashboard"), "/dashboard")
        self.assertEqual(safe_next_url("/sessions?tab=all"), "/sessions?tab=all")
        # Reject external or malicious redirects
        self.assertIsNone(safe_next_url("https://evil.com"))
        self.assertIsNone(safe_next_url("//evil.com"))
        self.assertIsNone(safe_next_url("/\\evil.com"))
        self.assertIsNone(safe_next_url("javascript:alert(1)"))

    def test_streak_calculation(self):
        user = self.create_user(email="streak@test.com", password="password123")
        self.assertEqual(compute_streak(user.id), 0)

        # 1 session today -> streak 1
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        s1 = StudySession(title="Day 1", duration=30, user_id=user.id, created_at=now_utc)
        db.session.add(s1)
        db.session.commit()
        self.assertEqual(compute_streak(user.id), 1)

        # Session yesterday -> streak 2
        yesterday_utc = now_utc - timedelta(days=1)
        s2 = StudySession(title="Day 2", duration=30, user_id=user.id, created_at=yesterday_utc)
        db.session.add(s2)
        db.session.commit()
        self.assertEqual(compute_streak(user.id), 2)

        # If last session was 2 days ago (missed yesterday and today) -> streak 0
        db.session.delete(s1)
        db.session.delete(s2)
        two_days_ago_utc = now_utc - timedelta(days=2)
        s3 = StudySession(title="Old Day", duration=30, user_id=user.id, created_at=two_days_ago_utc)
        db.session.add(s3)
        db.session.commit()
        self.assertEqual(compute_streak(user.id), 0)

    def test_timezone_helpers(self):
        # Without cookie, defaults to UTC
        self.assertEqual(to_local(datetime(2026, 10, 29, 12, 0)).tzinfo, timezone.utc)

        # In context with Asia/Kolkata (+05:30) cookie
        with self.app.test_request_context(environ_base={"HTTP_COOKIE": "tz=Asia/Kolkata"}):
            local_dt = to_local(datetime(2026, 10, 29, 12, 0))
            self.assertEqual(str(local_dt.tzinfo), "Asia/Kolkata")
            # 12:00 UTC + 5:30 -> 17:30
            self.assertEqual(local_dt.hour, 17)
            self.assertEqual(local_dt.minute, 30)

