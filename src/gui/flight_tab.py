"""Journey rules for flight bookings (no user-interface code).

A client's flights on one date must form a single linear journey: each leg
starts where the previous one ended and no city is departed from twice.
Stored record order defines the order of the legs, because departure and
arrival times are not captured.

The Flights view uses this class; it is kept free of Tk so the rules can be
tested headlessly.
"""


class FlightBookingRules:
    """Check bookings and deletions against the same-day journey rule."""

    def __init__(self, record_manager):
        self.rm = record_manager
        # Identity of the flight currently being edited (None when creating).
        self.original_flight_key = None

    @staticmethod
    def _flight_identity(flight):
        """Return a normalised identity for one stored flight record."""
        return (
            str(flight.get("client_id", "")).strip(),
            str(flight.get("airline_id", "")).strip(),
            str(flight.get("date", "")).strip(),
            str(flight.get("start_city", "")).strip().casefold(),
            str(flight.get("end_city", "")).strip().casefold(),
        )

    @staticmethod
    def _same_client_and_date(flight, client_id, travel_date):
        """Return whether a flight belongs to one client's dated journey."""
        return (
            str(flight.get("client_id", "")).strip() == client_id
            and str(flight.get("date", "")).strip() == travel_date
        )

    @staticmethod
    def _validate_linear_journey(journey):
        """Return a conflict message when flights do not form one linear path."""
        seen_flights = set()
        used_start_cities = set()

        for index, flight in enumerate(journey):
            identity = FlightBookingRules._flight_identity(flight)
            start_city = str(flight.get("start_city", "")).strip()
            normalized_start = start_city.casefold()

            if identity in seen_flights:
                return "An identical flight booking already exists."
            seen_flights.add(identity)

            if normalized_start in used_start_cities:
                return (
                    f"A flight already departs from {start_city} in this client's "
                    "journey on that date. Each reached city may be used as a "
                    "Start City only once."
                )

            if index:
                previous_destination = str(
                    journey[index - 1].get("end_city", "")
                ).strip()
                if normalized_start != previous_destination.casefold():
                    return (
                        f"The next flight must start from {previous_destination}, "
                        "the destination of the latest valid connection."
                    )

            used_start_cities.add(normalized_start)

        return None

    def booking_conflict_message(self, flight_data, exclude_original=False):
        """Return why a booking breaks the client's linear same-day journey.

        Stored record order defines the journey order because departure and
        arrival times are not captured. New bookings are appended as the latest
        leg. During an update, the candidate replaces the original leg in place.
        """
        candidate_client = str(flight_data.get("client_id", "")).strip()
        candidate_date = str(flight_data.get("date", "")).strip()
        original_identity = None
        if exclude_original and self.original_flight_key:
            original_identity = self._flight_identity(self.original_flight_key)

        records = self.rm.search_records(record_type="Flight")
        journey = []
        original_replaced = False
        candidate_inserted = False

        for record in records:
            is_original = (
                original_identity is not None
                and not original_replaced
                and self._flight_identity(record) == original_identity
            )
            if is_original:
                original_replaced = True
                if self._same_client_and_date(
                    record, candidate_client, candidate_date
                ):
                    journey.append(flight_data)
                    candidate_inserted = True
                continue

            if self._same_client_and_date(
                record, candidate_client, candidate_date
            ):
                journey.append(record)

        if not candidate_inserted:
            journey.append(flight_data)

        conflict = self._validate_linear_journey(journey)
        if conflict:
            return conflict

        # If an update moves a middle leg to another client/date, ensure that
        # removing it does not leave its original journey disconnected.
        if exclude_original and self.original_flight_key:
            original_client = str(
                self.original_flight_key.get("client_id", "")
            ).strip()
            original_date = str(
                self.original_flight_key.get("date", "")
            ).strip()
            moved_to_another_journey = (
                original_client != candidate_client
                or original_date != candidate_date
            )
            if moved_to_another_journey:
                remaining_journey = []
                original_removed = False
                for record in records:
                    if (
                        not original_removed
                        and self._flight_identity(record) == original_identity
                    ):
                        original_removed = True
                        continue
                    if self._same_client_and_date(
                        record, original_client, original_date
                    ):
                        remaining_journey.append(record)

                conflict = self._validate_linear_journey(remaining_journey)
                if conflict:
                    return (
                        "Updating this flight would break the remaining "
                        f"same-day journey. {conflict}"
                    )

        return None

    def has_booking_date_conflict(self, flight_data, exclude_original=False):
        """Return True when a booking breaks the linear same-day journey."""
        return self.booking_conflict_message(
            flight_data, exclude_original=exclude_original
        ) is not None


    def deletion_conflict_message(self, selected_flight):
        """Return a message if deleting a flight breaks its remaining journey."""
        client_id = str(selected_flight["client_id"]).strip()
        travel_date = str(selected_flight["date"]).strip()
        selected_identity = self._flight_identity(selected_flight)

        remaining_journey = []
        selected_removed = False

        for record in self.rm.search_records(record_type="Flight"):
            if (
                    not selected_removed
                    and self._flight_identity(record) == selected_identity
            ):
                selected_removed = True
                continue

            if self._same_client_and_date(
                    record,
                    client_id,
                    travel_date,
            ):
                remaining_journey.append(record)

        conflict = self._validate_linear_journey(remaining_journey)

        if conflict:
            return (
                "This flight cannot be deleted because doing so would break "
                f"the client's remaining same-day journey. {conflict}"
            )

        return None

# Backwards-compatible name used by the headless tests.
FlightTab = FlightBookingRules
