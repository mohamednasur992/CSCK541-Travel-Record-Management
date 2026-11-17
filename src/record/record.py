"""Manage client, airline, and flight records with .JSONL persistence."""
import os
import json

class RecordManager:
    """Manage the lifecycle and persistence of travel-agent records."""
    def __init__(self, filepath="src/record/record.jsonl"):
        """Initialise the manager and load previously saved records."""
        self.filepath = filepath
        self.records = []
        self.load_from_file()

    def load_from_file(self):
        """Load existing .JSONL records into memory."""

        # Create the storage directory on first use if no data file exists.
        if not os.path.exists(self.filepath):
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            self.records = []
            return

        try:
            # Each non-empty line represents one independently stored record.
            with open(self.filepath, "r", encoding="utf-8") as file:
                self.records = [
                    json.loads(line.strip()) for line in file if line.strip()
                ]
        except (json.JSONDecodeError, IOError) as e:
            # Start with an empty collection if stored data cannot be read safely.
            print(f"Error loading records from file: {e}")
            self.records = []

    def save_to_file(self):
        """SPersist all records to the configured .JSONL file."""
        try:
            # Ensure the destination directory exists before writing.
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)

            # Store one .JSON object per line to preserve the .JSONL structure.
            with open(self.filepath, "w", encoding="utf-8") as file:
                for record in self.records:
                    file.write(json.dumps(record) + "\n")
        except IOError as e:
            print(f"Error saving records to file: {e}")

    # ------------------------------------------------------------------
    # CREATE OPERATIONS
    # ------------------------------------------------------------------

    # Client records contain more fields than the default Pylint threshold.
    # pylint: disable=too-many-arguments, too-many-positional-arguments
    def add_client(
        self,
        client_id,
        name,
        email,
        phone_number,
        city,
        address,
        passport_number,
        nationality,
        emergency_contact,
    ):
        """Create a client record and add it to the in-memory collection."""

        # Convert the identifier to an integer so IDs use a consistent type.
        record = {
            "id": int(client_id),
            "type": "Client",
            "name": name,
            "email": email,
            "phone_number": phone_number,
            "city": city,
            "address": address,
            "passport_number": passport_number,
            "nationality": nationality,
            "emergency_contact": emergency_contact,
        }
        self.records.append(record)
        return record

    def add_airline(self, airline_id, company_name):
        """Create an airline-company record."""
        record = {
            "id": int(airline_id),
            "type": "Airline",
            "company_name": company_name,
        }
        self.records.append(record)
        return record

    def add_flight(
        self, client_id, airline_id, date_str, start_city, end_city
    ):
        """Create a flight record linking a client to an airline."""

        # Client and airline IDs act as references to their related records.
        record = {
            "type": "Flight",
            "client_id": int(client_id),
            "airline_id": int(airline_id),
            "date": date_str,
            "start_city": start_city,
            "end_city": end_city,
        }
        self.records.append(record)
        return record

    # ------------------------------------------------------------------
    # SEARCH AND RETRIEVAL OPERATIONS
    # ------------------------------------------------------------------

    def search_records(self, query=None, record_type=None):
        """Return records matching an optional type and keyword."""

        results = self.records

        # Apply the record-type filter before performing the broader text search.
        if record_type:
            results = [r for r in results if r.get("type") == record_type]

        if query:
            query_str = str(query).lower()
            matched = []

            # Search all stored values so users are not restricted to one field.
            for r in results:
                if any(query_str in str(val).lower() for val in r.values()):
                    matched.append(r)
            return matched

        return results

    def get_record_by_id(self, record_id, record_type=None):
        """Return the first record matching an ID and optional record type."""
        for r in self.records:
            if r.get("id") == int(record_id):
                if record_type is None or r.get("type") == record_type:
                    return r
        return None

    # ------------------------------------------------------------------
    # UPDATE OPERATIONS
    # ------------------------------------------------------------------

    # Updates support additional matching fields because flight records
    # do not have their own unique record ID.
    # pylint: disable=too-many-arguments, too-many-positional-arguments
    def update_record(
        self,
        record_id,
        updated_data,
        record_type=None,
        old_airline_id=None,
        old_date=None,
        old_start=None,
        old_end=None,
    ):
        """Update the first record matching the supplied identifying criteria."""
        updated = False
        for r in self.records:
            if record_type == "Flight" and r.get("type") == "Flight":
                match_client = str(r.get("client_id")) == str(record_id)
                # A flight is identified by a combination of client, airline,
                # date, origin, and destination rather than a standalone ID.
                match_airline = (
                    old_airline_id is None
                    or str(r.get("airline_id")) == str(old_airline_id)
                )
                match_date = old_date is None or str(r.get("date")) == str(
                    old_date
                )
                match_start = old_start is None or str(
                    r.get("start_city")
                ) == str(old_start)
                match_end = old_end is None or str(r.get("end_city")) == str(
                    old_end
                )

                if (
                    match_client
                    and match_airline
                    and match_date
                    and match_start
                    and match_end
                ):
                    r.update(updated_data)
                    updated = True
                    break
            elif (
                record_type
                and r.get("type") == record_type
                and str(r.get("id")) == str(record_id)
            ):
                r.update(updated_data)
                updated = True
                break
            elif not record_type and str(r.get("id")) == str(record_id):
                r.update(updated_data)
                updated = True
                break

        # Persist only when an existing record was successfully changed.
        if updated:
            if hasattr(self, "save_to_file"):
                self.save_to_file()
            elif hasattr(self, "save_records"):
                self.save_records()
        return updated

    # ------------------------------------------------------------------
    # DELETE OPERATIONS
    # ------------------------------------------------------------------

    # pylint: disable=too-many-arguments, too-many-positional-arguments
    def delete_record(
        self,
        record_id,
        record_type=None,
        airline_id=None,
        date=None,
        start_city=None,
        end_city=None,
    ):
        """Delete a matching record while protecting referenced records."""
        if record_type == "Client":
            # Prevent deletion when flights still reference the client.
            has_bookings = any(
                str(r.get("client_id")) == str(record_id)
                and r.get("type") == "Flight"
                for r in self.records
            )
            if has_bookings:
                raise ValueError(
                    f"Cannot delete Client (ID: {record_id}): "
                    "Active flight bookings exist."
                )

        elif record_type == "Airline":
            # Prevent deletion when flights still reference the airline.
            has_bookings = any(
                str(r.get("airline_id")) == str(record_id)
                and r.get("type") == "Flight"
                for r in self.records
            )
            if has_bookings:
                raise ValueError(
                    f"Cannot delete Airline (ID: {record_id}): "
                    "Active flight bookings exist."
                )

        initial_count = len(self.records)

        if record_type == "Flight":

            def match_flight(r):
                """Return True when a flight matches the supplied identifiers."""
                if r.get("type") != "Flight":
                    return False
                if str(r.get("client_id")) != str(record_id):
                    return False
                if airline_id is not None and str(
                    r.get("airline_id")
                ) != str(airline_id):
                    return False
                if date is not None and str(r.get("date")) != str(date):
                    return False
                if start_city is not None and str(
                    r.get("start_city")
                ) != str(start_city):
                    return False
                if end_city is not None and str(
                    r.get("end_city")
                ) != str(end_city):
                    return False
                return True

            # Rebuild the collection while excluding matching flight records.
            self.records = [r for r in self.records if not match_flight(r)]
        elif record_type:
            # Client and airline records use their own numeric IDs.
            self.records = [
                r
                for r in self.records
                if not (
                    str(r.get("id")) == str(record_id)
                    and r.get("type") == record_type
                )
            ]
        else:
            # Without a type filter, remove any record with the matching ID.
            self.records = [
                r for r in self.records if str(r.get("id")) != str(record_id)
            ]

        success = len(self.records) < initial_count

        # Without a type filter, remove any record with the matching ID.
        if success:
            if hasattr(self, "save_to_file"):
                self.save_to_file()
            elif hasattr(self, "save_records"):
                self.save_records()
        return success
