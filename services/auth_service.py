"""Business rules for accounts and logging in."""

from exceptions import (
    AuthenticationError,
    ConflictError,
    DuplicateAccountError,
    PermissionDeniedError,
    ValidationError,
)
from models.person import Admin, Participant
from validation import clean_text


class AuthService:
    """Sign up and login for participants, login for the administrator."""

    def __init__(self, repository, admin):
        self._repository = repository
        self._admin = admin

    @property
    def admin(self):
        return self._admin

    def register(self, student_id, name, email, password):
        student_id = clean_text(student_id)
        name = clean_text(name)
        email = clean_text(email).lower()

        if not all([student_id, name, email, password]):
            raise ValidationError(
                "Student ID, name, email, and password are required."
            )

        if email == self._admin.email:
            raise ConflictError("This email address is reserved for the administrator.")

        participant = Participant.create(student_id, name, email, password)

        with self._repository.transaction(write=True) as database:
            if database.find_user_by_email(email):
                raise DuplicateAccountError(
                    "An account with this email address already exists."
                )
            if database.find_user_by_student_id(student_id):
                raise DuplicateAccountError(
                    "This Student ID is already registered."
                )
            database.users.append(participant)

        return participant

    def login(self, email, password):
        email = clean_text(email).lower()

        if not email or not isinstance(password, str) or not password:
            raise ValidationError("Email and password are required.")

        if email == self._admin.email:
            raise PermissionDeniedError("Please use the administrator login page.")

        with self._repository.transaction() as database:
            user = database.find_user_by_email(email)

        if user is None or not user.check_password(password):
            raise AuthenticationError("Invalid email address or password.")

        return user

    def admin_login(self, email, password):
        if (
            clean_text(email).lower() != self._admin.email
            or not self._admin.check_password(password)
        ):
            raise AuthenticationError("Invalid administrator credentials.")
        return self._admin

    def verify_admin_password(self, password):
        if not self._admin.check_password(password):
            raise AuthenticationError("Incorrect administrator password.")
        return self._admin

    def get_participant(self, user_id):
        with self._repository.transaction() as database:
            return database.find_user(user_id)

    def list_participants(self):
        with self._repository.transaction() as database:
            return list(database.users)