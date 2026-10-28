from tests.test_base import BaseTestCase
from models import db, Subject, StudySession, Task, Note, Goal


class UserDataIsolationTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        # User A (Alice)
        self.user_a = self.create_user(name="Alice", email="alice@test.com", password="password123")
        # User B (Bob)
        self.user_b = self.create_user(name="Bob", email="bob@test.com", password="password123")

        # Bob's private records
        self.bob_subject = Subject(name="Bob Private Subject", color="#8E88A3", user_id=self.user_b.id)
        db.session.add(self.bob_subject)
        db.session.commit()

        self.bob_session = StudySession(title="Bob Secret Session", duration=50, subject_id=self.bob_subject.id, user_id=self.user_b.id)
        self.bob_task = Task(title="Bob Private Task", user_id=self.user_b.id)
        self.bob_note = Note(title="Bob Secret Note", content="Top secret formulas", user_id=self.user_b.id)
        self.bob_goal = Goal(title="Bob Secret Goal", progress=10, target=50, user_id=self.user_b.id)
        db.session.add_all([self.bob_session, self.bob_task, self.bob_note, self.bob_goal])
        db.session.commit()

        # Log in as Alice
        self.login_user(email="alice@test.com", password="password123")

    def test_alice_cannot_see_bob_session(self):
        response = self.client.get("/sessions")
        self.assertNotIn("Bob Secret Session", response.data.decode("utf-8"))

    def test_alice_cannot_edit_bob_session(self):
        # Alice tries to GET Bob's session edit page
        resp = self.client.get(f"/sessions/edit/{self.bob_session.id}")
        self.assertEqual(resp.status_code, 404)

        # Alice tries to POST to Bob's session edit endpoint
        csrf = self.get_csrf("/dashboard")
        resp = self.client.post(f"/sessions/edit/{self.bob_session.id}", data={
            "csrf_token": csrf,
            "title": "Hacked Title",
            "duration": 10,
        })
        self.assertEqual(resp.status_code, 404)

    def test_alice_cannot_delete_bob_session(self):
        csrf = self.get_csrf("/dashboard")
        resp = self.client.post(f"/sessions/delete/{self.bob_session.id}", data={"csrf_token": csrf})
        self.assertEqual(resp.status_code, 404)
        self.assertIsNotNone(db.session.get(StudySession, self.bob_session.id))

    def test_alice_cannot_toggle_bob_task(self):
        csrf = self.get_csrf("/dashboard")
        resp = self.client.post(f"/tasks/toggle/{self.bob_task.id}", data={"csrf_token": csrf})
        self.assertEqual(resp.status_code, 404)

    def test_alice_cannot_delete_bob_task(self):
        csrf = self.get_csrf("/dashboard")
        resp = self.client.post(f"/tasks/delete/{self.bob_task.id}", data={"csrf_token": csrf})
        self.assertEqual(resp.status_code, 404)
        self.assertIsNotNone(db.session.get(Task, self.bob_task.id))

    def test_alice_cannot_delete_bob_note(self):
        csrf = self.get_csrf("/dashboard")
        resp = self.client.post(f"/notes/delete/{self.bob_note.id}", data={"csrf_token": csrf})
        self.assertEqual(resp.status_code, 404)
        self.assertIsNotNone(db.session.get(Note, self.bob_note.id))

    def test_alice_cannot_update_or_delete_bob_goal(self):
        csrf = self.get_csrf("/dashboard")
        resp1 = self.client.post(f"/goals/update/{self.bob_goal.id}", data={"csrf_token": csrf, "progress": 40})
        self.assertEqual(resp1.status_code, 404)

        resp2 = self.client.post(f"/goals/delete/{self.bob_goal.id}", data={"csrf_token": csrf})
        self.assertEqual(resp2.status_code, 404)
        self.assertIsNotNone(db.session.get(Goal, self.bob_goal.id))

    def test_alice_cannot_edit_or_delete_bob_subject(self):
        csrf = self.get_csrf("/dashboard")
        resp1 = self.client.post(f"/subjects/edit/{self.bob_subject.id}", data={"csrf_token": csrf, "name": "Stolen", "color": "#123456"})
        self.assertEqual(resp1.status_code, 404)

        resp2 = self.client.post(f"/subjects/delete/{self.bob_subject.id}", data={"csrf_token": csrf})
        self.assertEqual(resp2.status_code, 404)
        self.assertIsNotNone(db.session.get(Subject, self.bob_subject.id))

    def test_alice_dashboard_shows_zero_minutes(self):
        response = self.client.get("/dashboard")
        html = response.data.decode("utf-8")
        self.assertNotIn("Bob Secret Session", html)
        self.assertNotIn("Bob Private Task", html)
        self.assertNotIn("Bob Secret Note", html)
        self.assertNotIn("Bob Secret Goal", html)
