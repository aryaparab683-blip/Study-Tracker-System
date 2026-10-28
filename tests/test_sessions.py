from datetime import timedelta
from tests.test_base import BaseTestCase
from models import db, Subject, StudySession
from utils import local_today


class SessionsTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user(email="sessions@example.com", password="password123")
        self.login_user(email="sessions@example.com", password="password123")
        self.subject = Subject(name="Mathematics", color="#8E88A3", user_id=self.user.id)
        db.session.add(self.subject)
        db.session.commit()

    def test_create_session_success(self):
        csrf = self.get_csrf("/sessions")
        response = self.client.post("/sessions", data={
            "csrf_token": csrf,
            "title": "Calculus Integration Practice",
            "duration": 45,
            "subject_id": str(self.subject.id),
            "date": local_today().isoformat(),
            "notes": "Solved practice questions 1-10",
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Study session logged", response.data.decode("utf-8"))
        session = StudySession.query.filter_by(title="Calculus Integration Practice").first()
        self.assertIsNotNone(session)
        self.assertEqual(session.duration, 45)
        self.assertEqual(session.subject_id, self.subject.id)

    def test_duration_boundary_rejection(self):
        csrf = self.get_csrf("/sessions")
        # 0 minutes rejected
        resp1 = self.client.post("/sessions", data={
            "csrf_token": csrf,
            "title": "Zero Duration",
            "duration": 0,
            "subject_id": "",
        }, follow_redirects=True)
        self.assertIn("must be between 1 and 1,440", resp1.data.decode("utf-8"))

        # > 1440 minutes rejected
        resp2 = self.client.post("/sessions", data={
            "csrf_token": csrf,
            "title": "Too Long",
            "duration": 1441,
            "subject_id": "",
        }, follow_redirects=True)
        self.assertIn("must be between 1 and 1,440", resp2.data.decode("utf-8"))

    def test_future_date_rejected(self):
        csrf = self.get_csrf("/sessions")
        tomorrow = local_today() + timedelta(days=2)
        response = self.client.post("/sessions", data={
            "csrf_token": csrf,
            "title": "Future Session",
            "duration": 30,
            "subject_id": "",
            "date": tomorrow.isoformat(),
        }, follow_redirects=True)
        self.assertIn("in the future", response.data.decode("utf-8"))

    def test_edit_session_success(self):
        # Create initial session
        study = StudySession(
            title="Old Title",
            duration=30,
            notes="Old notes",
            subject_id=self.subject.id,
            user_id=self.user.id,
        )
        db.session.add(study)
        db.session.commit()

        csrf = self.get_csrf(f"/sessions/edit/{study.id}")
        response = self.client.post(f"/sessions/edit/{study.id}", data={
            "csrf_token": csrf,
            "title": "Updated Title",
            "duration": 60,
            "subject_id": str(self.subject.id),
            "date": local_today().isoformat(),
            "notes": "Updated notes",
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Study session updated", response.data.decode("utf-8"))

        db.session.refresh(study)
        self.assertEqual(study.title, "Updated Title")
        self.assertEqual(study.duration, 60)

    def test_delete_session_success(self):
        study = StudySession(
            title="To Delete",
            duration=25,
            user_id=self.user.id,
        )
        db.session.add(study)
        db.session.commit()

        csrf = self.get_csrf("/sessions")
        response = self.client.post(f"/sessions/delete/{study.id}", data={
            "csrf_token": csrf,
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Study session deleted", response.data.decode("utf-8"))
        self.assertIsNone(db.session.get(StudySession, study.id))

    def test_cannot_assign_unowned_subject(self):
        # Create another user and their subject
        other_user = self.create_user(email="other@example.com", password="password123")
        other_subject = Subject(name="Confidential Subject", color="#C496A1", user_id=other_user.id)
        db.session.add(other_subject)
        db.session.commit()

        csrf = self.get_csrf("/sessions")
        response = self.client.post("/sessions", data={
            "csrf_token": csrf,
            "title": "Trying to steal subject",
            "duration": 30,
            "subject_id": str(other_subject.id),
        }, follow_redirects=True)
        self.assertIn("Selected subject was not found", response.data.decode("utf-8"))
