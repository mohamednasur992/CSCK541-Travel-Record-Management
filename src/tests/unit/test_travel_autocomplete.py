"""Reference data behind the city, airline and country suggestions."""

import re
import unittest

from gui.reference_data import CITY_TO_COUNTRY, WORLD_AIRLINES, WORLD_CITIES
from tests.helpers import TempStore


class TestReferenceData(unittest.TestCase):
    def test_lists_have_no_duplicates(self):
        self.assertEqual(len(WORLD_CITIES), len(set(WORLD_CITIES)))
        self.assertEqual(len(WORLD_AIRLINES), len(set(WORLD_AIRLINES)))

    def test_every_city_suggests_a_country(self):
        self.assertEqual(set(CITY_TO_COUNTRY), set(WORLD_CITIES))

    def test_airlines_show_a_two_character_code(self):
        for airline in WORLD_AIRLINES:
            self.assertRegex(airline, re.compile(r"\([A-Z0-9]{2}\)$"))

    def test_page_receives_sorted_suggestions(self):
        store = TempStore()
        self.addCleanup(store.cleanup)
        api, _ = store.api()
        boot = api.bootstrap()
        self.assertEqual(boot["cities"], sorted(WORLD_CITIES))
        self.assertEqual(boot["airlines"], sorted(WORLD_AIRLINES))
        self.assertEqual(boot["city_country"]["Accra"], "Ghana")


if __name__ == "__main__":
    unittest.main()
