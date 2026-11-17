"""Headless tests for the linear same-day connected-flight rule."""

import unittest

from record.flight_rules import FlightBookingRules


class FakeRecordManager:
    """Return a controlled list of stored flight records."""

    def __init__(self, records):
        self.records = records

    def search_records(self, record_type=None):
        if record_type == "Flight":
            return list(self.records)
        return []


def make_tab(records, original=None):
    """Booking rules over ``records``, optionally editing ``original``."""
    tab = FlightBookingRules(FakeRecordManager(records))
    tab.original_flight_key = original
    return tab


FIRST_LEG = {
    "Type": "Flight",
    "Client_ID": 1,
    "Airline_ID": 1,
    "Date": "2026-11-09 08:00",
    "Start City": "Johannesburg",
    "End City": "Moscow",
}
SECOND_LEG = {
    **FIRST_LEG,
    "Airline_ID": 2,
    "Date": "2026-11-09 14:30",
    "Start City": "Moscow",
    "End City": "London",
}
THIRD_LEG = {
    **FIRST_LEG,
    "Airline_ID": 3,
    "Date": "2026-11-09 21:15",
    "Start City": "London",
    "End City": "Paris",
}


class BookingDateConflictTests(unittest.TestCase):
    """Verify one ordered, non-branching journey per client and calendar day."""

    def test_legs_at_different_times_on_one_day_form_one_journey(self):
        unconnected_later_flight = {**SECOND_LEG, "Date": "2026-11-09 23:59", "Start City": "Accra"}
        self.assertTrue(make_tab([FIRST_LEG]).has_booking_date_conflict(unconnected_later_flight))

    def test_first_flight_on_date_is_allowed(self):
        self.assertFalse(make_tab([]).has_booking_date_conflict(FIRST_LEG))

    def test_connected_second_leg_is_allowed(self):
        self.assertFalse(
            make_tab([FIRST_LEG]).has_booking_date_conflict(SECOND_LEG)
        )

    def test_city_matching_ignores_case_and_surrounding_whitespace(self):
        candidate = {
            **SECOND_LEG,
            "Start City": "  mOsCoW  ",
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
            "Airline_ID": 4,
            "End City": "Amsterdam",
        }
        tab = make_tab([FIRST_LEG, SECOND_LEG])
        message = tab.booking_conflict_message(branch)
        self.assertIsNotNone(message)
        self.assertIn("already departs from Moscow", message)

    def test_third_leg_must_start_from_latest_destination(self):
        stale_connection = {
            **THIRD_LEG,
            "Start City": "Moscow",
            "End City": "Paris",
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
            "Start City": "Accra",
            "End City": "Amsterdam",
        }
        tab = make_tab([FIRST_LEG])
        message = tab.booking_conflict_message(candidate)
        self.assertIsNotNone(message)
        self.assertIn("Moscow", message)

    def test_reusing_an_earlier_start_city_is_blocked(self):
        loop = {
            **THIRD_LEG,
            "Start City": "London",
            "End City": "Johannesburg",
        }
        repeated_departure = {
            **THIRD_LEG,
            "Airline_ID": 4,
            "Start City": "Johannesburg",
            "End City": "Cape Town",
        }
        tab = make_tab([FIRST_LEG, SECOND_LEG, loop])
        message = tab.booking_conflict_message(repeated_departure)
        self.assertIsNotNone(message)
        self.assertIn("already departs from Johannesburg", message)

    def test_different_date_is_allowed(self):
        candidate = {
            **SECOND_LEG,
            "Date": "2026-11-10 08:00",
            "Start City": "Accra",
        }
        self.assertFalse(
            make_tab([FIRST_LEG]).has_booking_date_conflict(candidate)
        )

    def test_different_client_is_allowed(self):
        candidate = {
            **SECOND_LEG,
            "Client_ID": 2,
            "Start City": "Accra",
        }
        self.assertFalse(
            make_tab([FIRST_LEG]).has_booking_date_conflict(candidate)
        )

    def test_update_replaces_original_leg_in_place(self):
        updated_second_leg = {
            **SECOND_LEG,
            "Airline_ID": 5,
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
            "End City": "Amsterdam",
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
            "Client_ID": 2,
            "Date": "2026-11-10 08:00",
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

    def test_deleting_the_last_leg_is_allowed(self):
        self.assertIsNone(make_tab([FIRST_LEG, SECOND_LEG]).deletion_conflict_message(SECOND_LEG))

    def test_deleting_a_middle_leg_is_blocked(self):
        message = make_tab([FIRST_LEG, SECOND_LEG, THIRD_LEG]).deletion_conflict_message(SECOND_LEG)
        self.assertIsNotNone(message)
        self.assertIn("cannot be deleted", message)

    def test_update_ignores_original_when_it_is_only_leg(self):
        tab = make_tab([FIRST_LEG], original=FIRST_LEG.copy())
        self.assertFalse(
            tab.has_booking_date_conflict(FIRST_LEG, exclude_original=True)
        )


if __name__ == "__main__":
    unittest.main()
