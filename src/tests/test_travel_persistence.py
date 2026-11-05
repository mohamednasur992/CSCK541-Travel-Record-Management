import unittest
import os
import json
import tempfile


class TravelPersistenceManager:
    def __init__(self, filepath="travel_records.json"):
        self.filepath = filepath

    def save_records(self, records):
        """Save a list of travel record dictionaries to a JSON file."""
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(records, f, indent=4)
            return True
        except Exception as e:
            # Handle disk write errors gracefully
            return False

    def load_records(self):
        """Load travel records from the JSON file. Returns empty list if file doesn't exist or is corrupted."""
        if not os.path.exists(self.filepath):
            return []
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                return []
        except (json.JSONDecodeError, IOError):
            # Graceful recovery/handling for corrupted files
            return []

    def append_record(self, new_record):
        """Append a single record while preserving existing entries."""
        records = self.load_records()
        records.append(new_record)
        return self.save_records(records)


class TestTravelPersistence(unittest.TestCase):

    def setUp(self):
        """Create a temporary file for safe testing without touching production data."""
        self.test_dir = tempfile.TemporaryDirectory()
        self.test_file = os.path.join(self.test_dir.name, "test_records.json")
        self.manager = TravelPersistenceManager(filepath=self.test_file)

        self.sample_data = [
            {"flight_no": "FA123", "origin": "JNB", "destination": "CPT", "date": "2026-11-15"},
            {"flight_no": "ZB456", "origin": "DUR", "destination": "JNB", "date": "2026-11-10"}
        ]

    def tearDown(self):
        """Clean up and remove the temporary directory and files after each test."""
        self.test_dir.cleanup()

    def test_save_and_load_records(self):
        """Test that records saved to disk can be accurately loaded back into memory."""
        success = self.manager.save_records(self.sample_data)
        self.assertTrue(success, "Save operation should return True on success.")

        loaded_data = self.manager.load_records()
        self.assertEqual(len(loaded_data), 2, "Should load exactly 2 records.")
        self.assertEqual(loaded_data[0]["flight_no"], "FA123")
        self.assertEqual(loaded_data[1]["destination"], "JNB")

    def test_load_nonexistent_file(self):
        """Test that loading from a missing file path gracefully returns an empty list instead of crashing."""
        non_existent_manager = TravelPersistenceManager(filepath="non_existent_path.json")
        records = non_existent_manager.load_records()
        self.assertEqual(records, [], "Should return an empty list if file does not exist.")

    def test_append_record(self):
        """Test appending a new record preserves existing saved data."""
        # Save initial data
        self.manager.save_records(self.sample_data)

        # Append a new record
        new_entry = {"flight_no": "AA111", "origin": "PLZ", "destination": "JNB", "date": "2026-11-12"}
        self.manager.append_record(new_entry)

        # Verify total count is now 3 and new record is present
        loaded_data = self.manager.load_records()
        self.assertEqual(len(loaded_data), 3)
        self.assertEqual(loaded_data[2]["flight_no"], "AA111")

    def test_corrupted_file_handling(self):
        """Test that invalid/corrupted JSON data is handled gracefully without raising exceptions."""
        # Write malformed JSON text to the test file
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write("{ invalid json formatting ...")

        # Loading should catch the JSONDecodeError and return an empty list safely
        loaded_data = self.manager.load_records()
        self.assertEqual(loaded_data, [], "Should recover gracefully from corrupted files by returning an empty list.")


if __name__ == '__main__':
    unittest.main()