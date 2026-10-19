"""Automated tests for the Event Registration System.

Run with:  python -m unittest discover -s tests -v
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402
from config import Config  # noqa: E402
from exceptions import (  # noqa: E402
    DuplicateRegistrationError, EventFullError, EventSystemError,
    StorageError, ValidationError,
)
from models import Admin, Event, Participant, Registration  # noqa: E402
from repository import JsonRepository, Repository  # noqa: E402

FUTURE = (date.today() + timedelta(days=30)).isoformat()
PAST = (date.today() - timedelta(days=3)).isoformat()


class BaseCase(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.data_file = os.path.join(self.folder, "data.json")
        config = Config()
        config.data_file = self.data_file
        config.admin_email = "admin@test.local"
        config.admin_password = "secret-admin"
        self.app = create_app(config)
        self.client = self.app.test_client()

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def signup(self, client=None, **overrides):
        payload = {
            "student_id": "0001", "name": "Test Student",
            "email": "student@test.com", "password": "password123",
        }
        payload.update(overrides)
        return (client or self.client).post("/api/auth/register", json=payload)

    def admin_client(self):
        client = self.app.test_client()
        response = client.post("/api/auth/admin-login", json={
            "email": "admin@test.local", "password": "secret-admin"})
        self.assertEqual(response.status_code, 200)
        return client

    def make_event(self, admin, **overrides):
        payload = {
            "title": "Tech Talk", "category": "Seminar", "date": FUTURE,
            "time": "09:00", "location": "Room 1", "capacity": 5,
            "description": "Hello",
        }
        payload.update(overrides)
        return admin.post("/api/events", json=payload)


class ModelTests(unittest.TestCase):
    def test_participant_encapsulation_and_hashing(self):
        user = Participant.create("1", "Ana", "ANA@mail.com", "password123")
        self.assertEqual(user.email, "ana@mail.com")
        self.assertTrue(user.check_password("password123"))
        self.assertFalse(user.check_password("wrong"))
        self.assertNotIn("passwordHash", user.to_public_dict())
        self.assertNotEqual(user.to_dict()["passwordHash"], "password123")

    def test_polymorphism_describe(self):
        admin = Admin("a@b.com", "x")
        user = Participant.create("1", "Ana", "ana@mail.com", "password123")
        event = Event.create("Party", FUTURE, "10:00", "Hall", 5)
        for item in (admin, user, event):
            self.assertIsInstance(item.describe(), str)
        self.assertEqual(admin.role, "admin")
        self.assertEqual(user.role, "participant")

    def test_event_rules(self):
        with self.assertRaises(ValidationError):
            Event.create("", FUTURE, "10:00", "Hall", 5)
        with self.assertRaises(ValidationError):
            Event.create("Old", PAST, "10:00", "Hall", 5)
        with self.assertRaises(ValidationError):
            Event.create("Bad", FUTURE, "10:00", "Hall", "abc")
        with self.assertRaises(ValidationError):
            Event.create("Bad", FUTURE, "10:00", "Hall", 0)
        with self.assertRaises(ValidationError):
            Event.create("Bad", "not-a-date", "10:00", "Hall", 3)

    def test_registration_status_and_cancel_rules(self):
        reg = Registration("e1", "Party", "u1", "1", "Ana", "a@b.com", 1)
        reg.mark(Registration.ATTENDED)
        with self.assertRaises(ValidationError):
            reg.ensure_cancellable()
        with self.assertRaises(ValidationError):
            reg.mark("late")

    def test_repository_is_abstract(self):
        with self.assertRaises(TypeError):
            Repository()


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.path = os.path.join(self.folder, "data.json")

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def test_missing_file_gives_empty_database(self):
        db = JsonRepository(self.path).load()
        self.assertEqual(db.events, [])

    def test_damaged_file_raises_storage_error(self):
        with open(self.path, "w") as file:
            file.write("{ not json")
        with self.assertRaises(StorageError):
            JsonRepository(self.path).load()

    def test_failed_transaction_does_not_save(self):
        repo = JsonRepository(self.path)
        with self.assertRaises(RuntimeError):
            with repo.transaction(write=True) as db:
                db.events.append(Event.create("X", FUTURE, "10:00", "Hall", 2))
                raise RuntimeError("boom")
        self.assertFalse(os.path.exists(self.path))

    def test_legacy_data_is_migrated(self):
        legacy = {
            "events": [{"id": "e1", "title": "Old", "date": "2026-12-29",
                        "time": "20:00", "location": "AC", "price": 50}],
            "tickets": [{"id": "t1", "eventId": "e1", "eventTitle": "Old",
                         "owner": "u1", "name": "A", "email": "a@b.com",
                         "code": "XYZ", "total": 50, "quantity": 2}],
            "users": [{"name": "Ana", "email": "ana@b.com", "studentId": "9"}],
        }
        with open(self.path, "w") as file:
            json.dump(legacy, file)
        db = JsonRepository(self.path).load()
        self.assertEqual(db.events[0].registered, 2)
        self.assertEqual(db.users[0].student_id, "9")
        self.assertTrue(db.users[0].id.startswith("usr"))
        with open(self.path) as handle:
            saved = json.load(handle)
        self.assertIn("registrations", saved)
        self.assertNotIn("tickets", saved)
        self.assertNotIn("price", saved["events"][0])


class AuthApiTests(BaseCase):
    def test_signup_login_logout(self):
        self.assertEqual(self.signup().status_code, 201)
        self.client.post("/api/auth/logout")
        me = self.client.get("/api/auth/me").get_json()
        self.assertFalse(me["authenticated"])
        ok = self.client.post("/api/auth/login", json={
            "email": "student@test.com", "password": "password123"})
        self.assertEqual(ok.status_code, 200)
        self.assertTrue(self.client.get("/api/auth/me").get_json()["authenticated"])

    def test_signup_validation(self):
        self.assertEqual(self.signup(name="").status_code, 400)
        self.assertEqual(self.signup(email="bad").status_code, 400)
        self.assertEqual(self.signup(password="short").status_code, 400)
        self.assertEqual(self.signup(email="admin@test.local").status_code, 409)

    def test_duplicates_rejected(self):
        self.signup()
        again = self.signup(student_id="0002")
        self.assertEqual(again.status_code, 409)
        again = self.signup(email="other@test.com", student_id="0001")
        self.assertEqual(again.status_code, 409)

    def test_wrong_password_and_admin_email(self):
        self.signup()
        bad = self.client.post("/api/auth/login", json={
            "email": "student@test.com", "password": "nope"})
        self.assertEqual(bad.status_code, 401)
        blocked = self.client.post("/api/auth/login", json={
            "email": "admin@test.local", "password": "secret-admin"})
        self.assertEqual(blocked.status_code, 403)

    def test_admin_login_and_permissions(self):
        bad = self.client.post("/api/auth/admin-login", json={
            "email": "admin@test.local", "password": "wrong"})
        self.assertEqual(bad.status_code, 401)
        self.assertEqual(self.client.get("/api/admin/users").status_code, 403)
        self.assertEqual(self.client.post("/api/events", json={}).status_code, 403)
        self.assertEqual(self.client.get("/api/my-registrations").status_code, 401)

    def test_password_hash_never_exposed(self):
        self.signup()
        admin = self.admin_client()
        text = admin.get("/api/admin/users").get_data(as_text=True)
        self.assertNotIn("passwordHash", text)


class EventApiTests(BaseCase):
    def test_create_edit_delete_and_categories(self):
        admin = self.admin_client()
        created = self.make_event(admin)
        self.assertEqual(created.status_code, 201)
        event_id = created.get_json()["id"]
        self.assertIn("Seminar", self.client.get("/api/categories").get_json())

        updated = admin.put(f"/api/events/{event_id}", json={
            "title": "Renamed", "category": "Workshop", "date": FUTURE,
            "time": "10:00", "location": "Lab", "capacity": 8,
            "description": "x"})
        self.assertEqual(updated.status_code, 200)
        cats = self.client.get("/api/categories").get_json()
        self.assertIn("Workshop", cats)
        self.assertNotIn("Seminar", cats)

        self.assertEqual(admin.delete(f"/api/events/{event_id}").status_code, 200)
        self.assertEqual(self.client.get("/api/events").get_json(), [])

    def test_event_input_errors(self):
        admin = self.admin_client()
        self.assertEqual(self.make_event(admin, title="").status_code, 400)
        self.assertEqual(self.make_event(admin, capacity="abc").status_code, 400)
        self.assertEqual(self.make_event(admin, capacity=0).status_code, 400)
        self.assertEqual(self.make_event(admin, date=PAST).status_code, 400)
        self.assertEqual(admin.put("/api/events/nope", json={
            "title": "a", "category": "b", "date": FUTURE, "time": "10:00",
            "location": "c", "capacity": 1}).status_code, 404)

    def test_cannot_lower_capacity_or_delete_with_registrations(self):
        admin = self.admin_client()
        event_id = self.make_event(admin, capacity=5).get_json()["id"]
        self.signup()
        self.client.post(f"/api/events/{event_id}/register", json={"quantity": 3})
        low = admin.put(f"/api/events/{event_id}", json={
            "title": "T", "category": "C", "date": FUTURE, "time": "10:00",
            "location": "L", "capacity": 2, "description": ""})
        self.assertEqual(low.status_code, 400)
        self.assertEqual(admin.delete(f"/api/events/{event_id}").status_code, 409)


class RegistrationApiTests(BaseCase):
    def setUp(self):
        super().setUp()
        self.admin = self.admin_client()
        self.event_id = self.make_event(self.admin, capacity=3).get_json()["id"]
        self.signup()

    def reserve(self, quantity=1, client=None):
        return (client or self.client).post(
            f"/api/events/{self.event_id}/register", json={"quantity": quantity})

    def test_reserve_updates_count(self):
        self.assertEqual(self.reserve(2).status_code, 201)
        events = self.client.get("/api/events").get_json()
        self.assertEqual(events[0]["registered"], 2)
        mine = self.client.get("/api/my-registrations").get_json()
        self.assertEqual(len(mine), 1)

    def test_duplicate_and_overbooking_blocked(self):
        self.assertEqual(self.reserve(1).status_code, 201)
        self.assertEqual(self.reserve(1).status_code, 409)
        other = self.app.test_client()
        self.signup(client=other, student_id="0002", email="b@test.com")
        full = self.reserve(3, client=other)
        self.assertEqual(full.status_code, 400)
        self.assertIn("Only 2 spots", full.get_json()["error"])

    def test_invalid_quantity(self):
        self.assertEqual(self.reserve(0).status_code, 400)
        self.assertEqual(self.reserve("x").status_code, 400)

    def test_cancel_frees_spots(self):
        reg_id = self.reserve(2).get_json()["registration"]["id"]
        self.assertEqual(self.client.post(
            f"/api/registrations/{reg_id}/cancel").status_code, 200)
        self.assertEqual(self.client.get("/api/events").get_json()[0]["registered"], 0)

    def test_cannot_cancel_someone_elses(self):
        reg_id = self.reserve(1).get_json()["registration"]["id"]
        other = self.app.test_client()
        self.signup(client=other, student_id="0002", email="b@test.com")
        self.assertEqual(other.post(
            f"/api/registrations/{reg_id}/cancel").status_code, 404)

    def test_attendance_flow(self):
        reg_id = self.reserve(1).get_json()["registration"]["id"]
        url = f"/api/admin/registrations/{reg_id}/attendance"
        self.assertEqual(self.admin.post(url, json={"status": "bogus"}).status_code, 400)
        self.assertEqual(self.admin.post(url, json={"status": "attended"}).status_code, 200)
        self.assertEqual(self.client.post(
            f"/api/registrations/{reg_id}/cancel").status_code, 400)
        self.assertEqual(self.client.post(url, json={"status": "absent"}).status_code, 403)


class ExceptionTests(unittest.TestCase):
    def test_custom_exceptions(self):
        self.assertTrue(issubclass(EventFullError, EventSystemError))
        self.assertEqual(EventFullError(2).message, "Only 2 spots are available.")
        self.assertEqual(DuplicateRegistrationError().status_code, 409)


if __name__ == "__main__":
    unittest.main(verbosity=2)
