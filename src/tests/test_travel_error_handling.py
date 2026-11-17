"""Error handling in the bridge: field validation, contained failures and logging."""

import unittest
from unittest import mock

from record.errors import RecordStorageError
from tests.helpers import AIRLINE_FORM, CLIENT_FORM, FLIGHT_FORM, TempStore, add_sample_records


class BridgeTestCase(unittest.TestCase):
    def setUp(self):
        self.store = TempStore()
        self.addCleanup(self.store.cleanup)
        self.api, self.rm = self.store.api()
        add_sample_records(self.rm)


class TestValidationMessages(BridgeTestCase):
    def assert_rejected(self, record_type, data, field, words):
        result = self.api.create(record_type, data)
        self.assertFalse(result["ok"])
        self.assertIn(field, result["errors"])
        self.assertIn(words.lower(), result["errors"][field].lower())
        return result

    def test_required_fields(self):
        self.assert_rejected("Client", {**CLIENT_FORM, "ID": "5", "Name": " "}, "Name", "is required")
        self.assert_rejected("Flight", {**FLIGHT_FORM, "Client_ID": ""}, "Client_ID", "Select an existing client")

    def test_formats_and_lengths(self):
        self.assert_rejected("Client", {**CLIENT_FORM, "ID": "5", "Phone Number": "call me"}, "Phone Number", "digits")
        self.assert_rejected("Client", {**CLIENT_FORM, "ID": "0"}, "ID", "1 or more")
        self.assert_rejected("Client", {**CLIENT_FORM, "ID": "5", "Name": "x" * 101}, "Name", "at most 100")
        self.assert_rejected("Flight", {**FLIGHT_FORM, "Date": "01/12/2026"}, "Date", "YYYY-MM-DD")
        self.assert_rejected("Flight", {**FLIGHT_FORM, "Date": "2026-12-01"}, "Date", "HH:MM")   # time is required
        self.assert_rejected("Client", {**CLIENT_FORM, "ID": "5", "Zip Code": "9" * 21}, "Zip Code", "at most 20")
        self.assert_rejected("Flight", {**FLIGHT_FORM, "End City": " london "}, "End City", "differ")

    def test_integrity_rules(self):
        self.assert_rejected("Client", CLIENT_FORM, "ID", "already exists")
        self.assert_rejected("Airline", {"ID": "9", "Company Name": "british airways (ba)"}, "Company Name", "already uses")
        self.assert_rejected("Flight", {**FLIGHT_FORM, "Airline_ID": "8"}, "Airline_ID", "no longer exists")
        result = self.assert_rejected("Flight", {**FLIGHT_FORM, "Airline_ID": "2", "Start City": "Berlin",
                                                 "End City": "Rome"}, "Start City", "Paris")
        self.assertTrue(result["messages"])

    def test_rejected_input_changes_nothing_and_is_logged(self):
        before = [dict(r) for r in self.rm.records]
        with self.assertLogs("gui.bridge", level="INFO") as logs:
            self.api.create("Client", {**CLIENT_FORM, "ID": "5", "Address Line 1": ""})
        self.assertEqual(self.rm.records, before)
        self.assertIn("Address Line 1", logs.output[0])
        self.assertNotIn("Ada", "".join(logs.output))                    # no personal data in the log

    def test_unknown_record_type(self):
        self.assertFalse(self.api.create("Hotel", {})["ok"])
        self.assertFalse(self.api.search("Hotel")["ok"])
        self.assertFalse(self.api.search("Client", "x", "Shoe size")["ok"])

    def test_missing_records(self):
        self.assertIn("No client", self.api.get("Client", 42)["error"])
        self.assertFalse(self.api.get("Client", "abc")["ok"])
        self.assertFalse(self.api.get("Flight", [1, 2])["ok"])
        self.assertFalse(self.api.update("Airline", 42, AIRLINE_FORM)["ok"])
        self.assertFalse(self.api.delete("Airline", 42)["ok"])
        self.assertFalse(self.api.undo_delete()["ok"])


class TestContainedFailures(BridgeTestCase):
    def test_unexpected_exception_becomes_a_logged_error_result(self):
        with mock.patch.object(self.rm, "add_airline", side_effect=RuntimeError("boom")), \
                self.assertLogs("gui.bridge", level="ERROR") as logs:
            result = self.api.create("Airline", {"ID": "5", "Company Name": "New Air"})
        self.assertFalse(result["ok"])
        self.assertIn("boom", result["error"])
        self.assertIn("Traceback", "\n".join(logs.output))
        self.assertEqual(self.api.search("Airline")["ok"], True)        # the lock was released

    def test_save_failure_after_a_change_is_reported_but_change_kept(self):
        failure = RecordStorageError(self.store.data_file, OSError("disk full"))
        with mock.patch.object(self.rm, "save_to_file", side_effect=failure):
            result = self.api.create("Airline", {"ID": "5", "Company Name": "New Air"})
            self.assertTrue(result["ok"])
            self.assertIn("disk full", result["save_error"])
            self.assertIsNotNone(self.rm.get_record_by_id(5, "Airline"))
            saved = self.api.save_all()
        self.assertFalse(saved["ok"])
        self.assertIn("disk full", saved["error"])

    def test_page_errors_are_logged_and_truncated(self):
        with self.assertLogs("gui.bridge", level="ERROR") as logs:
            self.assertTrue(self.api.log_client_error("x" * 5000, "app.js", 12)["ok"])
        self.assertIn("app.js:12", logs.output[0])
        self.assertLess(len(logs.output[0]), 2300)

    def test_blocked_delete_message(self):
        result = self.api.delete("Client", 1)
        self.assertEqual((result["ok"], result["blocked"]), (False, True))

    def test_preference_errors(self):
        self.assertFalse(self.api.set_preference("theme", "neon")["ok"])
        with mock.patch("gui.preferences.os.replace", side_effect=OSError("read-only")):
            result = self.api.set_preference("theme", "dark")
        self.assertIn("not saved", result["error"])
        self.assertEqual(result["preferences"]["theme"], "dark")
        self.assertEqual(list(self.store.folder.glob(".settings-*")), [])


if __name__ == "__main__":
    unittest.main()
