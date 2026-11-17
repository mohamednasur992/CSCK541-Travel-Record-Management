"""Unit and integration tests for FR-06 to FR-15: create, search, display, update, delete."""

import unittest

from gui.reference_data import CITY_TO_COUNTRY
from tests.helpers import AIRLINE_FORM, CLIENT_FORM, FLIGHT_FORM, StoreTestCase


class TestCreate(StoreTestCase):
    """FR-06: create a record of each type."""

    def test_fr06_create_each_type_and_see_it_in_the_snapshot(self):
        for record_type, form in (("Client", CLIENT_FORM), ("Airline", AIRLINE_FORM)):
            result = self.create(record_type, form)
            self.assertEqual(len(result["records"][record_type]), 1)
        result = self.create("Flight", FLIGHT_FORM)
        self.assertEqual(len(result["records"]["Flight"]), 1)
        self.assertEqual(result["summary"]["clients"], 1)
        self.assertEqual(result["summary"]["airlines"], 1)
        self.assertEqual(result["summary"]["flights"], 1)

    def test_fr06_the_created_record_is_returned_with_its_key(self):
        result = self.create("Client", CLIENT_FORM)
        self.assertEqual(result["record"]["key"], 1)
        self.assertEqual(result["record"]["Name"], "Ada Lovelace")


class TestSearch(StoreTestCase):
    """FR-07: search across all fields or one field."""

    def setUp(self):
        super().setUp()
        self.seed()
        self.create("Client", {**CLIENT_FORM, "ID": "2", "Name": "Grace Hopper", "City": "New York",
                               "Country": "United States", "Phone Number": "+1 212 555 0100"})

    def names(self, text, field="All fields", record_type="Client"):
        result = self.api.search(record_type, text, field)
        self.assertTrue(result["ok"], result)
        return [row["Name"] for row in result["records"]]

    def test_matches_any_field_ignoring_case(self):
        self.assertEqual(self.names("LOVELACE"), ["Ada Lovelace"])
        self.assertEqual(self.names("new york"), ["Grace Hopper"])
        self.assertEqual(self.names("212 555"), ["Grace Hopper"])

    def test_matches_one_chosen_field_only(self):
        self.assertEqual(self.names("london", field="City"), ["Ada Lovelace"])
        self.assertEqual(self.names("london", field="Country"), [])

    def test_empty_text_returns_every_record_and_no_match_returns_none(self):
        self.assertEqual(len(self.names("")), 2)
        self.assertEqual(self.names("zzz-no-such-text"), [])

    def test_flight_search_also_matches_client_and_airline_names(self):
        rows = self.api.search("Flight", "lovelace")["records"]
        self.assertEqual(len(rows), 1)
        rows = self.api.search("Flight", "british airways")["records"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(self.api.search("Flight", "hopper")["records"], [])

    def test_unknown_search_field_is_refused(self):
        result = self.api.search("Client", "x", "Shoe Size")
        self.assertFalse(result["ok"])


class TestDisplay(StoreTestCase):
    """FR-08: the data the page needs to show tables and details."""

    def test_rows_carry_every_page_field_a_key_and_a_flight_count(self):
        self.seed()
        row = self.api.snapshot()["records"]["Client"][0]
        for field in CLIENT_FORM:
            self.assertEqual(row[field], CLIENT_FORM[field] if field != "ID" else 1)
        self.assertEqual(row["key"], 1)
        self.assertEqual(row["flights"], 1)

    def test_clients_and_airlines_are_listed_by_id(self):
        for number in (3, 1, 2):
            self.create("Airline", {"ID": str(number), "Company Name": f"Air {number}"})
        ids = [row["ID"] for row in self.api.snapshot()["records"]["Airline"]]
        self.assertEqual(ids, [1, 2, 3])

    def test_a_selected_record_can_be_fetched_with_full_details(self):
        self.seed()
        result = self.api.get("Client", 1)
        self.assertTrue(result["ok"])
        self.assertEqual(result["record"]["Address Line 2"], "Flat 2")


class TestUpdate(StoreTestCase):
    """FR-09: update any field except a client's or airline's ID."""

    def setUp(self):
        super().setUp()
        self.seed()

    def test_every_client_field_except_the_id_can_change(self):
        changed = {**CLIENT_FORM, "Name": "Ada King", "Address Line 1": "2 High St", "Address Line 2": "",
                   "Address Line 3": "Unit 9", "City": "Oxford", "State": "Oxon", "Zip Code": "OX1 1AA",
                   "Country": "United Kingdom", "Phone Number": "+44 1865 000000"}
        self.assertTrue(self.api.update("Client", 1, changed)["ok"])
        stored = self.stored("Client")[0]
        for field, value in changed.items():
            if field != "ID":
                self.assertEqual(stored[field], value, field)

    def test_the_id_cannot_be_changed(self):
        result = self.api.update("Client", 1, {**CLIENT_FORM, "ID": "99"})
        self.assertTrue(result["ok"])
        self.assertEqual([r["ID"] for r in self.stored("Client")], [1])
        result = self.api.update("Airline", 1, {**AIRLINE_FORM, "ID": "77"})
        self.assertEqual([r["ID"] for r in self.stored("Airline")], [1])

    def test_a_flight_can_change_every_field(self):
        self.create("Airline", {"ID": "2", "Company Name": "Air France (AF)"})
        key = self.api.snapshot()["records"]["Flight"][0]["key"]
        form = {"Client_ID": "1", "Airline_ID": "2", "Date": "2026-12-02 18:45",
                "Start City": "Rome", "End City": "Madrid"}
        result = self.api.update("Flight", key, form)
        self.assertTrue(result["ok"], result)
        flight = self.stored("Flight")[0]
        self.assertEqual((flight["Airline_ID"], flight["Date"], flight["Start City"], flight["End City"]),
                         (2, "2026-12-02 18:45", "Rome", "Madrid"))
        self.assertEqual(len(self.stored("Flight")), 1)

    def test_updating_a_missing_record_fails_cleanly(self):
        self.assertFalse(self.api.update("Client", 42, CLIENT_FORM)["ok"])
        self.assertFalse(self.api.update("Flight", ["x"], FLIGHT_FORM)["ok"])


class TestDelete(StoreTestCase):
    """FR-10: delete after the page has asked (delete_check), then delete."""

    def test_check_then_delete_an_unreferenced_airline(self):
        self.create("Airline", AIRLINE_FORM)
        check = self.api.delete_check("Airline", 1)
        self.assertTrue(check["ok"] and check["allowed"])
        self.assertTrue(self.api.delete("Airline", 1)["ok"])
        self.assertEqual(self.stored("Airline"), [])

    def test_a_flight_can_be_deleted_and_then_its_client(self):
        self.seed()
        key = self.api.snapshot()["records"]["Flight"][0]["key"]
        self.assertTrue(self.api.delete("Flight", key)["ok"])
        self.assertTrue(self.api.delete("Client", 1)["ok"])
        self.assertTrue(self.api.delete("Airline", 1)["ok"])
        self.assertEqual(self.rm.records, [])

    def test_deleting_something_that_does_not_exist_fails_cleanly(self):
        self.assertFalse(self.api.delete("Client", 5)["ok"])
        self.assertFalse(self.api.delete_check("Airline", 5)["ok"])

    def test_the_latest_delete_can_be_undone_in_place(self):
        self.create("Airline", AIRLINE_FORM)
        self.create("Airline", {"ID": "2", "Company Name": "Air France (AF)"})
        self.assertTrue(self.api.delete("Airline", 1)["ok"])
        self.assertTrue(self.api.undo_delete()["ok"])
        self.assertEqual([r["ID"] for r in self.stored("Airline")], [1, 2])
        self.assertFalse(self.api.undo_delete()["ok"])


class TestFlightIdentity(StoreTestCase):
    """FR-11: a flight is identified by its five values."""

    def test_two_flights_of_one_client_are_told_apart_by_their_key(self):
        self.seed()
        self.create("Flight", {**FLIGHT_FORM, "Date": "2026-12-05 08:00", "Start City": "Paris",
                               "End City": "Rome"})
        rows = self.api.snapshot()["records"]["Flight"]
        self.assertEqual(len(rows), 2)
        first, second = rows[0]["key"], rows[1]["key"]
        self.assertEqual(len(first), 5)
        self.assertNotEqual(first, second)
        self.assertTrue(self.api.update("Flight", second, {**FLIGHT_FORM, "Date": "2026-12-05 08:00",
                                                           "Start City": "Paris", "End City": "Oslo"})["ok"])
        cities = [(r["Start City"], r["End City"]) for r in self.stored("Flight")]
        self.assertEqual(cities, [("London", "Paris"), ("Paris", "Oslo")])
        self.assertEqual(self.api.get("Flight", first)["record"]["End City"], "Paris")


class TestChoicesAndSuggestions(StoreTestCase):
    """FR-12, FR-13, FR-14: drop-down choices and suggestions."""

    def test_fr12_choices_name_each_client_and_airline_by_id_and_name(self):
        self.seed()
        self.create("Client", {**CLIENT_FORM, "ID": "2", "Name": "Alan Turing"})
        choices = self.api.snapshot()["choices"]
        self.assertEqual([(c["id"], c["name"]) for c in choices["Client"]],
                         [(1, "Ada Lovelace"), (2, "Alan Turing")])
        self.assertEqual([(a["id"], a["name"]) for a in choices["Airline"]], [(1, "British Airways (BA)")])
        self.assertIn("1 flight", choices["Client"][0]["detail"])

    def test_fr13_the_page_receives_sorted_city_and_airline_suggestions(self):
        boot = self.api.bootstrap()
        for name in ("cities", "airlines"):
            self.assertTrue(boot[name])
            self.assertEqual(boot[name], sorted(boot[name]))
        self.assertIn("London", boot["cities"])

    def test_fr13_text_that_is_not_in_the_suggestions_is_still_accepted(self):
        self.create("Client", {**CLIENT_FORM, "City": "Smallville", "Country": "Kansas Republic"})
        self.create("Airline", {"ID": "7", "Company Name": "Home-made Air"})
        self.assertEqual(self.stored("Client")[0]["City"], "Smallville")

    def test_fr14_the_page_receives_a_country_for_each_suggested_city(self):
        boot = self.api.bootstrap()
        self.assertEqual(boot["city_country"], CITY_TO_COUNTRY)
        self.assertEqual(boot["city_country"]["London"], "United Kingdom")


class TestFeedback(StoreTestCase):
    """FR-15: every action returns a result the page can show."""

    def test_every_outcome_says_whether_it_worked_and_why_not(self):
        self.seed()
        outcomes = [
            self.api.create("Client", {**CLIENT_FORM, "Name": ""}),         # rejected input
            self.api.delete("Client", 1),                                   # blocked
            self.api.update("Client", 99, CLIENT_FORM),                     # missing
            self.api.create("Spaceship", {}),                               # unknown type
            self.api.save_all(),                                            # success
        ]
        for outcome in outcomes:
            self.assertIn("ok", outcome)
            if not outcome["ok"]:
                self.assertTrue(outcome.get("errors") or outcome.get("error"), outcome)


if __name__ == "__main__":
    unittest.main()
