"""Business rules for managing events."""

from functools import singledispatchmethod

from exceptions import NotFoundError
from models.event import Event


class EventService:
    """Create, read, update, delete and search events."""

    def __init__(self, repository):
        self._repository = repository

    def list_events(self):
        with self._repository.transaction() as database:
            return list(database.events)

    def list_categories(self):
        with self._repository.transaction() as database:
            return list(database.categories)

    @singledispatchmethod
    def get(self, reference):
        raise TypeError("Use an event id or an Event object.")

    @get.register
    def _(self, reference: str):
        with self._repository.transaction() as database:
            event = database.find_event(reference)
        if event is None:
            raise NotFoundError("Event not found.")
        return event

    @get.register
    def _(self, reference: Event):
        return self.get(reference.id)

    def search(self, text="", category="All"):
        text = text.strip().lower()
        results = []

        for event in self.list_events():
            if category not in ("All", "", None) and event.category != category:
                continue
            haystack = " ".join(
                [event.title, event.location, event.category, event.description]
            ).lower()
            if text in haystack:
                results.append(event)

        return sorted(results, key=lambda item: item.date)

    def create(self, title, date, time, location, capacity=1,
               category=None, description=None):
        event = Event.create(
            title, date, time, location, capacity, category, description
        )

        with self._repository.transaction(write=True) as database:
            database.events.append(event)
            database.add_category(event.category)

        return event

    def update(self, event_id, title, category, date, time, location,
               capacity, description):
        with self._repository.transaction(write=True) as database:
            event = database.find_event(event_id)
            if event is None:
                raise NotFoundError("Event not found.")

            old_category = event.category
            event.update_details(
                title, category, date, time, location, capacity,
                description, reserved=database.reserved_count(event_id),
            )

            database.add_category(event.category)
            if old_category != event.category:
                database.prune_category(old_category)

        return event

    def delete(self, event_id):
        with self._repository.transaction(write=True) as database:
            event = database.find_event(event_id)
            if event is None:
                raise NotFoundError("Event not found.")

            # Cascade delete: Alisin din ang mga rehistro na nakakabit sa event na ito
            database.registrations = [
                r for r in database.registrations if r.event_id != str(event_id)
            ]

            database.events.remove(event)
            database.prune_category(event.category)