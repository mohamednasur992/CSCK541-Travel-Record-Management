"""Headless tests for the linear same-day connected-flight rule."""

import sys
import types
import unittest
from pathlib import Path


# The build environment has no Tk runtime. These minimal stubs allow the
# flight-tab module to be imported without creating or rendering any widgets.
tkinter_stub = types.ModuleType("tkinter")
tkinter_stub.END = "end"
tkinter_stub.messagebox = types.SimpleNamespace()
tkinter_stub.ttk = types.SimpleNamespace()
sys.modules.setdefault("tkinter", tkinter_stub)

tkcalendar_stub = types.ModuleType("tkcalendar")
tkcalendar_stub.DateEntry = object
sys.modules.setdefault("tkcalendar", tkcalendar_stub)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

autocomplete_stub = types.ModuleType("gui.autocomplete")
autocomplete_stub.AutocompleteCombobox = object
sys.modules.setdefault("gui.autocomplete", autocomplete_stub)

constants_stub = types.ModuleType("gui.constants")
constants_stub.WORLD_CITIES = ()
sys.modules.setdefault("gui.constants", constants_stub)

from gui.flight_tab import FlightTab  # noqa: E402  pylint: disable=wrong-import-position


class FakeRecordManager:
    """Return a controlled list of stored flight records."""

    def __init__(self, records):
        self.records = records

    def search_records(self, record_type=None):
        if record_type == "Flight":
            return list(self.records)
        return []


def make_tab(records, original=None):
    """Construct a FlightTab without running its Tk-dependent initializer."""
    tab = object.__new__(FlightTab)
    tab.rm = FakeRecordManager(records)
    tab.original_flight_key = original
    return tab


FIRST_LEG = {
    "type": "Flight",
    "client_id": 1,
    "airline_id": 1,
    "date": "2026-11-09",
    "start_city": "Johannesburg",
    "end_city": "Moscow",
}
SECOND_LEG = {
    **FIRST_LEG,
    "airline_id": 2,
    "start_city": "Moscow",
    "end_city": "London",
}
THIRD_LEG = {
    **FIRST_LEG,
    "airline_id": 3,
    "start_city": "London",
    "end_city": "Paris",
}


class BookingDateConflictTests(unittest.TestCase):
    """Verify one ordered, non-branching journey per client and date."""

    def test_first_flight_on_date_is_allowed(self):
        self.assertFalse(make_tab([]).has_booking_date_conflict(FIRST_LEG))

    def test_connected_second_leg_is_allowed(self):
        self.assertFalse(
            make_tab([FIRST_LEG]).has_booking_date_conflict(SECOND_LEG)
        )

    def test_city_matching_ignores_case_and_surrounding_whitespace(self):
        candidate = {
            **SECOND_LEG,
            "start_city": "  mOsCoW  ",
        }
        self.assertFalse(
            make_tab([FIRST_LEG]).has_booking_date_conflict(candidate)
        )

    def test_duplicate_identical_booking_is_blocked(self):
        tab = make_tab([FIRST_LEG, SECOND_LEG])
        message = tab.booking_conflict_message(SECOND_LEG.copy())
        self.assertIsNotNone(message)
        self.assertIn("identical", message.lower())

    def test_second_outgoing_flight_from_reached_city_is_blocked(self):
        branch = {
            **SECOND_LEG,
            "airline_id": 4,
            "end_city": "Amsterdam",
        }
        tab = make_tab([FIRST_LEG, SECOND_LEG])
        message = tab.booking_conflict_message(branch)
        self.assertIsNotNone(message)
        self.assertIn("already departs from Moscow", message)

    def test_third_leg_must_start_from_latest_destination(self):
        stale_connection = {
            **THIRD_LEG,
            "start_city": "Moscow",
            "end_city": "Paris",
        }
        self.assertTrue(
            make_tab([FIRST_LEG, SECOND_LEG]).has_booking_date_conflict(
                stale_connection
            )
        )

    def test_third_leg_from_latest_destination_is_allowed(self):
        self.assertFalse(
            make_tab([FIRST_LEG, SECOND_LEG]).has_booking_date_conflict(
                THIRD_LEG
            )
        )

    def test_unconnected_same_day_flight_is_blocked(self):
        candidate = {
            **SECOND_LEG,
            "start_city": "Accra",
            "end_city": "Amsterdam",
        }
        tab = make_tab([FIRST_LEG])
        message = tab.booking_conflict_message(candidate)
        self.assertIsNotNone(message)
        self.assertIn("Moscow", message)

    def test_reusing_an_earlier_start_city_is_blocked(self):
        loop = {
            **THIRD_LEG,
            "start_city": "London",
            "end_city": "Johannesburg",
        }
        repeated_departure = {
            **THIRD_LEG,
            "airline_id": 4,
            "start_city": "Johannesburg",
            "end_city": "Cape Town",
        }
        tab = make_tab([FIRST_LEG, SECOND_LEG, loop])
        message = tab.booking_conflict_message(repeated_departure)
        self.assertIsNotNone(message)
        self.assertIn("already departs from Johannesburg", message)

    def test_different_date_is_allowed(self):
        candidate = {
            **SECOND_LEG,
            "date": "2026-11-10",
            "start_city": "Accra",
        }
        self.assertFalse(
            make_tab([FIRST_LEG]).has_booking_date_conflict(candidate)
        )

    def test_different_client_is_allowed(self):
        candidate = {
            **SECOND_LEG,
            "client_id": 2,
            "start_city": "Accra",
        }
        self.assertFalse(
            make_tab([FIRST_LEG]).has_booking_date_conflict(candidate)
        )

    def test_update_replaces_original_leg_in_place(self):
        updated_second_leg = {
            **SECOND_LEG,
            "airline_id": 5,
        }
        tab = make_tab(
            [FIRST_LEG, SECOND_LEG, THIRD_LEG],
            original=SECOND_LEG.copy(),
        )
        self.assertFalse(
            tab.has_booking_date_conflict(
                updated_second_leg, exclude_original=True
            )
        )

    def test_update_cannot_break_following_connection(self):
        updated_second_leg = {
            **SECOND_LEG,
            "end_city": "Amsterdam",
        }
        tab = make_tab(
            [FIRST_LEG, SECOND_LEG, THIRD_LEG],
            original=SECOND_LEG.copy(),
        )
        message = tab.booking_conflict_message(
            updated_second_leg, exclude_original=True
        )
        self.assertIsNotNone(message)
        self.assertIn("Amsterdam", message)

    def test_update_cannot_move_middle_leg_out_of_existing_journey(self):
        moved_second_leg = {
            **SECOND_LEG,
            "client_id": 2,
            "date": "2026-11-10",
        }
        tab = make_tab(
            [FIRST_LEG, SECOND_LEG, THIRD_LEG],
            original=SECOND_LEG.copy(),
        )
        message = tab.booking_conflict_message(
            moved_second_leg, exclude_original=True
        )
        self.assertIsNotNone(message)
        self.assertIn("break the remaining", message)

    def test_update_ignores_original_when_it_is_only_leg(self):
        tab = make_tab([FIRST_LEG], original=FIRST_LEG.copy())
        self.assertFalse(
            tab.has_booking_date_conflict(FIRST_LEG, exclude_original=True)
        )


if __name__ == "__main__":
    unittest.main()
