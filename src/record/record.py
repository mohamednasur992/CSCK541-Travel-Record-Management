import os
import json
from datetime import datetime

class RecordManager:
    def __init__(self, filepath="src/record/record.jsonl"):
        """Initializes the manager and loads existing records from the file system."""
        self.filepath = filepath
        self.records = []
        self.load_from_file()

    def load_from_file(self):
        """Checks for existing records on startup and loads them into memory."""
        if not os.path.exists(self.filepath):
            # Ensure directory exists if file doesn't
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            self.records = []
            return

        try:
            with open(self.filepath, "r", encoding="utf-8") as file:
                self.records = [json.loads(line.strip()) for line in file if line.strip()]
        except Exception as e:
            print(f"Error loading records from file: {e}")
            self.records = []

    def save_to_file(self):
        """Saves the current list of records to the file system (JSONL format)."""
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, "w", encoding="utf-8") as file:
                for record in self.records:
                    file.write(json.dumps(record) + "\n")
        except Exception as e:
            print(f"Error saving records to file: {e}")

    # --- 1. CREATE OPERATIONS ---
    
    def add_client(self, client_id, name, address_1, address_2, address_3, city, state, zip_code, country, phone_number):
        record = {
            "id": int(client_id),
            "type": "Client",
            "name": name,
            "address_line_1": address_1,
            "address_line_2": address_2,
            "address_line_3": address_3,
            "city": city,
            "state": state,
            "zip_code": zip_code,
            "country": country,
            "phone_number": phone_number
        }
        self.records.append(record)
        return record

    def add_airline(self, airline_id, company_name):
        record = {
            "id": int(airline_id),
            "type": "Airline",
            "company_name": company_name
        }
        self.records.append(record)
        return record

    def add_flight(self, client_id, airline_id, date_str, start_city, end_city):
        record = {
            "type": "Flight",
            "client_id": int(client_id),
            "airline_id": int(airline_id),
            "date": date_str,  # ISO format string recommended e.g., "2026-11-15T08:30:00"
            "start_city": start_city,
            "end_city": end_city
        }
        self.records.append(record)
        return record

    # --- 2. SEARCH & DISPLAY OPERATIONS ---
    
    def search_records(self, query=None, record_type=None):
        """
        Searches records by type or general keyword matching across values.
        """
        results = self.records
        
        if record_type:
            results = [r for r in results if r.get("type") == record_type]
            
        if query:
            query_str = str(query).lower()
            matched = []
            for r in results:
                if any(query_str in str(val).lower() for val in r.values()):
                    matched.append(r)
            return matched
            
        return results

    def get_record_by_id(self, record_id, record_type=None):
        """Finds a specific record by its ID and optional type."""
        for r in self.records:
            if r.get("id") == int(record_id):
                if record_type is None or r.get("type") == record_type:
                    return r
        return None

    # --- 3. UPDATE OPERATIONS ---

    def update_record(self, record_id, updated_data, record_type=None):
        """Updates an existing record matching the ID and optional type."""
        updated = False
        for r in self.records:
            match_id = str(r.get("id")) == str(record_id) or str(r.get("client_id")) == str(record_id)
            match_type = not record_type or r.get("type") == record_type

            if match_id and match_type:
                r.update(updated_data)
                updated = True

        if updated:
            if hasattr(self, 'save_to_file'):
                self.save_to_file()
            elif hasattr(self, 'save_records'):
                self.save_records()
        return updated

    # --- 4. DELETE OPERATIONS ---

    def delete_record(self, record_id, record_type=None):
        """Deletes a record matching the given ID and type, enforcing referential integrity."""
        # 1. Referential Integrity Checks
        if record_type == "Client":
            # Check if any flight booking uses this client's ID
            has_bookings = any(
                str(r.get("client_id")) == str(record_id) and r.get("type") == "Flight" for r in self.records)
            if has_bookings:
                raise ValueError(
                    f"Cannot delete Client (ID: {record_id}): Active flight bookings exist for this client.")

        elif record_type == "Airline":
            # Check if any flight booking uses this airline's ID
            has_bookings = any(
                str(r.get("airline_id")) == str(record_id) and r.get("type") == "Flight" for r in self.records)
            if has_bookings:
                raise ValueError(
                    f"Cannot delete Airline (ID: {record_id}): Active flight bookings exist for this airline.")

        # 2. Proceed with Deletion if checks pass
        initial_count = len(self.records)
        if record_type:
            self.records = [r for r in self.records if
                            not (str(r.get("id")) == str(record_id) and r.get("type") == record_type)]
        else:
            self.records = [r for r in self.records if str(r.get("id")) != str(record_id)]

        success = len(self.records) < initial_count
        if success:
            if hasattr(self, 'save_to_file'):
                self.save_to_file()
            elif hasattr(self, 'save_records'):
                self.save_records()
        return success