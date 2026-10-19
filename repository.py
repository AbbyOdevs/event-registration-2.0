"""Data access layer: an abstract repository and its JSON-file version."""

import json
import os
import threading
from abc import ABC, abstractmethod
from contextlib import contextmanager

from exceptions import StorageError
from models.database import Database


class Repository(ABC):
    """Abstract storage (abstraction).

    Services only talk to this interface, so the JSON file could later be
    replaced with a real database without touching the business rules.
    """

    def __init__(self):
        self._lock = threading.RLock()

    @abstractmethod
    def load(self):
        """Return the stored data as a ``Database``."""

    @abstractmethod
    def save(self, database):
        """Persist ``database``."""

    @contextmanager
    def transaction(self, write=False):
        """Load the data under a lock and save it again when ``write`` is set.

        If the block raises an exception nothing is saved, so a failed
        request can never leave half-finished changes in the file.
        """
        with self._lock:
            database = self.load()
            yield database

            if write:
                database.recount()
                self.save(database)


class JsonRepository(Repository):
    """Stores the whole database in one JSON file."""

    def __init__(self, path):
        super().__init__()
        self._path = path

    @property
    def path(self):
        return self._path

    def load(self):
        if not os.path.exists(self._path):
            return Database()

        try:
            with open(self._path, "r", encoding="utf-8") as file:
                raw = json.load(file)
        except json.JSONDecodeError:
            raise StorageError(
                "The data file is damaged and cannot be read. "
                "Restore it from a backup or delete it to start fresh."
            )
        except OSError as error:
            raise StorageError(f"The data file could not be opened: {error}")

        if not isinstance(raw, dict):
            raise StorageError("The data file has an unexpected format.")

        database = Database.from_dict(raw)

        # Persist upgrades (for example newly generated ids) exactly once.
        if database.to_dict() != raw:
            self.save(database)

        return database

    def save(self, database):
        temp_path = self._path + ".tmp"

        try:
            with open(temp_path, "w", encoding="utf-8") as file:
                json.dump(database.to_dict(), file, indent=2, ensure_ascii=False)
            os.replace(temp_path, self._path)
        except OSError as error:
            raise StorageError(f"The data file could not be saved: {error}")
