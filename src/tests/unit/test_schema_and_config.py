"""Unit tests for the small support modules: config, record.schema,
record.errors, gui.form_schema and gui.preferences."""

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import config
from gui import form_schema, preferences
from record import schema
from record.errors import DuplicateRecordError, RecordError, RecordStorageError, ReferencedRecordError


class TestRecordSchema(unittest.TestCase):
    """The stored field names are exactly those of the assignment brief."""

    def test_client_fields_match_the_brief(self):
        self.assertEqual(schema.CLIENT_FIELDS, (
            "ID", "Type", "Name", "Address Line 1", "Address Line 2", "Address Line 3",
            "City", "State", "Zip Code", "Country", "Phone Number"))

    def test_airline_fields_match_the_brief(self):
        self.assertEqual(schema.AIRLINE_FIELDS, ("ID", "Type", "Company Name"))

    def test_flight_fields_match_the_brief(self):
        self.assertEqual(schema.FLIGHT_KEY_FIELDS, ("Client_ID", "Airline_ID", "Date", "Start City", "End City"))
        self.assertEqual(schema.FLIGHT_FIELDS[0], "Type")

    def test_date_format_holds_date_and_time(self):
        parsed = datetime.strptime("2026-12-01 09:30", schema.DATE_FORMAT)
        self.assertEqual((parsed.hour, parsed.minute), (9, 30))
        self.assertEqual(len("2026-12-01"), schema.DAY_LENGTH)
        with self.assertRaises(ValueError):
            datetime.strptime("2026-12-01", schema.DATE_FORMAT)

    def test_link_keys_point_flights_at_clients_and_airlines(self):
        self.assertEqual(schema.LINK_KEY, {"Client": "Client_ID", "Airline": "Airline_ID"})


class TestErrors(unittest.TestCase):
    def test_hierarchy(self):
        for error in (DuplicateRecordError, ReferencedRecordError):
            self.assertTrue(issubclass(error, RecordError))
            self.assertTrue(issubclass(error, ValueError))
        self.assertTrue(issubclass(RecordStorageError, RecordError))

    def test_storage_error_keeps_path_and_cause(self):
        cause = OSError("disk full")
        error = RecordStorageError("records.jsonl", cause)
        self.assertIs(error.cause, cause)
        self.assertEqual(error.path, "records.jsonl")
        self.assertIn("disk full", str(error))


class TestConfig(unittest.TestCase):
    def test_paths_are_inside_the_project(self):
        self.assertEqual(config.DATA_FILE.suffix, ".jsonl")
        self.assertTrue(str(config.DATA_FILE).startswith(str(config.SRC_DIR)))
        self.assertTrue(config.INDEX_FILE.is_file())

    def test_backup_suffix_takes_a_timestamp(self):
        stamp = datetime(2026, 1, 2, 3, 4, 5).strftime(config.BACKUP_TIMESTAMP_FORMAT)
        self.assertIn(stamp, config.CORRUPT_BACKUP_SUFFIX.format(timestamp=stamp))

    def test_exit_codes_are_distinct(self):
        self.assertEqual(len({config.EXIT_OK, config.EXIT_ERROR, config.EXIT_MISSING_DEPENDENCY}), 3)


class TestFormSchema(unittest.TestCase):
    def test_every_form_field_has_a_spec_and_a_row(self):
        for record_type, fields in form_schema.FIELD_MAP.items():
            spec_names = [spec[0] for spec in form_schema.FIELD_SPECS[record_type]]
            row_names = [name for row in form_schema.FORM_ROWS[record_type] for name in row]
            self.assertEqual(sorted(spec_names), sorted(fields), record_type)
            self.assertEqual(sorted(row_names), sorted(fields), record_type)

    def test_flight_date_is_a_date_time_field(self):
        date_spec = next(s for s in form_schema.FIELD_SPECS[schema.FLIGHT] if s[0] == "Date")
        self.assertEqual(date_spec[2], form_schema.DATE)
        self.assertEqual(date_spec[5], schema.DATE_FORMAT_HINT)


class TestPreferences(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "settings.json"

    def test_defaults_when_no_file(self):
        self.assertEqual(preferences.PreferenceStore(self.path).values, preferences.DEFAULT_PREFERENCES)

    def test_set_validates_and_saves(self):
        store = preferences.PreferenceStore(self.path)
        store.set("theme", "dark")
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8"))["theme"], "dark")
        with self.assertRaises(ValueError):
            store.set("theme", "purple")
        with self.assertRaises(ValueError):
            store.set(preferences.PANEL_WIDTH, True)

    def test_damaged_or_unknown_values_fall_back_to_defaults(self):
        self.path.write_text('{"theme": "neon", "density": "compact"}', encoding="utf-8")
        values = preferences.PreferenceStore(self.path).values
        self.assertEqual((values["theme"], values["density"]), ("system", "compact"))
        self.path.write_text("not json", encoding="utf-8")
        with self.assertLogs("gui.preferences", "WARNING"):
            self.assertEqual(preferences.PreferenceStore(self.path).values, preferences.DEFAULT_PREFERENCES)


if __name__ == "__main__":
    unittest.main()
