import unittest
from datetime import datetime


class FormatError(Exception):
    """Custom exception for invalid date or data formatting."""
    pass


class BusinessLogicError(Exception):
    """Custom exception for invalid business logic rules."""
    pass


class TravelBookingService:
    def book_trip(self, origin, destination, departure_date, return_date):
        """Processes a travel booking with strict error handling and validation."""
        # 1. Check for missing mandatory fields
        if not origin or not destination or not departure_date or not return_date:
            raise ValueError("All fields (origin, destination, departure_date, return_date) are mandatory.")

        # 2. Validate date string formatting
        try:
            dep_dt = datetime.strptime(departure_date, '%Y-%m-%d')
            ret_dt = datetime.strptime(return_date, '%Y-%m-%d')
        except ValueError:
            raise FormatError("Dates must be correctly formatted as YYYY-MM-DD.")

        # 3. Validate business logic rules (Chronological date validation)
        if ret_dt < dep_dt:
            raise BusinessLogicError("Return date cannot be earlier than the departure date.")

        return {"status": "success", "message": "Booking confirmed successfully."}


class TestTravelErrorHandling(unittest.TestCase):

    def setUp(self):
        """Initialize the booking service instance before each test."""
        self.service = TravelBookingService()

    def test_missing_mandatory_fields(self):
        """Test that omitting required fields raises a ValueError."""
        with self.assertRaises(ValueError) as context:
            self.service.book_trip("", "CPT", "2026-11-15", "2026-11-20")

        self.assertIn("mandatory", str(context.exception))

    def test_invalid_date_formatting(self):
        """Test that incorrect date strings raise a custom FormatError instead of crashing."""
        with self.assertRaises(FormatError) as context:
            self.service.book_trip("JNB", "CPT", "15/11/2026", "2026-11-20")  # Invalid slash format

        self.assertIn("YYYY-MM-DD", str(context.exception))

    def test_illogical_date_ranges(self):
        """Test that a return date occurring before departure raises a BusinessLogicError."""
        with self.assertRaises(BusinessLogicError) as context:
            self.service.book_trip("JNB", "CPT", "2026-11-25", "2026-11-20")  # Return before departure

        self.assertIn("Return date cannot be earlier", str(context.exception))

    def test_successful_booking_execution(self):
        """Test that valid inputs pass error checks and return a successful status response."""
        response = self.service.book_trip("JNB", "CPT", "2026-11-15", "2026-11-20")
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["message"], "Booking confirmed successfully.")


if __name__ == '__main__':
    unittest.main()