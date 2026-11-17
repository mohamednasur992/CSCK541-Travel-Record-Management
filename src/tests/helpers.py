"""Shared test fixtures: a record manager on a temporary file and sample data."""

import tempfile
import unittest
from datetime import date
from pathlib import Path

from gui.bridge import WebApi
from record.record import RecordManager

TODAY = date(2026, 11, 10)

CLIENT_FORM = {"ID": "1", "Name": "Ada Lovelace", "Address Line 1": "1 Main St", "Address Line 2": "Flat 2",
               "Address Line 3": "", "City": "London", "State": "Greater London", "Zip Code": "SW1A 1AA",
               "Country": "United Kingdom", "Phone Number": "+44 151 123 4567"}
AIRLINE_FORM = {"ID": "1", "Company Name": "British Airways (BA)"}
FLIGHT_FORM = {"Client_ID": "1", "Airline_ID": "1", "Date": "2026-12-01 09:30", "Start City": "London", "End City": "Paris"}


class TempStore:
    """A temporary folder holding a records file; call ``cleanup`` when done."""

    def __init__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)
        self.data_file = self.folder / "record.jsonl"

    def manager(self):
        return RecordManager(filepath=self.data_file)

    def api(self, manager=None):
        manager = manager or self.manager()
        return WebApi(manager, today=lambda: TODAY, settings_path=self.folder / "settings.json"), manager

    def cleanup(self):
        self._tmp.cleanup()


def add_sample_records(manager):
    """One client, two airlines and one flight, added directly to ``manager``."""
    manager.add_client(1, "Ada Lovelace", "1 Main St", "Flat 2", "", "London", "Greater London",
                       "SW1A 1AA", "United Kingdom", "+44 151 123 4567")
    manager.add_airline(1, "British Airways (BA)")
    manager.add_airline(2, "Air France (AF)")
    manager.add_flight(1, 1, "2026-12-01 09:30", "London", "Paris")


class StoreTestCase(unittest.TestCase):
    """Base class: a fresh temporary store, a bridge and a manager per test.

    Tests never touch the real records file; everything lives in a temporary
    folder that is removed afterwards.
    """

    def setUp(self):
        self.store = TempStore()
        self.addCleanup(self.store.cleanup)
        self.api, self.rm = self.store.api()

    def create(self, record_type, form):
        """Create a record through the bridge and require success."""
        result = self.api.create(record_type, form)
        self.assertTrue(result["ok"], result)
        return result

    def seed(self):
        """Client 1, airline 1 and one flight, created through the bridge."""
        self.create("Client", CLIENT_FORM)
        self.create("Airline", AIRLINE_FORM)
        self.create("Flight", FLIGHT_FORM)

    def stored(self, record_type):
        """The stored records of one type."""
        return [r for r in self.rm.records if r["Type"] == record_type]

    def file_lines(self):
        """Non-empty lines currently in the records file."""
        if not self.store.data_file.exists():
            return []
        text = self.store.data_file.read_text(encoding="utf-8")
        return [line for line in text.splitlines() if line.strip()]
