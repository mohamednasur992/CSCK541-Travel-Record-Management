"""Negative and error-injection tests: failures are forced into the storage, the log and the page calls.

Covers NFR-07 (invalid input never changes data), NFR-08 (the program keeps
running with a bad file), NFR-09 (an interrupted save loses nothing) and the
error handling behind FR-14, FR-22, FR-24 and FR-25.
"""

import copy
import errno
import json
import logging
import random
import threading
import unittest
from unittest import mock

from gui.bridge import WebApi
from record.errors import RecordStorageError
from record.record import RecordManager
from tests.helpers import AIRLINE_FORM, CLIENT_FORM, FLIGHT_FORM, StoreTestCase, TempStore


class TestSaveFailures(StoreTestCase):
    """A save that fails must leave the old file intact and no temporary files behind."""

    def setUp(self):
        super().setUp()
        self.create("Airline", AIRLINE_FORM)
        self.before = self.store.data_file.read_bytes()

    def temp_files(self):
        return [p for p in self.store.folder.iterdir() if p.name.endswith(".tmp")]

    def test_replace_fails(self):
        self.rm.records.append({"ID": 2, "Type": "Airline", "Company Name": "Unsaved"})
        with mock.patch("os.replace", side_effect=PermissionError(errno.EACCES, "locked")):
            with self.assertRaises(RecordStorageError):
                self.rm.save_to_file()
        self.assertEqual(self.store.data_file.read_bytes(), self.before)
        self.assertEqual(self.temp_files(), [])

    def test_no_space_left_when_creating_the_temporary_file(self):
        with mock.patch("tempfile.mkstemp", side_effect=OSError(errno.ENOSPC, "No space left on device")):
            with self.assertRaises(RecordStorageError) as caught:
                self.rm.save_to_file()
        self.assertIn("No space left", str(caught.exception))
        self.assertEqual(self.store.data_file.read_bytes(), self.before)

    def test_write_fails_halfway(self):
        self.rm.records.append({"ID": 2, "Type": "Airline", "Company Name": "Second"})
        real_dumps = json.dumps
        calls = []

        def fail_on_second(value, *args, **kwargs):
            calls.append(value)
            if len(calls) == 2:
                raise OSError(errno.EIO, "I/O error")
            return real_dumps(value, *args, **kwargs)

        with mock.patch("record.record.json.dumps", side_effect=fail_on_second):
            with self.assertRaises(RecordStorageError):
                self.rm.save_to_file()
        self.assertEqual(self.store.data_file.read_bytes(), self.before)
        self.assertEqual(self.temp_files(), [])

    def test_a_record_that_cannot_be_written_as_json_leaves_the_old_file_and_no_temp_file(self):
        self.rm.records.append({"ID": 2, "Type": "Airline", "Company Name": {"not", "json"}})
        with self.assertRaises(Exception):
            self.rm.save_to_file()
        self.assertEqual(self.store.data_file.read_bytes(), self.before)
        self.assertEqual(self.temp_files(), [])

    def test_the_page_keeps_the_change_reports_the_failure_and_recovers(self):
        with mock.patch("os.replace", side_effect=PermissionError(errno.EACCES, "locked")):
            result = self.api.create("Airline", {"ID": "2", "Company Name": "Air France (AF)"})
        self.assertTrue(result["ok"])
        self.assertIn("save_error", result)
        self.assertEqual(len(result["records"]["Airline"]), 2)               # change kept in memory
        self.assertEqual(self.store.data_file.read_bytes(), self.before)     # file untouched
        self.assertTrue(self.api.save_all()["ok"])                            # a later save succeeds
        self.assertEqual(len(self.file_lines()), 2)

    def test_save_all_reports_the_failure_to_the_page(self):
        with mock.patch("tempfile.mkstemp", side_effect=OSError(errno.EROFS, "Read-only file system")):
            result = self.api.save_all()
        self.assertFalse(result["ok"])
        self.assertIn("Read-only", result["error"])

    def test_every_changing_call_survives_a_failing_disk(self):
        self.create("Client", CLIENT_FORM)
        key = self.api.snapshot()["records"]["Airline"][0]["key"]
        with mock.patch("os.replace", side_effect=OSError(errno.EIO, "I/O error")):
            results = [
                self.api.create("Airline", {"ID": "5", "Company Name": "Five"}),
                self.api.update("Airline", key, {"ID": "1", "Company Name": "Renamed"}),
                self.api.delete("Airline", 5),
            ]
            undo = self.api.undo_delete()
        for result in results + [undo]:
            self.assertTrue(result["ok"], result)
            self.assertIn("save_error", result)


class TestDamagedFiles(unittest.TestCase):
    """Bad data files: the program starts, warns, and never destroys the original."""

    def setUp(self):
        self.store = TempStore()
        self.addCleanup(self.store.cleanup)

    def load(self, payload):
        self.store.data_file.write_bytes(payload)
        with self.assertLogs("record.record", level="ERROR"):
            manager = self.store.manager()
        return manager

    def assert_started_empty_with_backup(self, manager, payload):
        self.assertEqual(manager.records, [])
        self.assertEqual(len(manager.load_warnings), 1)
        backups = list(self.store.folder.glob("record.jsonl.corrupt-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), payload)

    def test_each_kind_of_damage_is_handled(self):
        good = b'{"ID": 1, "Type": "Airline", "Company Name": "A"}\n'
        damage = {
            "truncated line": good + b'{"ID": 2, "Type": "Airl',
            "binary garbage": bytes(range(128, 256)) * 4,
            "json array": b"[1, 2, 3]\n",
            "json scalar": b"42\n",
            "unknown type": b'{"ID": 1, "Type": "Hotel", "Name": "x"}\n',
            "missing type": b'{"ID": 1, "Name": "x"}\n',
            "null line": b"null\n",
            "invalid utf-8": b'{"ID": 1, "Type": "Airline", "Company Name": "\xff\xfe"}\n',
        }
        for label, payload in damage.items():
            with self.subTest(damage=label):
                for old in self.store.folder.glob("record.jsonl.corrupt-*"):
                    old.unlink()
                manager = self.load(payload)
                self.assert_started_empty_with_backup(manager, payload)

    def test_an_empty_file_is_not_damage(self):
        self.store.data_file.write_bytes(b"")
        manager = self.store.manager()
        self.assertEqual((manager.records, manager.load_warnings), ([], []))
        self.assertEqual(list(self.store.folder.glob("*.corrupt-*")), [])

    def test_the_path_is_a_folder_not_a_file(self):
        self.store.data_file.mkdir()
        with self.assertLogs("record.record", level="ERROR"):
            manager = self.store.manager()
        self.assertEqual(manager.records, [])
        self.assertTrue(manager.load_warnings)

    def test_the_backup_itself_fails(self):
        self.store.data_file.write_text("{broken", encoding="utf-8")
        with mock.patch("shutil.copy2", side_effect=OSError(errno.EACCES, "denied")), \
                self.assertLogs("record.record", level="ERROR"):
            manager = self.store.manager()
        self.assertEqual(manager.records, [])
        self.assertNotIn(".corrupt-", manager.load_warnings[0])
        self.assertEqual(self.store.data_file.read_text(encoding="utf-8"), "{broken")

    def test_a_damaged_file_is_not_overwritten_before_the_user_changes_something(self):
        self.store.data_file.write_text("{broken", encoding="utf-8")
        with self.assertLogs("record.record", level="ERROR"):
            self.store.manager()
        self.assertEqual(self.store.data_file.read_text(encoding="utf-8"), "{broken")

    def test_the_bridge_still_starts_with_a_damaged_file(self):
        manager = self.load(b"\x00\x01\x02")
        api = WebApi(manager, warnings=manager.load_warnings, settings_path=self.store.folder / "s.json")
        boot = api.bootstrap()
        self.assertTrue(boot["ok"])
        self.assertEqual(boot["records"], {"Client": [], "Airline": [], "Flight": []})
        self.assertTrue(boot["warnings"])


class TestHostileAndMalformedInput(StoreTestCase):
    """The page is the only input path; whatever it sends, nothing is stored wrongly or crashes."""

    def snapshot(self):
        return copy.deepcopy(self.rm.records)

    def test_malformed_arguments_give_an_error_result_not_an_exception(self):
        self.seed()
        before = self.snapshot()
        calls = [
            lambda: self.api.create(None, None), lambda: self.api.create("Client", None),
            lambda: self.api.create("Client", "text"), lambda: self.api.create("Client", [1, 2]),
            lambda: self.api.update("Client", None, {}), lambda: self.api.update("Flight", "x", {}),
            lambda: self.api.update("Flight", [1, 2, 3, 4, 5], CLIENT_FORM),
            lambda: self.api.delete(None, None), lambda: self.api.delete("Flight", {"a": 1}),
            lambda: self.api.delete_check("Client", "abc"), lambda: self.api.get("Airline", [1]),
            lambda: self.api.search("Client", None, None), lambda: self.api.search(42, "x"),
            lambda: self.api.set_preference(None, None), lambda: self.api.set_preference("theme", ["dark"]),
            lambda: self.api.log_client_error(None), lambda: self.api.set_form_dirty(None),
        ]
        for number, call in enumerate(calls):
            with self.subTest(call=number):
                result = call()
                self.assertIsInstance(result, dict)
                self.assertIn("ok", result)
                json.dumps(result)                                  # always JSON-serialisable
        self.assertEqual(self.rm.records, before)

    def test_hostile_text_is_stored_as_plain_text_and_returned_unchanged(self):
        hostile = ["<script>alert(1)</script>", "'; DROP TABLE clients; --", "{{7*7}}", "${jndi:ldap://x}",
                   "<img src=x onerror=alert(1)>", "line1\nline2", "tab\there", "‮right-to-left",
                   "null\x00byte", "emoji 😀✈️", "Robert'); --"]
        for number, text in enumerate(hostile, start=1):
            with self.subTest(text=text):
                result = self.api.create("Airline", {"ID": str(number), "Company Name": text})
                self.assertTrue(result["ok"], result)
                self.assertEqual(result["record"]["Company Name"], text.strip())
        again = self.store.manager()
        self.assertEqual([r["Company Name"] for r in again.records], [t.strip() for t in hostile])

    def test_numbers_and_booleans_sent_instead_of_text_are_handled(self):
        result = self.api.create("Airline", {"ID": 7, "Company Name": 12345})
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["record"]["Company Name"], "12345")
        self.assertFalse(self.api.create("Airline", {"ID": True, "Company Name": "x"})["ok"] and False)

    def test_extra_unknown_fields_are_ignored_not_stored(self):
        self.create("Airline", {**AIRLINE_FORM, "Admin": "yes", "__proto__": {"x": 1}, "Type": "Client"})
        self.assertEqual(set(self.rm.records[0]), {"ID", "Type", "Company Name"})

    def test_huge_input_is_rejected_quickly(self):
        result = self.api.create("Airline", {"ID": "9" * 5000, "Company Name": "x" * 1_000_000})
        self.assertFalse(result["ok"])
        self.assertEqual(self.rm.records, [])

    def test_random_invalid_forms_never_change_the_data_or_the_file(self):
        """NFR-07: 300 random bad inputs leave memory and disk exactly as they were."""
        self.seed()
        before_memory, before_file = self.snapshot(), self.store.data_file.read_bytes()
        rng = random.Random(541)
        junk = ["", " ", "0", "-1", "abc", "9" * 30, "x" * 150, "2026-02-30 09:30", "<b>", "None", "12:61"]
        templates = {"Client": CLIENT_FORM, "Airline": AIRLINE_FORM, "Flight": FLIGHT_FORM}
        for _ in range(300):
            record_type = rng.choice(list(templates))
            form = dict(templates[record_type])
            for field in rng.sample(list(form), k=rng.randint(1, len(form))):
                form[field] = rng.choice(junk)
            if record_type == "Flight" and form == FLIGHT_FORM:
                continue
            result = self.api.create(record_type, form)
            if result["ok"]:                                         # a lucky valid combination
                before_memory, before_file = self.snapshot(), self.store.data_file.read_bytes()
        self.assertEqual(self.snapshot(), before_memory)
        self.assertEqual(self.store.data_file.read_bytes(), before_file)


class TestInjectedFailuresInsideTheApplication(StoreTestCase):
    """Unexpected exceptions are contained, logged and leave the window usable."""

    def test_an_exception_inside_the_record_manager_becomes_an_error_result(self):
        with mock.patch.object(RecordManager, "add_client", side_effect=RuntimeError("boom")), \
                self.assertLogs("gui.bridge", level="ERROR") as logs:
            result = self.api.create("Client", CLIENT_FORM)
        self.assertFalse(result["ok"])
        self.assertIn("boom", result["error"])
        self.assertTrue(any("Traceback" in line for line in logs.output))
        self.assertEqual(self.rm.records, [])
        self.assertTrue(self.api.create("Client", CLIENT_FORM)["ok"])        # next call works

    def test_every_public_call_is_contained(self):
        self.seed()
        with mock.patch.object(WebApi, "_records", side_effect=RuntimeError("injected")), \
                self.assertLogs("gui.bridge", level="ERROR"):
            for call in (self.api.bootstrap, self.api.snapshot, self.api.summary,
                         lambda: self.api.search("Client", "x"),
                         lambda: self.api.delete_check("Client", 1)):
                result = call()
                self.assertFalse(result["ok"])
                self.assertIn("injected", result["error"])

    def test_a_broken_log_destination_does_not_break_the_application(self):
        class BrokenStream:
            def write(self, _text):
                raise OSError(errno.EIO, "log disk failed")

            def flush(self):
                raise OSError(errno.EIO, "log disk failed")

        root = logging.getLogger()
        handler = logging.StreamHandler(BrokenStream())
        root.addHandler(handler)
        previous_level, previous_raise = root.level, logging.raiseExceptions
        root.setLevel(logging.DEBUG)
        logging.raiseExceptions = False          # Python then drops the message instead of raising
        self.addCleanup(root.removeHandler, handler)
        self.addCleanup(root.setLevel, previous_level)
        self.addCleanup(setattr, logging, "raiseExceptions", previous_raise)
        result = self.api.create("Airline", AIRLINE_FORM)
        self.assertTrue(result["ok"], result)
        self.assertEqual(len(self.file_lines()), 1)

    def test_preferences_survive_a_damaged_settings_file_and_a_failing_write(self):
        settings = self.store.folder / "settings.json"
        settings.write_text("{ not json", encoding="utf-8")
        api, _ = self.store.api()
        self.assertEqual(api.preferences()["preferences"]["theme"], "system")
        with mock.patch("os.replace", side_effect=OSError(errno.EACCES, "locked")):
            result = api.set_preference("theme", "dark")
        self.assertFalse(result["ok"])
        self.assertEqual(result["preferences"]["theme"], "dark")             # applies for this session
        self.assertEqual(settings.read_text(encoding="utf-8"), "{ not json")
        self.assertEqual([p for p in self.store.folder.iterdir() if p.name.endswith(".tmp")], [])

    def test_a_preference_value_of_the_wrong_kind_is_refused(self):
        for name, value in (("theme", "neon"), ("panel_width", 5), ("panel_width", True),
                            ("density", None), ("unknown", 1)):
            with self.subTest(name=name, value=value):
                self.assertFalse(self.api.set_preference(name, value)["ok"])


class TestConcurrency(StoreTestCase):
    """pywebview runs every call on its own thread: the lock must keep the data consistent."""

    def run_threads(self, target, count):
        threads = [threading.Thread(target=target, args=(n,)) for n in range(count)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
            self.assertFalse(thread.is_alive())

    def test_parallel_creates_with_distinct_ids_all_succeed(self):
        results = []

        def create(number):
            results.append(self.api.create("Airline", {"ID": str(number + 1), "Company Name": f"Air {number}"}))

        self.run_threads(create, 40)
        self.assertTrue(all(r["ok"] for r in results))
        self.assertEqual(sorted(r["ID"] for r in self.rm.records), list(range(1, 41)))
        self.assertEqual(len(self.store.manager().records), 40)

    def test_parallel_creates_of_the_same_id_let_exactly_one_win(self):
        results = []
        self.run_threads(lambda n: results.append(self.api.create("Airline", {"ID": "1", "Company Name": f"A{n}"})), 25)
        self.assertEqual(sum(1 for r in results if r["ok"]), 1)
        self.assertEqual(len(self.rm.records), 1)

    def test_reads_during_writes_always_see_a_consistent_list(self):
        self.seed()
        problems = []

        def worker(number):
            for step in range(15):
                if number % 2:
                    self.api.create("Airline", {"ID": str(100 + number * 20 + step), "Company Name": f"W{number}-{step}"})
                else:
                    snap = self.api.snapshot()
                    if not snap["ok"] or snap["summary"]["airlines"] != len(snap["records"]["Airline"]):
                        problems.append(snap)

        self.run_threads(worker, 8)
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
