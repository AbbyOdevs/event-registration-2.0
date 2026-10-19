"""Custom exception hierarchy for the Event Registration System."""


class EventSystemError(Exception):
    """Base class for all application-specific errors."""

    status_code = 400

    def __init__(self, message=None):
        super().__init__(message or self.default_message())
        self.message = message or self.default_message()

    @classmethod
    def default_message(cls):
        return "Please check your input and try again."


class ValidationError(EventSystemError):
    """Raised for empty fields, invalid input or wrong data types."""

    status_code = 400


class AuthenticationError(EventSystemError):
    """Raised when a user is not logged in or the credentials are wrong."""

    status_code = 401


class PermissionDeniedError(EventSystemError):
    """Raised when a logged-in user is not allowed to do something."""

    status_code = 403


class NotFoundError(EventSystemError):
    """Raised when a requested record does not exist."""

    status_code = 404


class ConflictError(EventSystemError):
    """Raised when an action conflicts with existing data."""

    status_code = 409


class DuplicateAccountError(ConflictError):
    """Raised when an email or Student ID is already registered."""

    @classmethod
    def default_message(cls):
        return "An account with this email or Student ID already exists."


class DuplicateRegistrationError(ConflictError):
    """Raised when a participant reserves the same event twice."""

    @classmethod
    def default_message(cls):
        return "You have already registered for this event."


class EventFullError(EventSystemError):
    """Raised when a reservation asks for more spots than are left."""

    status_code = 400

    def __init__(self, available):
        spots = max(int(available), 0)
        super().__init__(f"Only {spots} spot(s) remaining for this event.")
        self.available = spots


class StorageError(EventSystemError):
    """Raised when the data file cannot be read or written."""

    status_code = 500

    @classmethod
    def default_message(cls):
        return "The system could not access the database file. Please try again later."