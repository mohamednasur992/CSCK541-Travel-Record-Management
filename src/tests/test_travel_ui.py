"""What the page is given to display: start-up data, rows, choices, summary and preferences."""

import json
import unittest

from gui.form_schema import ALL_FIELDS, FIELD_MAP, FIELD_SPECS, FORM_ROWS
from gui.preferences import DEFAULT_PREFERENCES, PreferenceStore
from tests.helpers import TempStore, add_sample_records


class TestPageData(unittest.TestCase):
    def setUp(self):
        self.store = TempStore()
        self.addCleanup(self.store.cleanup)
        self.api, self.rm = self.store.api()
        add_sample_records(self.rm)

    def test_bootstrap_describes_every_form(self):
        boot = self.api.bootstrap()
        self.assertTrue(boot["ok"])
        self.assertEqual(boot["form_rows"], FORM_ROWS)
        self.assertEqual([f["name"] for f in boot["fields"]["Airline"]], ["ID", "Company Name"])
        self.assertEqual(boot["search_fields"]["Flight"][0]["value"], ALL_FIELDS)
        json.dumps(boot)                                           # everything is JSON for the page

    def test_form_schema_is_consistent(self):
        for record_type, specs in FIELD_SPECS.items():
            names = [spec[0] for spec in specs]
            self.assertEqual(set(names), set(FIELD_MAP[record_type]))
            self.assertEqual(sorted(n for row in FORM_ROWS[record_type] for n in row), sorted(names))

    def test_rows_carry_names_keys_and_counts(self):
        snap = self.api.snapshot()
        flight = snap["records"]["Flight"][0]
        self.assertEqual((flight["client_name"], flight["airline_name"]), ("Ada Lovelace", "British Airways (BA)"))
        self.assertEqual(flight["key"], [1, 1, "2026-12-01 09:30", "London", "Paris"])
        self.assertTrue(flight["upcoming"])
        self.assertEqual(snap["records"]["Client"][0]["flights"], 1)
        self.assertEqual(snap["next_id"], {"Client": 2, "Airline": 3})
        self.assertIn("1 flight", snap["choices"]["Client"][0]["detail"])

    def test_summary_counts_and_next_departure(self):
        summary = self.api.summary()
        self.assertEqual((summary["clients"], summary["airlines"], summary["flights"], summary["upcoming"]), (1, 2, 1, 1))
        self.assertEqual(summary["next"]["Start City"], "London")

    def test_search_by_field_and_by_name(self):
        self.assertEqual(len(self.api.search("Flight", "ada", "Client_ID")["records"]), 1)
        self.assertEqual(len(self.api.search("Airline", "france")["records"]), 1)
        self.assertEqual(len(self.api.search("Client", "", "")["records"]), 1)

    def test_preferences_defaults_saving_and_damaged_file(self):
        self.assertEqual(self.api.preferences()["preferences"], DEFAULT_PREFERENCES)
        self.assertTrue(self.api.set_preference("panel_width", 500)["ok"])
        self.assertEqual(PreferenceStore(self.store.folder / "settings.json").values["panel_width"], 500)
        (self.store.folder / "settings.json").write_text("{bad", encoding="utf-8")
        self.assertEqual(PreferenceStore(self.store.folder / "settings.json").values, DEFAULT_PREFERENCES)
        (self.store.folder / "settings.json").write_text('["x"]', encoding="utf-8")
        self.assertEqual(PreferenceStore(self.store.folder / "settings.json").values, DEFAULT_PREFERENCES)


if __name__ == "__main__":
    unittest.main()
