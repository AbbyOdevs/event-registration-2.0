"""Business rules for reservations and attendance."""

from exceptions import (
    AuthenticationError,
    DuplicateRegistrationError,
    EventFullError,
    NotFoundError,
)
from models.registration import Registration
from validation import parse_quantity


class RegistrationService:
    """Reserve spots, cancel reservations and record attendance."""

    def __init__(self, repository):
        self._repository = repository

    def reserve(self, user_id, event_id, quantity=1):
        quantity = parse_quantity(quantity)

        with self._repository.transaction(write=True) as database:
            participant = database.find_user(user_id)
            if participant is None:
                raise AuthenticationError(
                    "Account not found. Please log in again."
                )

            event = database.find_event(event_id)
            if event is None:
                raise NotFoundError("Event not found.")

            if any(
                r.belongs_to(user_id)
                for r in database.registrations_for_event(event_id)
            ):
                raise DuplicateRegistrationError()

            available = event.available_spots(database.reserved_count(event_id))
            if quantity > available:
                raise EventFullError(available)

            registration = Registration.for_participant(
                event, participant, quantity
            )
            database.registrations.append(registration)

        return registration

    def list_for_user(self, user_id):
        with self._repository.transaction() as database:
            return database.registrations_for_user(user_id)

    def list_all(self):
        with self._repository.transaction() as database:
            return list(database.registrations)

    def cancel(self, user_id, registration_id):
        with self._repository.transaction(write=True) as database:
            registration = database.find_registration(registration_id)

            if registration is None or not registration.belongs_to(user_id):
                raise NotFoundError("Registration not found.")

            registration.ensure_cancellable()
            database.registrations.remove(registration)

    def set_attendance(self, registration_id, status):
        with self._repository.transaction(write=True) as database:
            registration = database.find_registration(registration_id)
            if registration is None:
                raise NotFoundError("Registration not found.")

            registration.mark(status)

        return registration
