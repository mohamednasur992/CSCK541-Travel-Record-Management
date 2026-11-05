import unittest
from datetime import datetime


# Example dummy classes representing your core logic for testing purposes
class TravelRecordManager:
    def __init__(self):
        self.records = []

    def add_record(self, record):
        if not self._validate_record(record):
            raise ValueError("Invalid record data")
        self.records.append(record)

    def _validate_record(self, record):
        # Basic validation rules
        required_fields = ['flight_no', 'origin', 'destination', 'date']
        for field in required_fields:
            if not record.get(field):
                return False
        # Validate date format (YYYY-MM-DD)
        try:
            datetime.strptime(record['date'], '%Y-%m-%d')
        except ValueError:
            return False
        return True

    def sort_records(self, key, reverse=False):
        return sorted(self.records, key=lambda x: x.get(key, ''), reverse=reverse)

    def filter_records(self, query):
        query = query.lower()
        return [
            r for r in self.records
            if query in r['flight_no'].lower() or
               query in r['origin'].lower() or
               query in r['destination'].lower()
        ]


class TestTravelRecordManager(unittest.TestCase):

    def setUp(self):
        """Initialize a fresh manager and sample data before each test."""
        self.manager = TravelRecordManager()
        self.sample_record = {
            'flight_no': 'FA123',
            'origin': 'JNB',
            'destination': 'CPT',
            'date': '2026-11-15'
        }

    def test_add_valid_record(self):
        """Test adding a correctly formatted travel record."""
        self.manager.add_record(self.sample_record)
        self.assertEqual(len(self.manager.records), 1)
        self.assertEqual(self.manager.records[0]['flight_no'], 'FA123')

    def test_add_invalid_date_format(self):
        """Test that invalid date formats raise a ValueError."""
        invalid_record = self.sample_record.copy()
        invalid_record['date'] = '15/11/2026'  # Incorrect format
        with self.assertRaises(ValueError):
            self.manager.add_record(invalid_record)

    def test_missing_mandatory_field(self):
        """Test that missing required fields are rejected."""
        invalid_record = self.sample_record.copy()
        invalid_record['origin'] = ''  # Empty origin
        with self.assertRaises(ValueError):
            self.manager.add_record(invalid_record)

    def test_dynamic_sorting(self):
        """Test sorting records dynamically by keys like flight_no or date."""
        self.manager.add_record({'flight_no': 'ZB456', 'origin': 'DUR', 'destination': 'JNB', 'date': '2026-11-10'})
        self.manager.add_record({'flight_no': 'AA111', 'origin': 'PLZ', 'destination': 'JNB', 'date': '2026-11-12'})

        sorted_res = self.manager.sort_records(key='flight_no')
        self.assertEqual(sorted_res[0]['flight_no'], 'AA111')
        self.assertEqual(sorted_res[1]['flight_no'], 'ZB456')

    def test_search_filtering(self):
        """Test keyword filtering for the table view."""
        self.manager.add_record({'flight_no': 'BA055', 'origin': 'JNB', 'destination': 'LHR', 'date': '2026-12-01'})
        self.manager.add_record({'flight_no': 'SA312', 'origin': 'CPT', 'destination': 'JNB', 'date': '2026-12-05'})

        results = self.manager.filter_records('JNB')
        self.assertEqual(len(results), 2)

        results_flight = self.manager.filter_records('BA055')
        self.assertEqual(len(results_flight), 1)
        self.assertEqual(results_flight[0]['destination'], 'LHR')


if __name__ == '__main__':
    unittest.main()