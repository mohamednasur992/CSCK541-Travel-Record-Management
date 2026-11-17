"""Shared test fixtures: a record manager on a temporary file and sample data."""

import tempfile
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
