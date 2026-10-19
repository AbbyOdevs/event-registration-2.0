"""Small reusable input-cleaning and validation helpers."""

import re
from datetime import datetime

from exceptions import ValidationError

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def clean_text(value):
    """Return ``value`` as a stripped string (``None`` becomes '')."""
    return "" if value is None else str(value).strip()


def parse_capacity(value):
    """Convert ``value`` to a capacity of at least 1 or raise ValidationError."""
    try:
        capacity = int(value)
    except (ValueError, TypeError):
        raise ValidationError("Capacity must be a whole number.")

    if capacity < 1:
        raise ValidationError("Capacity must be at least 1.")

    return capacity


def parse_quantity(value):
    """Convert ``value`` to a whole number of spots (at least 1)."""
    try:
        quantity = int(value)
    except (ValueError, TypeError):
        raise ValidationError("Number of spots must be a whole number.")

    if quantity < 1:
        raise ValidationError("Reserve at least one spot.")

    return quantity


def parse_date(value):
    """Parse an ISO ``YYYY-MM-DD`` string into a ``date``."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise ValidationError("Enter a valid date (YYYY-MM-DD).")


def check_time(value):
    """Make sure ``value`` looks like ``HH:MM`` or ``HH:MM:SS``."""
    for pattern in ("%H:%M", "%H:%M:%S"):
        try:
            datetime.strptime(value, pattern)
            return value
        except (ValueError, TypeError):
            continue

    raise ValidationError("Enter a valid time (HH:MM).")
