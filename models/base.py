"""Abstract base class shared by every stored record."""

import uuid
from abc import ABC, abstractmethod


class Entity(ABC):
    """Base class (abstraction) for anything saved in the database.

    Subclasses must say how they turn into a dictionary (``to_dict``), how
    they are rebuilt from one (``from_dict``) and how they describe
    themselves in words (``describe``).  Code that works with an ``Entity``
    does not need to know which concrete class it holds (polymorphism).
    """

    ID_PREFIX = "ent"
    ID_LENGTH = 10

    def __init__(self, entity_id=None):
        # Encapsulation: the id is private and exposed read-only.
        self._id = str(entity_id) if entity_id else self.generate_id()

    @classmethod
    def generate_id(cls):
        return cls.ID_PREFIX + uuid.uuid4().hex[: cls.ID_LENGTH]

    @property
    def id(self):
        return self._id

    @abstractmethod
    def to_dict(self):
        """Return the record as a JSON-friendly dictionary."""

    @classmethod
    @abstractmethod
    def from_dict(cls, data):
        """Rebuild a record from a dictionary read from the data file."""

    @abstractmethod
    def describe(self):
        """Return a short human-readable description."""

    def __eq__(self, other):
        return type(self) is type(other) and self._id == other._id

    def __hash__(self):
        return hash((type(self).__name__, self._id))

    def __repr__(self):
        return f"<{type(self).__name__} {self._id}>"
