"""The Registration record (one participant's reservation for one event)."""

from datetime import datetime, timezone

from exceptions import ValidationError
from models.base import Entity
from validation import parse_quantity


class Registration(Entity):
    """A reservation of one or more spots made by a participant."""

    ID_PREFIX = "reg"

    REGISTERED = "registered"
    ATTENDED = "attended"
    ABSENT = "absent"
    STATUSES = (REGISTERED, ATTENDED, ABSENT)

    def __init__(self, event_id, event_title, owner, student_id, name, email,
                 quantity=1, attendance_status=REGISTERED,
                 registered_at=None, entity_id=None):
        super().__init__(entity_id)
        self.event_id = str(event_id)
        self.event_title = event_title
        self.owner = str(owner)
        self.student_id = student_id
        self.name = name
        self.email = email
        self._quantity = 1
        self._attendance_status = self.REGISTERED

        self.quantity = quantity
        self.attendance_status = attendance_status
        self.registered_at = (
            registered_at or datetime.now(timezone.utc).isoformat()
        )

    @classmethod
    def for_participant(cls, event, participant, quantity):
        """Create a registration for ``participant`` on ``event``."""
        return cls(
            event_id=event.id,
            event_title=event.title,
            owner=participant.id,
            student_id=participant.student_id,
            name=participant.name,
            email=participant.email,
            quantity=quantity,
        )

    @property
    def quantity(self):
        return self._quantity

    @quantity.setter
    def quantity(self, value):
        self._quantity = parse_quantity(value)

    @property
    def attendance_status(self):
        return self._attendance_status

    @attendance_status.setter
    def attendance_status(self, value):
        if value not in self.STATUSES:
            raise ValidationError("Invalid attendance status.")
        self._attendance_status = value

    def mark(self, status):
        """Record attendance (registered, attended or absent)."""
        self.attendance_status = status

    def ensure_cancellable(self):
        if self._attendance_status == self.ATTENDED:
            raise ValidationError(
                "An attended registration cannot be cancelled."
            )
        if self._attendance_status == self.ABSENT:
            raise ValidationError(
                "An absent registration cannot be cancelled."
            )

    def belongs_to(self, user_id):
        return self.owner == str(user_id)

    # ----- Entity contract -----

    def to_dict(self):
        return {
            "id": self.id,
            "eventId": self.event_id,
            "eventTitle": self.event_title,
            "student_id": self.student_id,
            "name": self.name,
            "email": self.email,
            "quantity": self._quantity,
            "owner": self.owner,
            "attendanceStatus": self._attendance_status,
            "registeredAt": self.registered_at,
        }

    @classmethod
    def from_dict(cls, data):
        try:
            quantity = parse_quantity(data.get("quantity", 1))
        except ValidationError:
            quantity = 1

        status = data.get("attendanceStatus", cls.REGISTERED)
        if status not in cls.STATUSES:
            status = cls.REGISTERED

        return cls(
            event_id=data.get("eventId", ""),
            event_title=data.get("eventTitle", ""),
            owner=data.get("owner", ""),
            student_id=data.get("student_id", data.get("studentId", "")),
            name=data.get("name", ""),
            email=data.get("email", ""),
            quantity=quantity,
            attendance_status=status,
            registered_at=data.get("registeredAt"),
            entity_id=data.get("id"),
        )

    def describe(self):
        return (
            f"{self.name} reserved {self._quantity} spot(s) for "
            f"{self.event_title} [{self._attendance_status}]"
        )