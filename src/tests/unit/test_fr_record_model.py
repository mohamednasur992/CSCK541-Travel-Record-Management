"""Unit tests for FR-01 to FR-05: the three record types and their fields."""

import unittest

from record import schema
from tests.helpers import AIRLINE_FORM, CLIENT_FORM, FLIGHT_FORM, StoreTestCase

CLIENT_REQUIRED = ("ID", "Name", "Address Line 1", "City", "Country", "Phone Number")
CLIENT_OPTIONAL = ("Address Line 2", "Address Line 3", "State", "Zip Code")
FLIGHT_REQUIRED = ("Client_ID", "Airline_ID", "Date", "Start City", "End City")


class TestRecordTypes(StoreTestCase):
    """FR-01, FR-02: one list of dictionaries, each carrying a Type."""

    def test_fr01_all_three_types_live_in_one_list_of_dicts(self):
        self.seed()
        self.assertIsInstance(self.rm.records, list)
        self.assertTrue(all(isinstance(record, dict) for record in self.rm.records))
        self.assertEqual({r["Type"] for r in self.rm.records}, {"Client", "Airline", "Flight"})
        self.assertEqual(len(self.rm.records), 3)

    def test_fr02_every_record_has_a_valid_type(self):
        self.seed()
        for record in self.rm.records:
            self.assertIn(record["Type"], schema.RECORD_TYPES)

    def test_fr02_the_type_cannot_be_chosen_by_the_page_data(self):
        form = {**CLIENT_FORM, "Type": "Airline"}
        self.create("Client", form)
        self.assertEqual(self.rm.records[0]["Type"], "Client")


class TestClientRecord(StoreTestCase):
    """FR-03: the client fields of the brief."""

    def test_stored_client_has_exactly_the_brief_fields(self):
        self.create("Client", CLIENT_FORM)
        self.assertEqual(set(self.rm.records[0]), set(schema.CLIENT_FIELDS))
        self.assertEqual(set(schema.CLIENT_FIELDS), {
            "ID", "Type", "Name", "Address Line 1", "Address Line 2", "Address Line 3",
            "City", "State", "Zip Code", "Country", "Phone Number"})

    def test_client_id_is_an_integer_and_the_rest_is_text(self):
        self.create("Client", CLIENT_FORM)
        record = self.rm.records[0]
        self.assertIsInstance(record["ID"], int)
        for key in schema.CLIENT_FIELDS:
            if key != "ID":
                self.assertIsInstance(record[key], str, key)

    def test_each_required_client_field_is_enforced(self):
        for field in CLIENT_REQUIRED:
            with self.subTest(field=field):
                result = self.api.create("Client", {**CLIENT_FORM, field: ""})
                self.assertFalse(result["ok"])
                self.assertIn(field, result["errors"])
        self.assertEqual(self.rm.records, [])

    def test_optional_client_fields_may_be_blank(self):
        form = {**CLIENT_FORM, **{field: "" for field in CLIENT_OPTIONAL}}
        self.create("Client", form)
        for field in CLIENT_OPTIONAL:
            self.assertEqual(self.rm.records[0][field], "")


class TestAirlineRecord(StoreTestCase):
    """FR-04: the airline fields of the brief."""

    def test_stored_airline_has_exactly_the_brief_fields(self):
        self.create("Airline", AIRLINE_FORM)
        self.assertEqual(set(self.rm.records[0]), {"ID", "Type", "Company Name"})
        self.assertIsInstance(self.rm.records[0]["ID"], int)

    def test_every_airline_field_is_required(self):
        for field in ("ID", "Company Name"):
            with self.subTest(field=field):
                result = self.api.create("Airline", {**AIRLINE_FORM, field: " "})
                self.assertFalse(result["ok"])
                self.assertIn(field, result["errors"])


class TestFlightRecord(StoreTestCase):
    """FR-05: the flight fields of the brief."""

    def setUp(self):
        super().setUp()
        self.create("Client", CLIENT_FORM)
        self.create("Airline", AIRLINE_FORM)

    def test_stored_flight_has_exactly_the_brief_fields(self):
        self.create("Flight", FLIGHT_FORM)
        flight = self.stored("Flight")[0]
        self.assertEqual(set(flight), {"Type", "Client_ID", "Airline_ID", "Date", "Start City", "End City"})

    def test_ids_are_integers_and_the_date_keeps_date_and_time(self):
        self.create("Flight", FLIGHT_FORM)
        flight = self.stored("Flight")[0]
        self.assertIsInstance(flight["Client_ID"], int)
        self.assertIsInstance(flight["Airline_ID"], int)
        self.assertEqual(flight["Date"], "2026-12-01 09:30")

    def test_every_flight_field_is_required(self):
        for field in FLIGHT_REQUIRED:
            with self.subTest(field=field):
                result = self.api.create("Flight", {**FLIGHT_FORM, field: ""})
                self.assertFalse(result["ok"])
                self.assertIn(field, result["errors"])
        self.assertEqual(self.stored("Flight"), [])


if __name__ == "__main__":
    unittest.main()
