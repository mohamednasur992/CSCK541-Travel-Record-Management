"""Exceptions raised by the record layer.

The two validation errors subclass ``ValueError`` so code written against the
earlier behaviour (``except ValueError``) keeps working.
"""


class RecordError(Exception):
    """Base class for every error raised by the record layer."""


class RecordStorageError(RecordError):
    """The records file could not be written (disk full, read-only, locked ...)."""

    def __init__(self, path, cause):
        super().__init__(f"Could not save records to {path}: {cause}")
        self.path = path
        self.cause = cause


class DuplicateRecordError(RecordError, ValueError):
    """A client or airline with the same ID already exists."""


class ReferencedRecordError(RecordError, ValueError):
    """A client or airline cannot be deleted because flights still refer to it."""
