"""In-memory snapshot of everything stored in the data file."""

from models.event import Event
from models.person import Participant
from models.registration import Registration


class Database:
    """Aggregate that owns all users, events, registrations and categories."""

    def __init__(self, users=None, events=None, registrations=None,
                 categories=None):
        self.users = list(users or [])
        self.events = list(events or [])
        self.registrations = list(registrations or [])
        self.categories = list(categories or [])
        self._sync_categories()
        self.recount()

    # ----- lookups -----

    def find_event(self, event_id):
        return next((e for e in self.events if e.id == str(event_id)), None)

    def find_user(self, user_id):
        return next((u for u in self.users if u.id == str(user_id)), None)

    def find_user_by_email(self, email):
        email = str(email).strip().lower()
        return next((u for u in self.users if u.email == email), None)

    def find_user_by_student_id(self, student_id):
        wanted = str(student_id).strip().casefold()
        return next(
            (u for u in self.users if u.student_id.casefold() == wanted),
            None,
        )

    def find_registration(self, registration_id):
        return next(
            (r for r in self.registrations if r.id == str(registration_id)),
            None,
        )

    def registrations_for_event(self, event_id):
        return [r for r in self.registrations if r.event_id == str(event_id)]

    def registrations_for_user(self, user_id):
        return [r for r in self.registrations if r.belongs_to(user_id)]

    def reserved_count(self, event_id):
        return sum(r.quantity for r in self.registrations_for_event(event_id))

    # ----- consistency helpers -----

    def recount(self):
        """Recalculate every event's reserved spots from the registrations."""
        for event in self.events:
            event.sync_registered(self.reserved_count(event.id))

    def _sync_categories(self):
        for event in self.events:
            if event.category not in self.categories:
                self.categories.append(event.category)

    def add_category(self, category):
        if category not in self.categories:
            self.categories.append(category)

    def prune_category(self, category):
        """Remove ``category`` when no event uses it any more."""
        if not any(e.category == category for e in self.events):
            self.categories = [c for c in self.categories if c != category]

    # ----- conversion to and from the data file -----

    def to_dict(self):
        return {
            "events": [e.to_dict() for e in self.events],
            "categories": list(self.categories),
            "registrations": [r.to_dict() for r in self.registrations],
            "users": [u.to_dict() for u in self.users],
        }

    @classmethod
    def from_dict(cls, data):
        """Build a database, upgrading records saved by older versions."""
        data = data if isinstance(data, dict) else {}

        def records(key, legacy_key=None):
            items = data.get(key)
            if not isinstance(items, list) and legacy_key:
                items = data.get(legacy_key)
            return [i for i in (items or []) if isinstance(i, dict)]

        categories = data.get("categories")
        categories = categories if isinstance(categories, list) else []

        return cls(
            users=[Participant.from_dict(i) for i in records("users")],
            events=[Event.from_dict(i) for i in records("events")],
            registrations=[
                Registration.from_dict(i)
                for i in records("registrations", legacy_key="tickets")
            ],
            categories=categories,
        )