"""Logging set-up: rotating log file, console, no duplicate handlers, unwritable folder."""

import logging
import unittest
from logging.handlers import RotatingFileHandler
from unittest import mock

import config
from app_logging import setup_logging
from tests.helpers import TempStore


def ours():
    return [h for h in logging.getLogger().handlers if getattr(h, "_travel_records_handler", False)]


class TestLogging(unittest.TestCase):
    def setUp(self):
        self.store = TempStore()
        self.addCleanup(self.store.cleanup)
        self.addCleanup(self.cleanup_handlers)

    @staticmethod
    def cleanup_handlers():
        for handler in ours():
            logging.getLogger().removeHandler(handler)
            handler.close()

    def test_messages_reach_the_rotating_file(self):
        log_file = self.store.folder / "logs" / "app.log"
        self.assertEqual(setup_logging(log_file=log_file, console=False), log_file)
        logging.getLogger("record.record").error("disk problem")
        for handler in ours():
            handler.flush()
        self.assertIn("ERROR    record.record: disk problem", log_file.read_text(encoding="utf-8"))
        handler = next(h for h in ours() if isinstance(h, RotatingFileHandler))
        self.assertEqual((handler.maxBytes, handler.backupCount), (config.LOG_FILE_MAX_BYTES, config.LOG_FILE_BACKUPS))

    def test_calling_twice_does_not_duplicate_handlers(self):
        log_file = self.store.folder / "app.log"
        setup_logging(log_file=log_file)
        setup_logging(log_file=log_file)
        self.assertEqual(len(ours()), 2)                                      # one console, one file

    def test_unwritable_log_folder_falls_back_to_console(self):
        with mock.patch("app_logging.RotatingFileHandler", side_effect=PermissionError("read-only")):
            self.assertIsNone(setup_logging(log_file=self.store.folder / "x.log"))
        self.assertEqual(len(ours()), 1)


if __name__ == "__main__":
    unittest.main()
