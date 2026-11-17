"""The entry point: start-up check, missing dependency, final save and exit codes."""

import functools
import logging
import unittest
from unittest import mock

import config
import main
from app_logging import setup_logging
from record.errors import RecordStorageError
from tests.helpers import TempStore


class TestMain(unittest.TestCase):
    def setUp(self):
        self.store = TempStore()
        self.addCleanup(self.store.cleanup)
        self.log_file = self.store.folder / "logs" / "app.log"
        self.addCleanup(self.remove_handlers)

    @staticmethod
    def remove_handlers():
        for handler in list(logging.getLogger().handlers):
            if getattr(handler, "_travel_records_handler", False):
                logging.getLogger().removeHandler(handler)
                handler.close()

    def start(self, run=None, available=True):
        with mock.patch("main.webview_available", return_value=available), \
                mock.patch("main.run", run or mock.Mock(return_value=config.EXIT_OK)) as fake_run, \
                mock.patch("main.setup_logging", functools.partial(setup_logging, console=False)):
            code = main.main(data_file=self.store.data_file, log_file=self.log_file)
        return code, fake_run

    def test_missing_pywebview_explains_and_exits(self):
        code, fake_run = self.start(available=False)
        self.assertEqual(code, config.EXIT_MISSING_DEPENDENCY)
        fake_run.assert_not_called()
        self.assertIn("pip install -r requirements.txt", self.log_file.read_text(encoding="utf-8"))

    def test_normal_run_loads_opens_and_saves(self):
        self.store.data_file.write_text('{"ID": 1, "Type": "Airline", "Company Name": "A"}\n', encoding="utf-8")
        code, fake_run = self.start()
        self.assertEqual(code, config.EXIT_OK)
        manager = fake_run.call_args.args[0]
        self.assertEqual(len(manager.records), 1)                            # start-up check
        self.assertEqual(fake_run.call_args.kwargs["warnings"], [])
        self.assertIn("Loaded 1 record", self.log_file.read_text(encoding="utf-8"))

    def test_keyboard_interrupt_still_saves(self):
        def interrupted(manager, warnings):
            manager.add_airline(5, "Saved anyway")
            raise KeyboardInterrupt
        code, _ = self.start(run=interrupted)
        self.assertEqual(code, config.EXIT_OK)
        self.assertIn("Saved anyway", self.store.data_file.read_text(encoding="utf-8"))

    def test_unexpected_error_is_logged_with_traceback_and_records_saved(self):
        def crash(manager, warnings):
            manager.add_airline(6, "Kept")
            raise RuntimeError("window back-end failed")
        code, _ = self.start(run=crash)
        self.assertEqual(code, config.EXIT_ERROR)
        log = self.log_file.read_text(encoding="utf-8")
        self.assertIn("Traceback", log)
        self.assertIn("window back-end failed", log)
        self.assertIn("Kept", self.store.data_file.read_text(encoding="utf-8"))

    def test_failed_final_save_is_reported(self):
        with mock.patch("record.record.RecordManager.save_to_file",
                        side_effect=RecordStorageError("f", OSError("disk full"))):
            code, _ = self.start()
        self.assertEqual(code, config.EXIT_ERROR)
        self.assertIn("could not be saved on exit", self.log_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
