"""End to end through the page's API: create, search, update, delete, undo, reload from disk."""

import unittest

from tests.helpers import AIRLINE_FORM, CLIENT_FORM, FLIGHT_FORM, TempStore


class TestEndToEnd(unittest.TestCase):
    def setUp(self):
        self.store = TempStore()
        self.addCleanup(self.store.cleanup)
        self.api, self.rm = self.store.api()

    def reload(self):
        """A fresh manager reading the file, as on the next program start."""
        return self.store.manager().records

    def test_full_workflow(self):
        # Create, each written to the file at once
        self.assertTrue(self.api.create("Client", CLIENT_FORM)["ok"])
        self.assertTrue(self.api.create("Airline", AIRLINE_FORM)["ok"])
        self.assertTrue(self.api.create("Airline", {"ID": "2", "Company Name": "Air France (AF)"})["ok"])
        first = self.api.create("Flight", FLIGHT_FORM)
        self.assertTrue(first["ok"])
        second = self.api.create("Flight", {**FLIGHT_FORM, "Airline_ID": "2", "Start City": "Paris", "End City": "Rome"})
        self.assertTrue(second["ok"])
        self.assertEqual(len(self.reload()), 5)

        # Search and display
        found = self.api.search("Flight", "air france", "Airline_ID")["records"]
        self.assertEqual([r["End City"] for r in found], ["Rome"])
        self.assertEqual(first["summary"]["flights"], 1)

        # Update the last leg; the ID of a client cannot change
        key = second["record"]["key"]
        updated = self.api.update("Flight", key, {**FLIGHT_FORM, "Airline_ID": "2", "Start City": "Paris", "End City": "Milan"})
        self.assertTrue(updated["ok"])
        self.assertEqual(updated["record"]["End City"], "Milan")
        client = self.api.update("Client", 1, {**CLIENT_FORM, "ID": "99", "City": "Paris"})
        self.assertEqual((client["record"]["ID"], client["record"]["City"]), (1, "Paris"))

        # Delete rules: removing the first leg leaves a valid one-leg journey; a client with flights is blocked
        self.assertTrue(self.api.delete_check("Flight", first["record"]["key"])["allowed"])
        self.assertTrue(self.api.delete("Client", 1)["blocked"])
        deleted = self.api.delete("Flight", updated["record"]["key"])
        self.assertTrue(deleted["undo"])
        self.assertEqual(len(self.reload()), 4)

        # Undo puts it back in its place and on disk
        self.assertTrue(self.api.undo_delete()["ok"])
        stored = self.reload()
        self.assertEqual(len(stored), 5)
        self.assertEqual(stored[-1]["End City"], "Milan")

    def test_save_all_and_close_flags(self):
        self.api.create("Airline", AIRLINE_FORM)
        self.api.set_form_dirty(True)
        self.assertTrue(self.api._form_dirty)  # pylint: disable=protected-access
        result = self.api.save_all()
        self.assertTrue(result["ok"])
        self.assertEqual(result["path"], str(self.store.data_file))


if __name__ == "__main__":
    unittest.main()
