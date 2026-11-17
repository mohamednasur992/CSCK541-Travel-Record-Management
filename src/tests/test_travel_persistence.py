"""RecordManager persistence: JSON Lines save/load, start-up check, damaged files, failed saves."""

import json
import os
import unittest
from unittest import mock

import config
from record.errors import RecordStorageError
from record.record import RecordManager
from tests.helpers import TempStore, add_sample_records


class TestPersistence(unittest.TestCase):
    def setUp(self):
        self.store = TempStore()
        self.addCleanup(self.store.cleanup)

    def test_save_and_load_round_trip_keeps_types(self):
        rm = self.store.manager()
        add_sample_records(rm)
        rm.save_to_file()
        lines = self.store.data_file.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 4)                              # one JSON object per line
        self.assertEqual(json.loads(lines[0])["Type"], "Client")
        again = self.store.manager()
        self.assertEqual(again.records, rm.records)
        self.assertIsInstance(again.records[3]["Client_ID"], int)

    def test_missing_file_starts_empty_and_creates_folder(self):
        rm = RecordManager(filepath=self.store.folder / "new" / "record.jsonl")
        self.assertEqual((rm.records, rm.load_warnings), ([], []))
        self.assertTrue((self.store.folder / "new").is_dir())

    def test_earlier_format_records_are_upgraded_to_brief_names(self):
        old = [{"id": 1, "type": "Client", "name": "Abe", "email": "a@b.c", "phone_number": "+27 11 000 0000",
                "city": "Johannesburg", "address": "100 9th St", "passport_number": "X", "nationality": "SA",
                "emergency_contact": ""},
               {"id": 1, "type": "Airline", "company_name": "Emirates (EK)"},
               {"type": "Flight", "client_id": 1, "airline_id": 1, "date": "2026-11-09",
                "start_city": "Johannesburg", "end_city": "Moscow"}]
        self.store.data_file.write_text("".join(json.dumps(r) + "\n" for r in old), encoding="utf-8")
        rm = self.store.manager()
        self.assertEqual(rm.load_warnings, [])
        client, airline, flight = rm.records
        self.assertEqual(list(client), ["ID", "Type", "Name", "Address Line 1", "Address Line 2", "Address Line 3",
                                        "City", "State", "Zip Code", "Country", "Phone Number"])
        self.assertEqual((client["Address Line 1"], client["Country"]), ("100 9th St", ""))
        self.assertEqual(airline, {"ID": 1, "Type": "Airline", "Company Name": "Emirates (EK)"})
        self.assertEqual(flight["Date"], "2026-11-09 00:00")
        self.assertEqual(flight["Start City"], "Johannesburg")

    def test_blank_lines_are_ignored(self):
        self.store.data_file.write_text('{"ID": 1, "Type": "Airline", "Company Name": "A"}\n\n', encoding="utf-8")
        self.assertEqual(len(self.store.manager().records), 1)

    def test_damaged_file_is_backed_up_and_program_starts_empty(self):
        self.store.data_file.write_text("{ not json", encoding="utf-8")
        with self.assertLogs("record.record", level="ERROR"):
            rm = self.store.manager()
        self.assertEqual(rm.records, [])
        self.assertEqual(len(rm.load_warnings), 1)
        backups = list(self.store.folder.glob("record.jsonl.corrupt-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(encoding="utf-8"), "{ not json")
        self.assertIn(backups[0].name, rm.load_warnings[0])

    def test_line_that_is_not_a_record_counts_as_damage(self):
        self.store.data_file.write_text('{"ID": 1, "Type": "Airline", "Company Name": "A"}\n[1, 2]\n',
                                        encoding="utf-8")
        rm = self.store.manager()
        self.assertEqual(rm.records, [])
        self.assertIn("line 2", rm.load_warnings[0])

    def test_unreadable_file_still_starts(self):
        self.store.data_file.write_text("x", encoding="utf-8")
        with mock.patch("record.record.open", side_effect=PermissionError("denied")), \
                mock.patch("record.record.shutil.copy2", side_effect=OSError("no space")):
            rm = self.store.manager()
        self.assertEqual(rm.records, [])
        self.assertNotIn("kept as", rm.load_warnings[0])          # backup failed and says nothing false

    def test_failed_save_raises_and_keeps_the_old_file(self):
        rm = self.store.manager()
        add_sample_records(rm)
        rm.save_to_file()
        before = self.store.data_file.read_text(encoding="utf-8")
        rm.records.clear()
        with mock.patch("record.record.os.replace", side_effect=OSError("disk full")), \
                self.assertRaises(RecordStorageError) as caught:
            rm.save_to_file()
        self.assertIn("disk full", str(caught.exception))
        self.assertEqual(self.store.data_file.read_text(encoding="utf-8"), before)
        self.assertEqual([p.name for p in self.store.folder.iterdir()], ["record.jsonl"])   # no temp left

    def test_default_location_is_the_configured_data_file(self):
        self.assertEqual(RecordManager.__init__.__defaults__[0], config.DATA_FILE)
        self.assertEqual(config.DATA_FILE.name, "record.jsonl")

    def test_save_creates_missing_folder(self):
        rm = RecordManager(filepath=self.store.folder / "a" / "b.jsonl")
        os.rmdir(self.store.folder / "a")
        rm.save_to_file()
        self.assertTrue((self.store.folder / "a" / "b.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
