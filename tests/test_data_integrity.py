from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from tests.test_base import BaseTestCase
from models import db, User, Subject, StudySession, Task, Note, Goal


class DataIntegrityTestCase(BaseTestCase):
    """Verifies foreign key constraints and deletion behaviors in an isolated test database."""

    def test_sqlite_foreign_key_pragmas_enabled(self):
        """Verify that foreign keys are enabled on the SQLite connection."""
        cursor = db.session.connection().connection.cursor()
        cursor.execute("PRAGMA foreign_keys;")
        result = cursor.fetchone()
        cursor.close()
        print("\nCurrent PRAGMA foreign_keys status:", result[0])

    def test_foreign_key_enforcement_prevents_orphan_insert(self):
        """With foreign keys ON, inserting a session with an invalid user_id must fail."""
        # Enable FK for this connection
        conn = db.session.connection().connection
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()

        # Try to insert session for non-existent user 999999
        invalid_session = StudySession(title="Ghost Session", duration=25, user_id=999999)
        db.session.add(invalid_session)
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_subject_deletion_with_linked_sessions_and_tasks_under_foreign_keys_on(self):
        """Deleting a subject with FK ON should cleanly unassign linked sessions and tasks without constraint violation."""
        conn = db.session.connection().connection
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()

        user = self.create_user(email="subjdel_fk@test.com", password="password123")
        self.login_user(email="subjdel_fk@test.com", password="password123")

        subject = Subject(name="Biology", color="#8E88A3", user_id=user.id)
        db.session.add(subject)
        db.session.commit()

        session1 = StudySession(title="Cell Biology", duration=45, subject_id=subject.id, user_id=user.id)
        task1 = Task(title="Mitosis quiz", subject_id=subject.id, user_id=user.id)
        db.session.add_all([session1, task1])
        db.session.commit()

        # Delete subject via route
        csrf = self.get_csrf("/subjects")
        response = self.client.post(f"/subjects/delete/{subject.id}", data={"csrf_token": csrf}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Subject deleted", response.data.decode("utf-8"))

        # Verify subject is removed
        self.assertIsNone(db.session.get(Subject, subject.id))

        # Verify linked session and task are safely set to NULL
        refreshed_session = db.session.get(StudySession, session1.id)
        self.assertIsNotNone(refreshed_session)
        self.assertIsNone(refreshed_session.subject_id)

        refreshed_task = db.session.get(Task, task1.id)
        self.assertIsNotNone(refreshed_task)
        self.assertIsNone(refreshed_task.subject_id)

    def test_subject_deletion_with_linked_sessions_and_tasks(self):
        """Deleting a subject should unassign linked sessions and tasks (subject_id -> NULL)."""
        user = self.create_user(email="subjdel@test.com", password="password123")
        self.login_user(email="subjdel@test.com", password="password123")

        subject = Subject(name="Chemistry", color="#8E88A3", user_id=user.id)
        db.session.add(subject)
        db.session.commit()

        session1 = StudySession(title="Organic Chemistry", duration=45, subject_id=subject.id, user_id=user.id)
        task1 = Task(title="Lab report", subject_id=subject.id, user_id=user.id)
        db.session.add_all([session1, task1])
        db.session.commit()

        # Delete subject via route
        csrf = self.get_csrf("/subjects")
        response = self.client.post(f"/subjects/delete/{subject.id}", data={"csrf_token": csrf}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Subject deleted", response.data.decode("utf-8"))

        # Verify subject is removed
        self.assertIsNone(db.session.get(Subject, subject.id))

        # Verify linked session and task still exist and are now unassigned (subject_id = None)
        refreshed_session = db.session.get(StudySession, session1.id)
        self.assertIsNotNone(refreshed_session)
        self.assertIsNone(refreshed_session.subject_id)

        refreshed_task = db.session.get(Task, task1.id)
        self.assertIsNotNone(refreshed_task)
        self.assertIsNone(refreshed_task.subject_id)
