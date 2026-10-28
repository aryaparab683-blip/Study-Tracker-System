from tests.test_base import BaseTestCase
from models import User
from routes.auth import _failures


class AuthTestCase(BaseTestCase):
    def test_successful_registration(self):
        csrf = self.get_csrf("/register")
        response = self.client.post("/register", data={
            "csrf_token": csrf,
            "name": "Alex Smith",
            "email": "alex@example.com",
            "password": "securepassword123",
            "confirm": "securepassword123",
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Account created successfully", response.data.decode("utf-8"))
        user = User.query.filter_by(email="alex@example.com").first()
        self.assertIsNotNone(user)
        self.assertEqual(user.name, "Alex Smith")

    def test_duplicate_email_registration_rejected(self):
        self.create_user(name="Original User", email="duplicate@example.com")
        csrf = self.get_csrf("/register")
        response = self.client.post("/register", data={
            "csrf_token": csrf,
            "name": "Imposter",
            "email": "duplicate@example.com",
            "password": "securepassword123",
            "confirm": "securepassword123",
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("already exists", response.data.decode("utf-8"))

    def test_password_too_short_rejected(self):
        csrf = self.get_csrf("/register")
        response = self.client.post("/register", data={
            "csrf_token": csrf,
            "name": "Short Pass User",
            "email": "short@example.com",
            "password": "123",
            "confirm": "123",
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("at least 8 characters", response.data.decode("utf-8"))

    def test_password_mismatch_rejected(self):
        csrf = self.get_csrf("/register")
        response = self.client.post("/register", data={
            "csrf_token": csrf,
            "name": "Mismatch User",
            "email": "mismatch@example.com",
            "password": "password123",
            "confirm": "password999",
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("do not match", response.data.decode("utf-8"))

    def test_successful_login(self):
        self.create_user(email="login@example.com", password="mypassword123")
        response = self.login_user(email="login@example.com", password="mypassword123")
        self.assertEqual(response.status_code, 200)
        # Should redirect to dashboard
        self.assertIn("Dashboard", response.data.decode("utf-8"))

    def test_invalid_password_rejected(self):
        self.create_user(email="user@example.com", password="correctpassword")
        response = self.login_user(email="user@example.com", password="wrongpassword")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Invalid email or password", response.data.decode("utf-8"))

    def test_brute_force_throttle_locks_after_five_attempts(self):
        _failures.clear()
        self.create_user(email="target@example.com", password="correctpassword")
        for i in range(5):
            self.login_user(email="target@example.com", password="wrongpassword")
        # Sixth attempt should be throttled
        response = self.login_user(email="target@example.com", password="correctpassword")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Too many failed attempts", response.data.decode("utf-8"))

    def test_logout(self):
        self.create_user(email="logout@example.com", password="password123")
        self.login_user(email="logout@example.com", password="password123")
        csrf = self.get_csrf("/dashboard")
        response = self.client.post("/logout", data={"csrf_token": csrf}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("You have been logged out", response.data.decode("utf-8"))
        # Verify subsequent dashboard request redirects to login
        dash_resp = self.client.get("/dashboard")
        self.assertEqual(dash_resp.status_code, 302)

    def test_protected_routes_require_login(self):
        protected = ["/dashboard", "/sessions", "/tasks", "/notes", "/goals", "/calendar", "/profile"]
        for path in protected:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 302, f"Route {path} should redirect unauthenticated user")
            self.assertIn("/login", response.headers.get("Location", ""))

    def test_authenticated_user_redirected_from_login_and_register(self):
        self.create_user(email="auth@example.com", password="password123")
        self.login_user(email="auth@example.com", password="password123")
        for path in ["/login", "/register"]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 302)
            self.assertIn("/dashboard", response.headers.get("Location", ""))

