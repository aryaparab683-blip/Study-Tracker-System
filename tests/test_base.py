import os
import re
import tempfile
import unittest

# Ensure tests never connect to the real instance/study_tracker.db
# We point DATABASE_URL to an isolated temporary file before importing the app
_temp_db_fd, _temp_db_path = tempfile.mkstemp(prefix="study_tracker_test_", suffix=".db")
os.close(_temp_db_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_temp_db_path}"
os.environ["FLASK_DEBUG"] = "0"

from main import create_app
from models import db, User, Subject, StudySession, Task, Note, Goal, Reminder
from werkzeug.security import generate_password_hash


class BaseTestCase(unittest.TestCase):
    """Base test case providing an isolated database and test client."""

    @classmethod
    def setUpClass(cls):
        cls.db_path = _temp_db_path
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.app.config["WTF_CSRF_ENABLED"] = True

    def setUp(self):
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.db_path):
            try:
                os.remove(cls.db_path)
            except OSError:
                pass

    def get_csrf(self, path="/login", client=None):
        """Extract CSRF token from a rendered form."""
        c = client or self.client
        response = c.get(path)
        match = re.search(r'name="csrf_token"\s+value="([a-f0-9]+)"', response.data.decode("utf-8"))
        if not match:
            match = re.search(r'value="([a-f0-9]+)"\s+name="csrf_token"', response.data.decode("utf-8"))
        return match.group(1) if match else None

    def create_user(self, name="Test Student", email="student@test.com", password="password123"):
        """Create and commit a test user."""
        user = User(
            name=name,
            email=email,
            password=generate_password_hash(password, method="pbkdf2:sha256", salt_length=16),
        )
        db.session.add(user)
        db.session.commit()
        return user

    def login_user(self, email="student@test.com", password="password123"):
        """Log in a user through the client using standard form POST."""
        csrf = self.get_csrf("/login")
        return self.client.post("/login", data={
            "csrf_token": csrf,
            "email": email,
            "password": password,
        }, follow_redirects=True)

