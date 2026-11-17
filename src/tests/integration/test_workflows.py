"""Integration tests: bridge, rules, record manager, files, preferences and start-up working together."""

import functools
import json
import logging
import unittest
from unittest import mock

import config
import main
from app_logging import setup_logging
from gui.bridge import WebApi
from tests.helpers import AIRLINE_FORM, CLIENT_FORM, FLIGHT_FORM, StoreTestCase, TempStore


class TestAgentSession(StoreTestCase):
    """A travel agent's day: book, change, cancel, restart, and find everything as left."""

    def book_a_three_leg_trip(self):
        self.create("Client", CLIENT_FORM)
        self.create("Airline", AIRLINE_FORM)
        self.create("Airline", {"ID": "2", "Company Name": "Air France (AF)"})
        self.create("Flight", {**FLIGHT_FORM, "Date": "2026-12-01 07:00", "Start City": "London", "End City": "Paris"})
        self.create("Flight", {**FLIGHT_FORM, "Airline_ID": "2", "Date": "2026-12-01 11:30",
                               "Start City": "Paris", "End City": "Rome"})
        self.create("Flight", {**FLIGHT_FORM, "Airline_ID": "2", "Date": "2026-12-01 18:00",
                               "Start City": "Rome", "End City": "Oslo"})

    def restart(self):
        api, manager = self.store.api()
        return api, manager

    def test_everything_booked_is_there_after_a_restart(self):
        self.book_a_three_leg_trip()
        api, manager = self.restart()
        self.assertEqual(manager.load_warnings, [])
        snapshot = api.snapshot()
        self.assertEqual(snapshot["summary"]["flights"], 3)
        self.assertEqual([f["End City"] for f in snapshot["records"]["Flight"]], ["Paris", "Rome", "Oslo"])
        self.assertEqual(snapshot["records"]["Client"][0]["flights"], 3)
        self.assertEqual(snapshot["next_id"], {"Client": 2, "Airline": 3})

    def test_the_rules_still_apply_after_a_restart(self):
        self.book_a_three_leg_trip()
        api, _ = self.restart()
        self.assertFalse(api.create("Flight", {**FLIGHT_FORM, "Start City": "London", "End City": "Oslo",
                                               "Date": "2026-12-01 20:00"})["ok"])
        middle = api.snapshot()["records"]["Flight"][1]["key"]
        self.assertFalse(api.delete("Flight", middle)["ok"])
        self.assertFalse(api.delete("Client", 1)["ok"])

    def test_cancelling_the_trip_leg_by_leg_then_the_people(self):
        self.book_a_three_leg_trip()
        for _ in range(3):                                          # always the last leg
            last = self.api.snapshot()["records"]["Flight"][-1]["key"]
            self.assertTrue(self.api.delete("Flight", last)["ok"])
        self.assertTrue(self.api.delete("Client", 1)["ok"])
        self.assertTrue(self.api.delete("Airline", 1)["ok"])
        self.assertTrue(self.api.delete("Airline", 2)["ok"])
        self.assertEqual(self.store.manager().records, [])
        self.assertEqual(self.file_lines(), [])

    def test_undo_restores_the_exact_position_in_the_journey_even_after_a_restart_of_the_bridge(self):
        self.book_a_three_leg_trip()
        last = self.api.snapshot()["records"]["Flight"][-1]["key"]
        self.api.delete("Flight", last)
        self.assertTrue(self.api.undo_delete()["ok"])
        again = self.store.manager()
        self.assertEqual([f["End City"] for f in again.records if f["Type"] == "Flight"], ["Paris", "Rome", "Oslo"])

    def test_an_edit_to_a_client_is_visible_in_flights_and_choices(self):
        self.book_a_three_leg_trip()
        self.api.update("Client", 1, {**CLIENT_FORM, "Name": "Ada King"})
        snapshot = self.api.snapshot()
        self.assertEqual({f["client_name"] for f in snapshot["records"]["Flight"]}, {"Ada King"})
        self.assertEqual(snapshot["choices"]["Client"][0]["name"], "Ada King")
        self.assertEqual(len(self.api.search("Flight", "king")["records"]), 3)

    def test_every_result_is_json_serialisable(self):
        self.book_a_three_leg_trip()
        key = self.api.snapshot()["records"]["Flight"][0]["key"]
        results = [self.api.bootstrap(), self.api.snapshot(), self.api.summary(), self.api.search("Flight", "x"),
                   self.api.get("Flight", key), self.api.delete_check("Flight", key),
                   self.api.delete("Client", 1), self.api.save_all(), self.api.preferences(),
                   self.api.create("Client", {}), self.api.undo_delete()]
        for result in results:
            json.dumps(result)


class TestPreferencesAcrossRestarts(StoreTestCase):
    """The display settings live beside the records and survive a restart (settings.json)."""

    def test_a_preference_is_remembered_by_the_next_session(self):
        self.assertTrue(self.api.set_preference("theme", "dark")["ok"])
        self.assertTrue(self.api.set_preference("panel_width", 520)["ok"])
        api, _ = self.store.api()
        prefs = api.preferences()["preferences"]
        self.assertEqual((prefs["theme"], prefs["panel_width"]), ("dark", 520))
        self.assertEqual(json.loads((self.store.folder / "settings.json").read_text(encoding="utf-8"))["theme"], "dark")

    def test_preferences_and_records_do_not_interfere(self):
        self.create("Airline", AIRLINE_FORM)
        self.api.set_preference("density", "compact")
        self.assertEqual(len(self.file_lines()), 1)
        self.assertNotIn("compact", self.store.data_file.read_text(encoding="utf-8"))


class TestStartUpToShutdown(unittest.TestCase):
    """main() with the real record manager, bridge and logging; only the window is replaced."""

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

    def run_main(self, session):
        with mock.patch("main.webview_available", return_value=True), mock.patch("main.run", session), \
                mock.patch("main.setup_logging", functools.partial(setup_logging, console=False)):
            return main.main(data_file=self.store.data_file, log_file=self.log_file)

    def test_two_sessions_in_a_row_build_on_each_other(self):
        def first(manager, warnings):
            api = WebApi(manager, warnings=warnings, settings_path=self.store.folder / "s.json")
            api.create("Client", CLIENT_FORM)
            api.create("Airline", AIRLINE_FORM)
            return config.EXIT_OK

        def second(manager, warnings):
            api = WebApi(manager, warnings=warnings, settings_path=self.store.folder / "s.json")
            self.assertEqual(api.snapshot()["summary"]["clients"], 1)
            self.assertTrue(api.create("Flight", FLIGHT_FORM)["ok"])
            return config.EXIT_OK

        self.assertEqual(self.run_main(first), config.EXIT_OK)
        self.assertEqual(self.run_main(second), config.EXIT_OK)
        self.assertEqual([r["Type"] for r in self.store.manager().records], ["Client", "Airline", "Flight"])

    def test_a_damaged_file_is_reported_to_the_page_and_logged_then_the_session_continues(self):
        self.store.data_file.write_text("{ oops", encoding="utf-8")
        seen = {}

        def session(manager, warnings):
            api = WebApi(manager, warnings=warnings, settings_path=self.store.folder / "s.json")
            seen["warnings"] = api.bootstrap()["warnings"]
            api.create("Airline", AIRLINE_FORM)
            return config.EXIT_OK

        self.assertEqual(self.run_main(session), config.EXIT_OK)
        self.assertEqual(len(seen["warnings"]), 1)
        self.assertEqual(len(list(self.store.folder.glob("record.jsonl.corrupt-*"))), 1)
        log = self.log_file.read_text(encoding="utf-8")
        self.assertIn("Could not load records", log)
        self.assertIn("Created airline 1", log)
        self.assertEqual(self.store.manager().records[0]["Company Name"], "British Airways (BA)")

    def test_the_log_records_the_session_but_not_personal_details(self):
        def session(manager, warnings):
            api = WebApi(manager, warnings=warnings, settings_path=self.store.folder / "s.json")
            api.create("Client", CLIENT_FORM)
            return config.EXIT_OK

        self.run_main(session)
        log = self.log_file.read_text(encoding="utf-8")
        self.assertIn("Created client 1", log)
        for personal in ("Ada Lovelace", "1 Main St", "+44 151 123 4567", "SW1A 1AA"):
            self.assertNotIn(personal, log)


if __name__ == "__main__":
    unittest.main()
