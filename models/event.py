"""The Event record."""

from datetime import date as date_type

from exceptions import ConflictError, ValidationError
from models.base import Entity
from validation import (
    check_time,
    clean_text,
    parse_capacity,
    parse_date,
)


class Event(Entity):
    """An event that participants can register for."""

    ID_PREFIX = "ev"
    DEFAULT_CATEGORY = "Meetup"
    DEFAULT_DESCRIPTION = "Details coming soon."

    def __init__(self, title, date, time, location, capacity=1,
                 category=DEFAULT_CATEGORY, description=DEFAULT_DESCRIPTION,
                 registered=0, entity_id=None):
        super().__init__(entity_id)
        self._title = ""
        self._date = ""
        self._time = ""
        self._location = ""
        self._capacity = 1
        self._category = self.DEFAULT_CATEGORY
        self._description = ""
        self._registered = 0

        self.title = title
        self.date = date
        self.time = time
        self.location = location
        self.capacity = capacity
        self.category = category
        self.description = description
        self._registered = max(0, int(registered or 0))

    @classmethod
    def create(cls, title, date, time, location, capacity=1,
               category=None, description=None):
        title, date, time, location = (
            clean_text(title), clean_text(date),
            clean_text(time), clean_text(location),
        )
        if not all([title, date, time, location]):
            raise ValidationError(
                "Title, date, time, and location are required."
            )

        event = cls(
            title=title,
            date=date,
            time=time,
            location=location,
            capacity=parse_capacity(capacity),
            category=clean_text(category) or cls.DEFAULT_CATEGORY,
            description=(
                cls.DEFAULT_DESCRIPTION if description is None
                else clean_text(description)
            ),
        )
        event.ensure_not_in_past()
        return event

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, value):
        value = clean_text(value)
        if len(value) > 150:
            raise ValidationError("Title or location is too long.")
        self._title = value

    @property
    def location(self):
        return self._location

    @location.setter
    def location(self, value):
        value = clean_text(value)
        if len(value) > 200:
            raise ValidationError("Title or location is too long.")
        self._location = value

    @property
    def date(self):
        return self._date

    @date.setter
    def date(self, value):
        value = clean_text(value)
        if value:
            parse_date(value)
        self._date = value

    @property
    def time(self):
        return self._time

    @time.setter
    def time(self, value):
        value = clean_text(value)
        if value:
            check_time(value)
        self._time = value

    @property
    def capacity(self):
        return self._capacity

    @capacity.setter
    def capacity(self, value):
        self._capacity = parse_capacity(value)

    @property
    def category(self):
        return self._category

    @category.setter
    def category(self, value):
        cleaned = clean_text(value)
        if not cleaned:
            self._category = self.DEFAULT_CATEGORY
        else:
            # Ginagawa nitong malinis ang pormat (hal. "meet up" o "MEET UP" ay magiging "Meet up")
            self._category = cleaned.strip().title()

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, value):
        self._description = clean_text(value)

    @property
    def registered(self):
        return self._registered

    def sync_registered(self, reserved):
        self._registered = max(0, int(reserved))

    def available_spots(self, reserved=None):
        reserved = self._registered if reserved is None else reserved
        return self._capacity - reserved

    def is_full(self):
        return self.available_spots() <= 0

    def ensure_not_in_past(self):
        if self._date and parse_date(self._date) < date_type.today():
            raise ValidationError("The event date cannot be in the past.")

    def update_details(self, title, category, date, time, location,
                       capacity, description, reserved=0):
        title, category, date, time, location = (
            clean_text(title), clean_text(category), clean_text(date),
            clean_text(time), clean_text(location),
        )
        if not all([title, category, date, time, location]):
            raise ValidationError(
                "Title, category, date, time, and location are required."
            )

        new_capacity = parse_capacity(capacity)
        if new_capacity < reserved:
            raise ValidationError(
                f"Capacity cannot be less than the {reserved} "
                f"currently reserved spots."
            )

        date_changed = date != self._date

        self.title = title
        self.category = category
        self.date = date
        self.time = time
        self.location = location
        self._capacity = new_capacity
        self.description = description
        self._registered = reserved

        if date_changed:
            self.ensure_not_in_past()

    def ensure_deletable(self, has_registrations):
        if has_registrations:
            raise ConflictError(
                "Cannot delete this event because there are participants "
                "already registered."
            )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self._title,
            "category": self._category,
            "date": self._date,
            "time": self._time,
            "location": self._location,
            "capacity": self._capacity,
            "registered": self._registered,
            "description": self._description,
        }

    @classmethod
    def from_dict(cls, data):
        try:
            capacity = parse_capacity(data.get("capacity", 1))
        except ValidationError:
            capacity = 1

        return cls(
            title=data.get("title", ""),
            date=data.get("date", ""),
            time=data.get("time", ""),
            location=data.get("location", ""),
            capacity=capacity,
            category=data.get("category") or cls.DEFAULT_CATEGORY,
            description=data.get("description", ""),
            registered=data.get("registered", 0),
            entity_id=data.get("id"),
        )

    def describe(self):
        return (
            f"{self._title} ({self._category}) on {self._date} at "
            f"{self._time}, {self._location} - "
            f"{self._registered}/{self._capacity} reserved"
        )