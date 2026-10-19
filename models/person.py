"""People who use the system: participants and the administrator."""

import hmac
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from exceptions import ValidationError
from models.base import Entity
from validation import EMAIL_RE, clean_text


class Person(Entity, ABC):
    """Abstract user account (inheritance: Participant and Admin extend it)."""

    def __init__(self, name, email, student_id="", entity_id=None):
        super().__init__(entity_id)
        self._name = ""
        self._email = ""
        self._student_id = ""
        self.name = name
        self.email = email
        self.student_id = student_id

    # ----- encapsulated attributes with validation -----

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        value = clean_text(value)
        if len(value) > 100:
            raise ValidationError("Name is too long.")
        self._name = value

    @property
    def email(self):
        return self._email

    @email.setter
    def email(self, value):
        value = clean_text(value).lower()
        if value and (not EMAIL_RE.fullmatch(value) or len(value) > 254):
            raise ValidationError("Enter a valid email address.")
        self._email = value

    @property
    def student_id(self):
        return self._student_id

    @student_id.setter
    def student_id(self, value):
        value = clean_text(value)
        if len(value) > 50:
            raise ValidationError("Student ID is too long.")
        self._student_id = value

    @property
    @abstractmethod
    def role(self):
        """Role name used for permissions ('participant' or 'admin')."""

    @abstractmethod
    def check_password(self, raw_password):
        """Return True when ``raw_password`` belongs to this account."""

    def to_public_dict(self):
        """Account fields that are safe to send to the browser."""
        return {
            "id": self.id,
            "student_id": self.student_id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "createdAt": getattr(self, "created_at", None),
        }

    def describe(self):
        return f"{self.role.title()} {self.name} <{self.email}>"


class Participant(Person):
    """A student who can reserve spots for events."""

    ID_PREFIX = "usr"
    ID_LENGTH = 12
    MIN_PASSWORD = 8
    MAX_PASSWORD = 128

    def __init__(self, name, email, student_id, password_hash="",
                 created_at=None, entity_id=None):
        super().__init__(name, email, student_id, entity_id)
        self._password_hash = password_hash or ""
        self.created_at = created_at

    @property
    def role(self):
        return "participant"

    @classmethod
    def create(cls, student_id, name, email, password):
        """Factory used at sign up: validates and hashes the password."""
        participant = cls(
            name=name,
            email=email,
            student_id=student_id,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        participant.set_password(password)
        return participant

    def set_password(self, raw_password):
        if not isinstance(raw_password, str) or len(raw_password) < self.MIN_PASSWORD:
            raise ValidationError(
                "Password must contain at least 8 characters."
            )
        if len(raw_password) > self.MAX_PASSWORD:
            raise ValidationError("Password is too long.")
        self._password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        if not isinstance(raw_password, str) or not self._password_hash:
            return False
        return check_password_hash(self._password_hash, raw_password)

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "name": self.name,
            "email": self.email,
            "passwordHash": self._password_hash,
            "createdAt": self.created_at,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data.get("name", ""),
            email=data.get("email", ""),
            student_id=data.get("student_id", data.get("studentId", "")),
            password_hash=data.get("passwordHash", ""),
            created_at=data.get("createdAt"),
            entity_id=data.get("id"),
        )


class Admin(Person):
    """The single administrator whose credentials come from configuration."""

    def __init__(self, email, password):
        super().__init__(name="Administrator", email=email, entity_id="admin")
        self._password = password

    @property
    def role(self):
        return "admin"

    def check_password(self, raw_password):
        if not isinstance(raw_password, str):
            return False
        return hmac.compare_digest(
            raw_password.encode("utf-8"), self._password.encode("utf-8")
        )

    def to_public_dict(self):
        return {"email": self.email, "role": self.role}

    def to_dict(self):
        # The administrator is never written to the data file.
        return {"email": self.email, "role": self.role}

    @classmethod
    def from_dict(cls, data):
        raise NotImplementedError("The administrator is configured, not stored.")
