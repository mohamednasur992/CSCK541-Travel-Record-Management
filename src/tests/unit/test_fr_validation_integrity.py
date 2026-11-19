"""Unit and integration tests for FR-16 to FR-21: validation and data integrity."""

import unittest

from record.errors import DuplicateRecordError, ReferencedRecordError
from tests.helpers import AIRLINE_FORM, CLIENT_FORM, FLIGHT_FORM, StoreTestCase


class TestFieldValidation(StoreTestCase):
    """FR-16: values are checked before anything is stored."""

    def rejected(self, record_type, form, field):
        result = self.api.create(record_type, form)
        self.assertFalse(result["ok"], result)
        self.assertIn(field, result["errors"])
        self.assertEqual(self.rm.records, [] if record_type != "Flight" else self.rm.records[:2])

    def test_phone_numbers_with_too_few_digits_or_bad_characters_are_rejected(self):
        for phone in ("12345", "+44 12", "abc1234567", "0151-ABC-4567", "44+1512345678", "07#1234567"):
            with self.subTest(phone=phone):
                self.rejected("Client", {**CLIENT_FORM, "Phone Number": phone}, "Phone Number")

    def test_phone_numbers_in_common_formats_are_accepted(self):
        for number, phone in enumerate(("+44 151 794 2000", "(0151) 794-2000", "0151 794 2000",
                                        "+27 83 287 8260", "1234567"), start=1):
            with self.subTest(phone=phone):
                self.create("Client", {**CLIENT_FORM, "ID": str(number), "Phone Number": phone})

    def test_text_longer_than_the_field_allows_is_rejected(self):
        self.rejected("Client", {**CLIENT_FORM, "Name": "x" * 101}, "Name")
        self.rejected("Client", {**CLIENT_FORM, "Zip Code": "1" * 21}, "Zip Code")
        self.rejected("Airline", {**AIRLINE_FORM, "Company Name": "A" * 101}, "Company Name")

    def test_ids_must_be_whole_numbers_of_one_or_more(self):
        for bad in ("0", "-3", "1.5", "one", "1e3", "٣"):
            with self.subTest(id=bad):
                result = self.api.create("Airline", {**AIRLINE_FORM, "ID": bad})
                self.assertFalse(result["ok"])
                self.assertIn("ID", result["errors"])

    def test_flight_dates_must_be_a_real_date_and_time(self):
        self.create("Client", CLIENT_FORM)
        self.create("Airline", AIRLINE_FORM)
        for bad in ("2026-12-01", "2026-13-01 09:30", "2026-02-30 09:30", "2026-12-01 25:00",
                    "2026-12-01 09:60", "01/12/2026 09:30", "tomorrow", "2026-12-01T09:30"):
            with self.subTest(date=bad):
                result = self.api.create("Flight", {**FLIGHT_FORM, "Date": bad})
                self.assertFalse(result["ok"])
                self.assertIn("Date", result["errors"])
        self.assertEqual(self.stored("Flight"), [])

    def test_a_leap_day_and_midnight_are_valid(self):
        self.create("Client", CLIENT_FORM)
        self.create("Airline", AIRLINE_FORM)
        self.create("Flight", {**FLIGHT_FORM, "Date": "2028-02-29 00:00"})

    def test_the_end_city_must_differ_from_the_start_city_ignoring_case_and_spaces(self):
        self.create("Client", CLIENT_FORM)
        self.create("Airline", AIRLINE_FORM)
        for end in ("London", "LONDON", "  london  "):
            with self.subTest(end=end):
                result = self.api.create("Flight", {**FLIGHT_FORM, "Start City": "London", "End City": end})
                self.assertFalse(result["ok"])
                self.assertIn("End City", result["errors"])

    def test_every_rejection_names_the_field_and_ends_like_a_sentence(self):
        result = self.api.create("Client", {"ID": "x"})
        self.assertGreaterEqual(len(result["errors"]), 6)
        for field, message in result["errors"].items():
            self.assertTrue(message[0].isupper() and message.endswith("."), (field, message))
        self.assertEqual(len(result["messages"]), len(result["errors"]))


class TestCityNames(StoreTestCase):
    """FR-16 (RT-17): city names are letters with simple joining punctuation, 2 to 60 characters."""

    BAD = ("Dubai@#$%&*!?", "Paris!", "London2", "123", "A", "-Paris", "Paris-", "Rome/Oslo", "<b>Rome</b>",
           "Lyon; DROP TABLE", "x" * 61, "x" * 100, "'", ".")
    GOOD = ("Dubai", "São Paulo", "Saint-Étienne", "St. John's", "Xi’an", "Rio de Janeiro", "München", "Zürich",
            "東京", "Москва", "Ho Chi Minh City", "Llanfairpwllgwyngyllgogerychwyrndrobwllllantysiliogogogoch")

    def setUp(self):
        super().setUp()
        self.create("Client", CLIENT_FORM)
        self.create("Airline", AIRLINE_FORM)

    def test_a_client_city_with_symbols_digits_or_the_wrong_length_is_rejected(self):
        for city in self.BAD:
            with self.subTest(city=city[:30]):
                result = self.api.create("Client", {**CLIENT_FORM, "ID": "2", "City": city})
                self.assertFalse(result["ok"], city)
                self.assertIn("City", result["errors"])
        self.assertEqual(len(self.stored("Client")), 1)

    def test_a_flight_start_or_end_city_is_checked_the_same_way(self):
        for city in self.BAD:
            for field, other in (("Start City", "End City"), ("End City", "Start City")):
                with self.subTest(city=city[:30], field=field):
                    form = {**FLIGHT_FORM, field: city, other: "Valid Place"}
                    result = self.api.create("Flight", form)
                    self.assertFalse(result["ok"], (city, field))
                    self.assertIn(field, result["errors"])
        self.assertEqual(self.stored("Flight"), [])

    def test_real_world_city_names_are_accepted(self):
        for number, city in enumerate(self.GOOD, start=10):
            with self.subTest(city=city[:30]):
                self.create("Client", {**CLIENT_FORM, "ID": str(number), "City": city})
                self.assertEqual(self.api.get("Client", number)["record"]["City"], city)

    def test_the_longest_allowed_name_is_60_characters_and_the_message_says_so(self):
        self.assertTrue(self.api.create("Client", {**CLIENT_FORM, "ID": "2", "City": "a" * 60})["ok"])
        result = self.api.create("Client", {**CLIENT_FORM, "ID": "3", "City": "a" * 61})
        self.assertIn("at most 60", result["errors"]["City"])

    def test_the_message_explains_how_to_fix_a_bad_city(self):
        message = self.api.create("Client", {**CLIENT_FORM, "ID": "2", "City": "Dubai@#$%&*!?"})["errors"]["City"]
        self.assertIn("letters", message)
        self.assertIn("Saint-Étienne", message)
        self.assertTrue(message[0].isupper() and message.endswith("."))

    def test_updating_a_record_applies_the_same_rule(self):
        self.assertFalse(self.api.update("Client", 1, {**CLIENT_FORM, "City": "Dubai@#$%"})["ok"])
        self.assertEqual(self.stored("Client")[0]["City"], "London")
        self.create("Flight", FLIGHT_FORM)
        key = self.api.snapshot()["records"]["Flight"][0]["key"]
        self.assertFalse(self.api.update("Flight", key, {**FLIGHT_FORM, "End City": "Pa$$is"})["ok"])
        self.assertEqual(self.stored("Flight")[0]["End City"], "Paris")

    def test_the_page_is_told_the_same_length_limit(self):
        fields = self.api.bootstrap()["fields"]
        client = {spec["name"]: spec for spec in fields["Client"]}
        flight = {spec["name"]: spec for spec in fields["Flight"]}
        self.assertEqual(client["City"]["max_length"], 60)
        self.assertEqual((flight["Start City"]["max_length"], flight["End City"]["max_length"]), (60, 60))

    def test_cities_already_stored_are_not_re_checked_when_loaded(self):
        self.rm.add_client(5, "Old", "x", "", "", "Dubai@#$", "", "", "k", "1234567")      # earlier data
        self.assertEqual(self.api.get("Client", 5)["record"]["City"], "Dubai@#$")


class TestUniqueIds(StoreTestCase):
    """FR-17: next free ID suggested; duplicates rejected."""

    def test_the_next_free_id_is_one_more_than_the_highest(self):
        self.assertEqual(self.api.snapshot()["next_id"], {"Client": 1, "Airline": 1})
        self.create("Client", {**CLIENT_FORM, "ID": "1"})
        self.create("Client", {**CLIENT_FORM, "ID": "7", "Name": "Seven"})
        self.create("Airline", AIRLINE_FORM)
        self.assertEqual(self.api.snapshot()["next_id"], {"Client": 8, "Airline": 2})

    def test_a_duplicate_client_or_airline_id_is_rejected_by_the_page_layer(self):
        self.create("Client", CLIENT_FORM)
        self.create("Airline", AIRLINE_FORM)
        self.assertIn("ID", self.api.create("Client", {**CLIENT_FORM, "Name": "Other"})["errors"])
        self.assertIn("ID", self.api.create("Airline", {**AIRLINE_FORM, "Company Name": "Other"})["errors"])
        self.assertEqual((len(self.stored("Client")), len(self.stored("Airline"))), (1, 1))

    def test_a_duplicate_id_is_also_rejected_by_the_record_manager_itself(self):
        self.rm.add_client(1, "A", "x", "", "", "c", "", "", "k", "1234567")
        with self.assertRaises(DuplicateRecordError):
            self.rm.add_client(1, "B", "x", "", "", "c", "", "", "k", "1234567")
        self.rm.add_airline(1, "Air")
        with self.assertRaises(DuplicateRecordError):
            self.rm.add_airline(1, "Air 2")

    def test_a_client_and_an_airline_may_share_an_id(self):
        self.create("Client", CLIENT_FORM)
        self.create("Airline", AIRLINE_FORM)
        self.assertEqual(self.stored("Client")[0]["ID"], self.stored("Airline")[0]["ID"])


class TestAirlineNames(StoreTestCase):
    """FR-18: no two airlines share a name."""

    def test_names_are_compared_ignoring_case_and_surrounding_spaces(self):
        self.create("Airline", AIRLINE_FORM)
        for name in ("british airways (ba)", "  BRITISH AIRWAYS (BA)  "):
            with self.subTest(name=name):
                result = self.api.create("Airline", {"ID": "2", "Company Name": name})
                self.assertFalse(result["ok"])
                self.assertIn("Company Name", result["errors"])

    def test_an_airline_may_keep_its_own_name_when_updated(self):
        self.create("Airline", AIRLINE_FORM)
        self.assertTrue(self.api.update("Airline", 1, AIRLINE_FORM)["ok"])

    def test_renaming_an_airline_to_another_airlines_name_is_rejected(self):
        self.create("Airline", AIRLINE_FORM)
        self.create("Airline", {"ID": "2", "Company Name": "Air France (AF)"})
        result = self.api.update("Airline", 2, {"ID": "2", "Company Name": "british airways (ba)"})
        self.assertFalse(result["ok"])
        self.assertEqual(self.stored("Airline")[1]["Company Name"], "Air France (AF)")


class TestFlightReferences(StoreTestCase):
    """FR-19: a flight needs an existing client and airline."""

    def test_unknown_client_or_airline_is_rejected_on_create_and_update(self):
        self.seed()
        self.assertIn("Client_ID", self.api.create("Flight", {**FLIGHT_FORM, "Client_ID": "9"})["errors"])
        self.assertIn("Airline_ID", self.api.create("Flight", {**FLIGHT_FORM, "Airline_ID": "9"})["errors"])
        key = self.api.snapshot()["records"]["Flight"][0]["key"]
        result = self.api.update("Flight", key, {**FLIGHT_FORM, "Client_ID": "9"})
        self.assertIn("Client_ID", result["errors"])
        self.assertEqual(self.stored("Flight")[0]["Client_ID"], 1)

    def test_the_reference_must_be_the_right_type_of_record(self):
        self.create("Client", {**CLIENT_FORM, "ID": "5"})
        self.create("Airline", {"ID": "6", "Company Name": "Air"})
        result = self.api.create("Flight", {**FLIGHT_FORM, "Client_ID": "6", "Airline_ID": "5"})
        self.assertFalse(result["ok"])
        self.assertEqual(set(result["errors"]), {"Client_ID", "Airline_ID"})


class TestReferencedRecords(StoreTestCase):
    """FR-20: clients and airlines that have flights cannot be deleted."""

    def setUp(self):
        super().setUp()
        self.seed()
        self.create("Flight", {**FLIGHT_FORM, "Date": "2026-12-09 10:00", "Start City": "Rome",
                               "End City": "Oslo"})

    def test_the_page_is_told_how_many_flights_refer_to_the_record(self):
        for record_type in ("Client", "Airline"):
            check = self.api.delete_check(record_type, 1)
            self.assertFalse(check["allowed"])
            self.assertEqual(check["linked_flights"], 2)

    def test_delete_is_refused_even_if_the_page_skips_the_check(self):
        for record_type in ("Client", "Airline"):
            result = self.api.delete(record_type, 1)
            self.assertFalse(result["ok"])
            self.assertTrue(result["blocked"])
        self.assertEqual(len(self.stored("Client")), 1)
        self.assertEqual(len(self.stored("Airline")), 1)

    def test_the_record_manager_refuses_too(self):
        with self.assertRaises(ReferencedRecordError):
            self.rm.delete_record(1, record_type="Client")
        with self.assertRaises(ReferencedRecordError):
            self.rm.delete_record(1, record_type="Airline")

    def test_deleting_the_flights_unblocks_the_delete(self):
        for row in list(self.api.snapshot()["records"]["Flight"]):
            self.assertTrue(self.api.delete("Flight", row["key"])["ok"])
        self.assertTrue(self.api.delete_check("Client", 1)["allowed"])
        self.assertTrue(self.api.delete("Client", 1)["ok"])


class TestJourneyRuleThroughTheBridge(StoreTestCase):
    """FR-21: one linear journey per client and day, on create, update and delete."""

    def setUp(self):
        super().setUp()
        self.seed()                                        # London -> Paris, 2026-12-01 09:30

    def leg(self, start, end, when="2026-12-01 15:00"):
        return {**FLIGHT_FORM, "Date": when, "Start City": start, "End City": end}

    def test_a_connecting_leg_the_same_day_is_allowed(self):
        self.create("Flight", self.leg("Paris", "Rome"))
        self.create("Flight", self.leg("Rome", "Oslo", "2026-12-01 21:15"))
        self.assertEqual(len(self.stored("Flight")), 3)

    def test_a_second_departure_from_the_same_city_is_blocked_with_a_reason(self):
        result = self.api.create("Flight", self.leg("London", "Rome"))
        self.assertFalse(result["ok"])
        self.assertIn("London", result["errors"]["Start City"])

    def test_a_leg_that_does_not_connect_is_blocked(self):
        result = self.api.create("Flight", self.leg("Madrid", "Rome"))
        self.assertFalse(result["ok"])
        self.assertIn("Paris", result["errors"]["Start City"])

    def test_an_identical_booking_is_blocked(self):
        self.assertFalse(self.api.create("Flight", FLIGHT_FORM)["ok"])

    def test_another_day_or_another_client_starts_a_fresh_journey(self):
        self.create("Flight", self.leg("Madrid", "Rome", "2026-12-02 09:00"))
        self.create("Client", {**CLIENT_FORM, "ID": "2", "Name": "Alan Turing"})
        self.create("Flight", {**self.leg("Madrid", "Rome"), "Client_ID": "2"})

    def test_an_update_cannot_break_the_journey(self):
        self.create("Flight", self.leg("Paris", "Rome"))
        first = self.api.snapshot()["records"]["Flight"][0]["key"]
        result = self.api.update("Flight", first, {**FLIGHT_FORM, "End City": "Berlin"})
        self.assertFalse(result["ok"])
        self.assertEqual(self.stored("Flight")[0]["End City"], "Paris")

    def test_deleting_a_middle_leg_is_blocked_but_the_last_leg_can_go(self):
        self.create("Flight", self.leg("Paris", "Rome"))
        self.create("Flight", self.leg("Rome", "Oslo", "2026-12-01 21:15"))
        rows = self.api.snapshot()["records"]["Flight"]
        check = self.api.delete_check("Flight", rows[1]["key"])
        self.assertFalse(check["allowed"])
        self.assertTrue(check["reason"])
        self.assertFalse(self.api.delete("Flight", rows[1]["key"])["ok"])
        self.assertTrue(self.api.delete("Flight", rows[2]["key"])["ok"])
        self.assertEqual(len(self.stored("Flight")), 2)


if __name__ == "__main__":
    unittest.main()
