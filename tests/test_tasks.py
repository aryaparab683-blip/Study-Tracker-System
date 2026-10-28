from datetime import date, timedelta
from tests.test_base import BaseTestCase
from models import db, Subject, Task
from utils import local_today


class TaskManagementTestCase(BaseTestCase):
    """Tests for Batch 4: Task management improvements, priorities, due dates, filtering, and editing."""

    def setUp(self):
        super().setUp()
        self.user = self.create_user(name="Maya Student", email="maya@test.com", password="password123")
        self.login_user(email="maya@test.com", password="password123")

        self.subj_math = Subject(name="Calculus", color="#E0909F", user_id=self.user.id)
        self.subj_cs = Subject(name="Operating Systems", color="#8E88A3", user_id=self.user.id)
        db.session.add_all([self.subj_math, self.subj_cs])
        db.session.commit()

    def test_create_task_with_priority_and_due_date(self):
        """User can create a task specifying subject, priority, and due date."""
        csrf = self.get_csrf("/tasks")
        due = (local_today() + timedelta(days=3)).isoformat()

        response = self.client.post("/tasks", data={
            "csrf_token": csrf,
            "title": "Complete Assignment 3",
            "subject_id": str(self.subj_cs.id),
            "priority": "High",
            "due_date": due,
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Task created.", response.data.decode("utf-8"))

        task = Task.query.filter_by(title="Complete Assignment 3", user_id=self.user.id).first()
        self.assertIsNotNone(task)
        self.assertEqual(task.subject_id, self.subj_cs.id)
        self.assertEqual(task.priority, "High")
        self.assertEqual(task.due_date.isoformat(), due)
        self.assertFalse(task.completed)

    def test_create_task_defaults_priority_to_medium_and_due_date_to_none(self):
        """Omitting priority and due date defaults safely to Medium and None."""
        csrf = self.get_csrf("/tasks")
        response = self.client.post("/tasks", data={
            "csrf_token": csrf,
            "title": "Quick read",
            "subject_id": "",
            "priority": "",
            "due_date": "",
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        task = Task.query.filter_by(title="Quick read", user_id=self.user.id).first()
        self.assertIsNotNone(task)
        self.assertIsNone(task.subject_id)
        self.assertEqual(task.priority, "Medium")
        self.assertIsNone(task.due_date)

    def test_invalid_task_inputs_rejected(self):
        """Empty title, invalid priority, and invalid date format are rejected on server."""
        csrf = self.get_csrf("/tasks")

        # 1. Empty title
        resp1 = self.client.post("/tasks", data={
            "csrf_token": csrf,
            "title": "   ",
            "priority": "Low",
        }, follow_redirects=True)
        self.assertIn("Task title is required", resp1.data.decode("utf-8"))

        # 2. Invalid priority
        resp2 = self.client.post("/tasks", data={
            "csrf_token": csrf,
            "title": "Valid title",
            "priority": "CriticalUrgentMega",
        }, follow_redirects=True)
        self.assertIn("Priority must be Low, Medium, or High", resp2.data.decode("utf-8"))

        # 3. Invalid date format
        resp3 = self.client.post("/tasks", data={
            "csrf_token": csrf,
            "title": "Valid title 2",
            "due_date": "not-a-date",
        }, follow_redirects=True)
        self.assertIn("Due date must be a valid date in YYYY-MM-DD format", resp3.data.decode("utf-8"))

        # 4. Out-of-bounds year
        resp4 = self.client.post("/tasks", data={
            "csrf_token": csrf,
            "title": "Valid title 3",
            "due_date": "1850-01-01",
        }, follow_redirects=True)
        self.assertIn("Due date year must be between 2000 and 2100", resp4.data.decode("utf-8"))

    def test_edit_task_success_and_preserves_completion_state(self):
        """User can edit their task fields while preserving existing completion status."""
        today = local_today()
        task = Task(title="Original Task", priority="Low", user_id=self.user.id, completed=True)
        db.session.add(task)
        db.session.commit()

        csrf = self.get_csrf(f"/tasks/edit/{task.id}")
        new_due = (today + timedelta(days=5)).isoformat()

        # Submit edit WITHOUT completed field in post -> should preserve task.completed == True
        response = self.client.post(f"/tasks/edit/{task.id}", data={
            "csrf_token": csrf,
            "title": "Updated Task Title",
            "subject_id": str(self.subj_math.id),
            "priority": "High",
            "due_date": new_due,
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Task updated.", response.data.decode("utf-8"))

        updated = db.session.get(Task, task.id)
        self.assertEqual(updated.title, "Updated Task Title")
        self.assertEqual(updated.subject_id, self.subj_math.id)
        self.assertEqual(updated.priority, "High")
        self.assertEqual(updated.due_date.isoformat(), new_due)
        self.assertTrue(updated.completed, "Completion status must be preserved when not explicitly changed")

    def test_edit_task_explicit_completion_toggle(self):
        """User can uncheck completed box in edit form to revert task to pending."""
        task = Task(title="Done Task", priority="Medium", user_id=self.user.id, completed=True)
        db.session.add(task)
        db.session.commit()

        csrf = self.get_csrf(f"/tasks/edit/{task.id}")
        # Explicit completed=0 sent
        response = self.client.post(f"/tasks/edit/{task.id}", data={
            "csrf_token": csrf,
            "title": "Done Task",
            "priority": "Medium",
            "completed": "0",
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        updated = db.session.get(Task, task.id)
        self.assertFalse(updated.completed)

    def test_user_cannot_edit_or_delete_other_users_task(self):
        """Bob cannot edit, update, or delete Alice's task (strict 404 isolation)."""
        bob = self.create_user(name="Bob Hacker", email="bob_task@test.com", password="password123")
        bob_task = Task(title="Bob Private Task", user_id=bob.id, priority="High")
        db.session.add(bob_task)
        db.session.commit()

        # Maya is logged in, tries to access Bob's task
        get_resp = self.client.get(f"/tasks/edit/{bob_task.id}")
        self.assertEqual(get_resp.status_code, 404)

        csrf = self.get_csrf("/tasks")
        post_resp = self.client.post(f"/tasks/edit/{bob_task.id}", data={
            "csrf_token": csrf,
            "title": "Hacked Title",
        })
        self.assertEqual(post_resp.status_code, 404)

        del_resp = self.client.post(f"/tasks/delete/{bob_task.id}", data={"csrf_token": csrf})
        self.assertEqual(del_resp.status_code, 404)
        self.assertIsNotNone(db.session.get(Task, bob_task.id))

    def test_due_date_status_calculations(self):
        """Tasks are correctly categorized as overdue, due today, or upcoming."""
        today = local_today()

        t_overdue = Task(title="Overdue Task", due_date=today - timedelta(days=2), user_id=self.user.id, completed=False)
        t_today = Task(title="Today Task", due_date=today, user_id=self.user.id, completed=False)
        t_upcoming = Task(title="Upcoming Task", due_date=today + timedelta(days=4), user_id=self.user.id, completed=False)
        t_done_overdue = Task(title="Done Past Task", due_date=today - timedelta(days=5), user_id=self.user.id, completed=True)

        db.session.add_all([t_overdue, t_today, t_upcoming, t_done_overdue])
        db.session.commit()

        response = self.client.get("/tasks")
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")

        self.assertIn("badge-due-overdue", html)
        self.assertIn("Overdue (2d)", html)
        self.assertIn("Due today", html)
        self.assertIn("In 4d", html)
        # Completed task should NOT have overdue danger badge
        self.assertIn("badge-due-muted", html)

    def test_filtering_by_status_priority_and_overdue(self):
        """Tasks list filters correctly by status, priority, and overdue state."""
        today = local_today()

        t1 = Task(title="High Pending", priority="High", completed=False, user_id=self.user.id)
        t2 = Task(title="Low Pending", priority="Low", completed=False, user_id=self.user.id)
        t3 = Task(title="High Completed", priority="High", completed=True, user_id=self.user.id)
        t4 = Task(title="Overdue Item", priority="Medium", due_date=today - timedelta(days=1), completed=False, user_id=self.user.id)

        db.session.add_all([t1, t2, t3, t4])
        db.session.commit()

        # 1. Filter status=pending
        r1 = self.client.get("/tasks?status=pending")
        html1 = r1.data.decode("utf-8")
        self.assertIn("High Pending", html1)
        self.assertIn("Low Pending", html1)
        self.assertNotIn("High Completed", html1)

        # 2. Filter priority=High
        r2 = self.client.get("/tasks?priority=High")
        html2 = r2.data.decode("utf-8")
        self.assertIn("High Pending", html2)
        self.assertIn("High Completed", html2)
        self.assertNotIn("Low Pending", html2)

        # 3. Filter overdue=1
        r3 = self.client.get("/tasks?overdue=1")
        html3 = r3.data.decode("utf-8")
        self.assertIn("Overdue Item", html3)
        self.assertNotIn("High Pending", html3)

        # 4. Invalid filter values fallback gracefully
        r4 = self.client.get("/tasks?status=malformed&priority=unknown")
        self.assertEqual(r4.status_code, 200)

    def test_sorting_by_due_date_and_priority(self):
        """Tasks sort correctly by due date (nulls last) and priority (High -> Med -> Low)."""
        today = local_today()

        t_no_due = Task(title="Task No Due", due_date=None, priority="High", user_id=self.user.id)
        t_later = Task(title="Task Later", due_date=today + timedelta(days=10), priority="Low", user_id=self.user.id)
        t_soon = Task(title="Task Soon", due_date=today + timedelta(days=1), priority="Medium", user_id=self.user.id)

        db.session.add_all([t_no_due, t_later, t_soon])
        db.session.commit()

        # Sort by due_date: Task Soon -> Task Later -> Task No Due
        r_due = self.client.get("/tasks?sort=due_date")
        html_due = r_due.data.decode("utf-8")
        pos_soon = html_due.find("Task Soon")
        pos_later = html_due.find("Task Later")
        pos_nodue = html_due.find("Task No Due")
        self.assertTrue(pos_soon < pos_later < pos_nodue)

        # Sort by priority: High (Task No Due) -> Medium (Task Soon) -> Low (Task Later)
        r_prio = self.client.get("/tasks?sort=priority")
        html_prio = r_prio.data.decode("utf-8")
        pos_high = html_prio.find("Task No Due")
        pos_med = html_prio.find("Task Soon")
        pos_low = html_prio.find("Task Later")
        self.assertTrue(pos_high < pos_med < pos_low)

    def test_dashboard_open_tasks_integration(self):
        """Dashboard displays open tasks with priority tags, due indicators, and overdue badge."""
        today = local_today()

        t_overdue = Task(title="Urgent Homework", due_date=today - timedelta(days=1), priority="High", subject_id=self.subj_cs.id, user_id=self.user.id)
        t_normal = Task(title="Casual Reading", due_date=today + timedelta(days=4), priority="Low", user_id=self.user.id)
        db.session.add_all([t_overdue, t_normal])
        db.session.commit()

        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")

        self.assertIn("Urgent Homework", html)
        self.assertIn("Casual Reading", html)
        self.assertIn("prio-high", html)
        self.assertIn("1 overdue", html)

