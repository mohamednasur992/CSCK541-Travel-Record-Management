"""End-to-end GUI tests: the real window, the real page, a user clicking and typing.

The window runs in a separate process (``gui_driver.py``) because pywebview
can only be started once per process. The driver records one result per
check; each check becomes one test below, so a failure names the feature.

Skipped when pywebview is not installed, when there is no display (Linux
without ``DISPLAY``) or when ``RMS_SKIP_GUI=1`` is set.

Requirements covered: FR-06, FR-07, FR-08, FR-09, FR-10, FR-14, FR-15, FR-16,
FR-18, FR-20, FR-21, FR-22, FR-27, NFR-01, NFR-02, NFR-03, NFR-14 (see
``docs/requirements/03_Test_Traceability.md``).
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

DRIVER = Path(__file__).with_name("gui_driver.py")
TIMEOUT_SECONDS = 240


def skip_reason():
    """Why the GUI tests cannot run here, or ``None``."""
    if os.environ.get("RMS_SKIP_GUI") == "1":
        return "RMS_SKIP_GUI=1"
    if importlib.util.find_spec("webview") is None:
        return "pywebview is not installed"
    if sys.platform.startswith("linux") and not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        return "no display available"
    return None


@unittest.skipIf(skip_reason() is not None, skip_reason() or "")
class TestGuiEndToEnd(unittest.TestCase):
    """One session of the real application, checked feature by feature."""

    results = {}
    folder = None
    data_file = None
    settings_file = None

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls._tmp.cleanup)
        cls.folder = Path(cls._tmp.name)
        cls.data_file = cls.folder / "record.jsonl"
        cls.settings_file = cls.folder / "settings.json"
        result_file = cls.folder / "results.json"
        completed = subprocess.run(
            [sys.executable, "-I", str(DRIVER), str(cls.data_file), str(cls.settings_file), str(result_file)],
            capture_output=True, text=True, timeout=TIMEOUT_SECONDS, check=False)
        if not result_file.exists():
            raise AssertionError(f"the GUI driver produced no results (exit {completed.returncode}):\n"
                                 f"{completed.stdout}\n{completed.stderr}")
        cls.results = json.loads(result_file.read_text(encoding="utf-8"))

    def check(self, name):
        """Fail with the driver's explanation if check ``name`` did not pass."""
        self.assertNotIn("driver_crashed", self.results, self.results.get("driver_crashed"))
        self.assertIn(name, self.results, f"the driver never reached {name}")
        outcome = self.results[name]
        self.assertTrue(outcome["ok"], f"{name}: {outcome['detail']}")

    # ---- the page itself
    def test_page_loads_and_the_bridge_answers(self):
        self.check("page_ready")

    def test_fr27_logo_is_shown(self):
        self.check("logo_is_shown")

    def test_nfr01_three_tabs_and_a_new_button(self):
        self.check("three_tabs_and_new_button")

    # ---- create and feedback
    def test_fr06_fr14_fr15_create_a_client_and_a_country_is_suggested(self):
        self.check("create_client_and_country_suggestion")

    def test_fr14_a_typed_country_is_not_overwritten(self):
        self.check("country_suggestion_never_overwrites_typed_value")

    def test_fr06_create_an_airline_and_fr18_reject_a_duplicate_name(self):
        self.check("create_airline_and_reject_duplicate_name")

    def test_fr06_create_a_flight_with_the_dropdowns_and_quick_date(self):
        self.check("create_flight_with_dropdowns_and_quick_date")

    # ---- validation beside the fields
    def test_nfr03_a_required_field_error_appears_beside_the_field(self):
        self.check("required_field_error_is_shown_beside_the_field")

    def test_nfr03_a_phone_error_explains_how_to_fix_it(self):
        self.check("invalid_phone_number_error_explains_the_fix")

    def test_fr16_the_same_start_and_end_city_is_flagged_while_typing(self):
        self.check("same_start_and_end_city_is_flagged_while_typing")

    def test_fr21_the_journey_rule_blocks_a_second_departure_from_a_city(self):
        self.check("journey_rule_blocks_a_second_departure_from_the_same_city")

    # ---- search, sort, edit, delete
    def test_fr07_search_filters_and_show_all_restores(self):
        self.check("search_filters_and_show_all_restores")

    def test_fr08_table_columns_sort_both_ways(self):
        self.check("table_columns_sort_both_ways")

    def test_fr09_a_client_can_be_edited_but_its_id_is_locked(self):
        self.check("edit_a_client_with_the_id_locked")

    def test_fr20_a_client_with_flights_cannot_be_deleted(self):
        self.check("deleting_a_client_with_flights_is_blocked_with_an_explanation")

    def test_fr10_delete_asks_first_and_can_be_undone(self):
        self.check("delete_asks_first_cancel_keeps_confirm_removes_undo_restores")

    # ---- keyboard, settings, errors
    def test_nfr02_keyboard_shortcuts_work(self):
        self.check("keyboard_shortcuts_new_search_help_escape")

    def test_display_settings_change_the_theme_and_are_saved(self):
        self.check("display_settings_change_the_theme_and_are_saved")
        self.assertEqual(json.loads(self.settings_file.read_text(encoding="utf-8"))["theme"], "dark")

    def test_the_session_produced_no_javascript_errors(self):
        self.check("no_javascript_errors_during_the_whole_session")

    # ---- what ended up on disk (FR-22)
    def test_fr22_the_records_made_by_clicking_are_in_the_file(self):
        self.assertNotIn("driver_crashed", self.results)
        records = [json.loads(line) for line in self.data_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        clients = sorted(r["Name"] for r in records if r["Type"] == "Client")
        airlines = [r["Company Name"] for r in records if r["Type"] == "Airline"]
        flights = [r for r in records if r["Type"] == "Flight"]
        self.assertEqual(clients, ["Ada King", "Grace Hopper"])
        self.assertEqual(airlines, ["British Airways (BA)"])
        self.assertEqual(len(flights), 1)                         # the second departure from London was refused
        self.assertEqual((flights[0]["Start City"], flights[0]["End City"]), ("London", "Paris"))
        self.assertRegex(flights[0]["Date"], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")
        self.assertEqual(flights[0]["Client_ID"], 1)

    def test_nfr14_the_settings_file_sits_beside_the_records_not_in_them(self):
        text = self.data_file.read_text(encoding="utf-8")
        self.assertNotIn("dark", text)
        self.assertTrue(self.settings_file.exists())


if __name__ == "__main__":
    unittest.main()
