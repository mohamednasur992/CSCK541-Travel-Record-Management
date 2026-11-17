"""RecordManager: create, search, update and delete records in memory."""

import unittest

from record.errors import DuplicateRecordError, ReferencedRecordError
from tests.helpers import TempStore, add_sample_records


class RecordManagerTestCase(unittest.TestCase):
    def setUp(self):
        self.store = TempStore()
        self.addCleanup(self.store.cleanup)
        self.rm = self.store.manager()
        add_sample_records(self.rm)


class TestCreate(RecordManagerTestCase):
    def test_records_are_one_list_of_dictionaries_with_a_type(self):
        self.assertIsInstance(self.rm.records, list)
        self.assertTrue(all(isinstance(r, dict) for r in self.rm.records))
        self.assertEqual([r["Type"] for r in self.rm.records], ["Client", "Airline", "Airline", "Flight"])

    def test_client_fields_and_integer_id(self):
        client = self.rm.add_client("7", "Grace Hopper", "5 Navy Rd", "", "", "New York", "NY", "10001",
                                    "United States", "+1 212 555 0100")
        self.assertEqual(client["ID"], 7)
        # Exactly the client fields named in the assignment brief.
        self.assertEqual(list(client), ["ID", "Type", "Name", "Address Line 1", "Address Line 2", "Address Line 3",
                                        "City", "State", "Zip Code", "Country", "Phone Number"])

    def test_flight_ids_become_integers(self):
        flight = self.rm.add_flight("1", "2", "2026-12-02 10:00", "Paris", "Rome")
        self.assertEqual((flight["Client_ID"], flight["Airline_ID"]), (1, 2))

    def test_duplicate_ids_are_rejected(self):
        with self.assertRaises(DuplicateRecordError):
            self.rm.add_client(1, "Someone", "2 High St", "", "", "Leeds", "", "", "United Kingdom", "+44 113 000 0000")
        with self.assertRaises(ValueError):          # still a ValueError for older callers
            self.rm.add_airline(2, "Another")
        self.assertEqual(len(self.rm.records), 4)

    def test_non_numeric_id_is_rejected(self):
        with self.assertRaises(ValueError):
            self.rm.add_airline("abc", "Bad")


class TestSearch(RecordManagerTestCase):
    def test_filter_by_type_and_keyword(self):
        self.assertEqual(len(self.rm.search_records(record_type="Airline")), 2)
        self.assertEqual(len(self.rm.search_records("LONDON")), 2)       # client city and flight start
        self.assertEqual(len(self.rm.search_records("paris", record_type="Flight")), 1)
        self.assertEqual(self.rm.search_records("nothing-matches"), [])

    def test_get_record_by_id(self):
        self.assertEqual(self.rm.get_record_by_id("2", record_type="Airline")["Company Name"], "Air France (AF)")
        self.assertIsNone(self.rm.get_record_by_id(9))
        with self.assertRaises(ValueError):
            self.rm.get_record_by_id("x")


class TestUpdate(RecordManagerTestCase):
    def test_update_client(self):
        self.assertTrue(self.rm.update_record(1, {"City": "Paris"}, record_type="Client"))
        self.assertEqual(self.rm.get_record_by_id(1, "Client")["City"], "Paris")

    def test_update_flight_by_its_identifying_fields(self):
        changed = self.rm.update_record(1, {"end_city": "Rome"}, record_type="Flight", old_airline_id=1,
                                        old_date="2026-12-01 09:30", old_start="London", old_end="Paris")
        self.assertTrue(changed)
        self.assertEqual(self.rm.search_records(record_type="Flight")[0]["end_city"], "Rome")

    def test_update_missing_record_returns_false(self):
        self.assertFalse(self.rm.update_record(99, {"Name": "x"}, record_type="Client"))
        self.assertFalse(self.rm.update_record(1, {}, record_type="Flight", old_date="1999-01-01"))


class TestDelete(RecordManagerTestCase):
    def test_referenced_client_and_airline_cannot_be_deleted(self):
        with self.assertRaises(ReferencedRecordError):
            self.rm.delete_record(1, record_type="Client")
        with self.assertRaises(ValueError):
            self.rm.delete_record(1, record_type="Airline")
        self.assertEqual(len(self.rm.records), 4)

    def test_delete_flight_then_its_client(self):
        self.assertTrue(self.rm.delete_record(1, record_type="Flight", airline_id=1, date="2026-12-01 09:30",
                                              start_city="London", end_city="Paris"))
        self.assertTrue(self.rm.delete_record(1, record_type="Client"))
        self.assertIsNone(self.rm.get_record_by_id(1, "Client"))

    def test_unreferenced_airline_and_missing_record(self):
        self.assertTrue(self.rm.delete_record(2, record_type="Airline"))
        self.assertFalse(self.rm.delete_record(2, record_type="Airline"))

    def test_changes_are_not_written_until_saved(self):
        self.rm.delete_record(2, record_type="Airline")
        self.assertFalse(self.store.data_file.exists())
        self.rm.save_to_file()
        self.assertEqual(len(self.store.manager().records), 3)


if __name__ == "__main__":
    unittest.main()
