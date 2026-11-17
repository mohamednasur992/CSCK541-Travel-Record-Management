"""Unit and integration tests for FR-22 to FR-27: the JSON Lines file, start-up, saving, upgrading."""

import functools
import json
import logging
import unittest
from pathlib import Path
from unittest import mock

import config
import main
from app_logging import setup_logging
from gui.bridge import WebApi
from record.record import RecordManager
from tests.helpers import AIRLINE_FORM, CLIENT_FORM, FLIGHT_FORM, StoreTestCase, TempStore

STATIC = Path(config.STATIC_DIR)


class TestFileFormat(StoreTestCase):
    """FR-22: UTF-8 JSON Lines, one record per line, written after every change."""

    def test_the_file_is_one_json_object_per_line(self):
        self.seed()
        lines = self.file_lines()
        self.assertEqual(len(lines), 3)
        records = [json.loads(line) for line in lines]
        self.assertTrue(all(isinstance(record, dict) for record in records))
        self.assertEqual([r["Type"] for r in records], ["Client", "Airline", "Flight"])

    def test_the_file_is_not_one_big_json_array(self):
        self.seed()
        text = self.store.data_file.read_text(encoding="utf-8")
        self.assertFalse(text.lstrip().startswith("["))
        self.assertTrue(text.endswith("\n"))

    def test_non_ascii_text_survives_a_save_and_reload(self):
        name = "José Ñandú 東京 Ольга"
        self.create("Client", {**CLIENT_FORM, "Name": name, "City": "São Paulo"})
        again = self.store.manager()
        self.assertEqual((again.records[0]["Name"], again.records[0]["City"]), (name, "São Paulo"))
        self.store.data_file.read_bytes().decode("utf-8")                # valid UTF-8

    def test_the_file_is_written_after_every_create_update_and_delete(self):
        self.create("Airline", AIRLINE_FORM)
        self.assertEqual(len(self.file_lines()), 1)
        self.create("Airline", {"ID": "2", "Company Name": "Air France (AF)"})
        self.assertEqual(len(self.file_lines()), 2)
        self.api.update("Airline", 2, {"ID": "2", "Company Name": "Air Nouveau"})
        self.assertIn("Air Nouveau", self.store.data_file.read_text(encoding="utf-8"))
        self.api.delete("Airline", 1)
        self.assertEqual(len(self.file_lines()), 1)
        self.assertNotIn("British", self.store.data_file.read_text(encoding="utf-8"))

    def test_rejected_actions_do_not_touch_the_file(self):
        self.create("Airline", AIRLINE_FORM)
        before = self.store.data_file.read_bytes()
        self.api.create("Airline", AIRLINE_FORM)                          # duplicate
        self.api.update("Airline", 9, AIRLINE_FORM)                       # missing
        self.assertEqual(self.store.data_file.read_bytes(), before)


class TestStartUp(unittest.TestCase):
    """FR-23, FR-24: look for the file at start-up; survive a bad one."""

    def setUp(self):
        self.store = TempStore()
        self.addCleanup(self.store.cleanup)

    def test_an_existing_file_is_loaded(self):
        self.store.data_file.write_text('{"ID": 4, "Type": "Airline", "Company Name": "Loaded"}\n',
                                        encoding="utf-8")
        manager = self.store.manager()
        self.assertEqual([r["Company Name"] for r in manager.records], ["Loaded"])

    def test_no_file_means_an_empty_start_and_the_folder_is_created(self):
        folder = self.store.folder / "not" / "yet"
        manager = RecordManager(filepath=folder / "record.jsonl")
        self.assertEqual(manager.records, [])
        self.assertTrue(folder.is_dir())

    def test_a_damaged_file_gives_an_empty_start_a_warning_and_a_backup(self):
        self.store.data_file.write_text('{"ID": 1, "Type": "Airline", "Company Name": "A"}\n{broken\n',
                                        encoding="utf-8")
        with self.assertLogs("record.record", level="ERROR"):
            manager = self.store.manager()
        self.assertEqual(manager.records, [])
        self.assertEqual(len(manager.load_warnings), 1)
        backups = list(self.store.folder.glob("record.jsonl.corrupt-*"))
        self.assertEqual(len(backups), 1)
        self.assertIn("broken", backups[0].read_text(encoding="utf-8"))

    def test_the_warning_reaches_the_page(self):
        self.store.data_file.write_text("garbage", encoding="utf-8")
        with self.assertLogs("record.record", level="ERROR"):
            manager = self.store.manager()
        api = WebApi(manager, warnings=manager.load_warnings, settings_path=self.store.folder / "s.json")
        self.assertEqual(api.bootstrap()["warnings"], manager.load_warnings)


class TestSavingOnExit(unittest.TestCase):
    """FR-25: records are saved on exit, including after Ctrl+C."""

    def setUp(self):
        self.store = TempStore()
        self.addCleanup(self.store.cleanup)
        self.addCleanup(self.remove_handlers)

    @staticmethod
    def remove_handlers():
        for handler in list(logging.getLogger().handlers):
            if getattr(handler, "_travel_records_handler", False):
                logging.getLogger().removeHandler(handler)
                handler.close()

    def start(self, run):
        with mock.patch("main.webview_available", return_value=True), \
                mock.patch("main.run", run), \
                mock.patch("main.setup_logging", functools.partial(setup_logging, console=False)):
            return main.main(data_file=self.store.data_file, log_file=self.store.folder / "app.log")

    def test_records_made_through_the_bridge_are_on_disk_when_the_window_closes(self):
        def session(manager, warnings):
            api = WebApi(manager, warnings=warnings, settings_path=self.store.folder / "s.json")
            self.assertTrue(api.create("Airline", AIRLINE_FORM)["ok"])
            return config.EXIT_OK
        self.assertEqual(self.start(session), config.EXIT_OK)
        self.assertEqual(self.store.manager().records[0]["Company Name"], "British Airways (BA)")

    def test_a_record_held_only_in_memory_is_saved_after_ctrl_c(self):
        def session(manager, warnings):
            manager.add_airline(3, "Memory only")
            raise KeyboardInterrupt
        self.assertEqual(self.start(session), config.EXIT_OK)
        self.assertEqual(self.store.manager().records[0]["Company Name"], "Memory only")

    def test_a_manual_save_writes_everything_at_once(self):
        api, manager = self.store.api()
        manager.add_airline(1, "Direct")                                 # bypasses the page's autosave
        self.assertFalse(self.store.data_file.exists())
        self.assertTrue(api.save_all()["ok"])
        self.assertEqual(len(self.store.data_file.read_text(encoding="utf-8").splitlines()), 1)


class TestReloadAndUpgrade(StoreTestCase):
    """FR-26: records reload unchanged; earlier-version records are upgraded."""

    def test_a_full_set_of_records_reloads_identically_with_the_same_types(self):
        self.seed()
        self.create("Flight", {**FLIGHT_FORM, "Date": "2026-12-02 07:05", "Start City": "Rome",
                               "End City": "Oslo"})
        again = self.store.manager()
        self.assertEqual(again.records, self.rm.records)
        for record in again.records:
            for key in ("ID", "Client_ID", "Airline_ID"):
                if key in record:
                    self.assertIsInstance(record[key], int)

    def test_earlier_version_records_are_upgraded_and_rewritten_in_the_new_form(self):
        legacy = [{"id": 2, "type": "Airline", "company_name": "Old Air"},
                  {"id": 1, "type": "Client", "name": "Abe", "address": "1 Road", "city": "Leeds",
                   "phone_number": "+44 113 000 0000", "email": "gone@example.com"},
                  {"type": "Flight", "client_id": 1, "airline_id": 2, "date": "2026-11-09",
                   "start_city": "Leeds", "end_city": "Oslo"}]
        self.store.data_file.write_text("".join(json.dumps(r) + "\n" for r in legacy), encoding="utf-8")
        api, manager = self.store.api()
        self.assertEqual(manager.load_warnings, [])
        client = api.get("Client", 1)["record"]
        self.assertEqual((client["Address Line 1"], client["City"], client["Country"]), ("1 Road", "Leeds", ""))
        self.assertEqual(api.snapshot()["records"]["Flight"][0]["Date"], "2026-11-09 00:00")
        self.assertTrue(api.save_all()["ok"])
        for line in self.store.data_file.read_text(encoding="utf-8").splitlines():
            self.assertTrue(all(key[0].isupper() for key in json.loads(line)), line)
        self.assertNotIn("gone@example.com", self.store.data_file.read_text(encoding="utf-8"))


class TestLogo(unittest.TestCase):
    """FR-27: the logo is shown when present; the program does not depend on it."""

    def test_the_logo_file_is_a_png_and_the_page_shows_it(self):
        logo = STATIC / "assets" / "Logo.png"
        self.assertEqual(logo.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
        self.assertIn('src="assets/Logo.png"', (STATIC / "index.html").read_text(encoding="utf-8"))

    def test_no_python_module_needs_the_logo_file(self):
        src = Path(config.SRC_DIR)
        for path in src.rglob("*.py"):
            if "tests" in path.parts:
                continue
            self.assertNotIn("Logo.png", path.read_text(encoding="utf-8"), path.name)

    def test_the_bridge_works_whether_or_not_the_logo_exists(self):
        store = TempStore()
        self.addCleanup(store.cleanup)
        api, _ = store.api()
        self.assertTrue(api.bootstrap()["ok"])


if __name__ == "__main__":
    unittest.main()
