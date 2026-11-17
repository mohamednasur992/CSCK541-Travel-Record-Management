"""Manage client, airline and flight records with JSON Lines persistence.

``RecordManager`` keeps every record in one in-memory list of dictionaries
(``self.records``) and reads and writes them as JSON Lines: one record per
line, UTF-8.

Error handling
--------------
* A missing file means an empty start; its folder is created.
* A file that cannot be read, or that contains a line that is not a valid
  record, is copied to a ``.corrupt-<timestamp>`` backup before the manager
  starts with an empty list, so the damaged data can never be overwritten
  and lost on the next save. The reason is kept in ``self.load_warnings``
  for the interface to show.
* Saving writes a temporary file and then replaces the old one, so a failed
  save never leaves a half-written file. Failures raise ``RecordStorageError``.
* Records saved by the earlier version of the program (lower-case keys such
  as ``company_name``) are upgraded to the brief's field names on load and
  written in the new form at the next save.
* Duplicate IDs raise ``DuplicateRecordError`` and deleting a client or airline
  that flights still refer to raises ``ReferencedRecordError`` (both are
  ``ValueError`` subclasses).

Records use the field names of the assignment brief (``record.schema``),
for example ``{"ID": 1, "Type": "Airline", "Company Name": "Emirates (EK)"}``.

The methods change the records in memory only; the caller decides when to
call ``save_to_file`` (the interface does so after every change and on exit).
"""

import json
import logging
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import config
from record import schema
from record.errors import DuplicateRecordError, RecordStorageError, ReferencedRecordError

logger = logging.getLogger(__name__)


class RecordManager:
    """Manage the lifecycle and persistence of travel-agent records."""

    def __init__(self, filepath=config.DATA_FILE):
        """Initialise the manager and load previously saved records."""
        self.filepath = str(filepath)
        self.records = []
        self.load_warnings = []
        self.load_from_file()

    # ------------------------------------------------------------------
    # PERSISTENCE
    # ------------------------------------------------------------------

    def load_from_file(self):
        """Load existing JSON Lines records into memory (see the module docstring)."""
        self.load_warnings = []
        path = Path(self.filepath)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            self.records = []
            logger.info("No records file at %s; starting with no records.", path)
            return

        try:
            self.records = self._read_records(path)
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            # json.JSONDecodeError is a subclass of ValueError.
            backup = self._back_up_damaged_file(path)
            self.records = []
            message = (f"The records file {path.name} could not be read ({exc}). "
                       "The program started with no records.")
            if backup:
                message += f" The original file was kept as {backup.name}."
            self.load_warnings.append(message)
            logger.error("Could not load records from %s: %s", path, exc)
            return
        logger.info("Loaded %d record(s) from %s.", len(self.records), path)

    @staticmethod
    def _read_records(path):
        """Return the records in ``path``; raise ``ValueError`` on a bad line."""
        records = []
        with open(path, "r", encoding=config.FILE_ENCODING) as file:
            for number, line in enumerate(file, start=1):
                if not line.strip():
                    continue
                record = json.loads(line)
                if isinstance(record, dict) and schema.TYPE not in record and "type" in record:
                    record = RecordManager._upgrade_legacy(record)
                if not isinstance(record, dict) or record.get(schema.TYPE) not in schema.RECORD_TYPES:
                    raise ValueError(f"line {number} is not a Client, Airline or Flight record")
                records.append(record)
        return records

    @staticmethod
    def _upgrade_legacy(old):
        """Return an earlier-format record using the brief's field names."""
        record = {new: old[key] for key, new in schema.LEGACY_KEYS.items() if key in old}
        if record.get(schema.TYPE) == schema.CLIENT:
            record = {key: record.get(key, "") for key in schema.CLIENT_FIELDS}
        elif record.get(schema.TYPE) == schema.FLIGHT:
            day = str(record.get(schema.DATE, "")).strip()
            if len(day) == schema.DAY_LENGTH:
                record[schema.DATE] = f"{day} {schema.LEGACY_DEFAULT_TIME}"
            record = {key: record.get(key, "") for key in schema.FLIGHT_FIELDS}
        logger.info("Upgraded an earlier-format %s record.", record.get(schema.TYPE, "unknown"))
        return record

    @staticmethod
    def _back_up_damaged_file(path):
        """Copy a damaged data file aside; return the backup path or ``None``."""
        stamp = datetime.now().strftime(config.BACKUP_TIMESTAMP_FORMAT)
        backup = path.with_name(path.name + config.CORRUPT_BACKUP_SUFFIX.format(timestamp=stamp))
        try:
            shutil.copy2(path, backup)
        except OSError as exc:
            logger.error("Could not back up damaged records file %s: %s", path, exc)
            return None
        logger.warning("Damaged records file copied to %s.", backup)
        return backup

    def save_to_file(self):
        """Write all records to the JSON Lines file, replacing it atomically.

        Raises ``RecordStorageError`` if the file cannot be written; the
        previous file is then left unchanged.
        """
        path = Path(self.filepath)
        temp_name = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            handle, temp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}-", suffix=".tmp")
            with os.fdopen(handle, "w", encoding=config.FILE_ENCODING) as file:
                for record in self.records:
                    file.write(json.dumps(record) + "\n")
            os.replace(temp_name, path)
        except OSError as exc:
            if temp_name and os.path.exists(temp_name):
                os.unlink(temp_name)
            logger.error("Could not save records to %s: %s", path, exc)
            raise RecordStorageError(path, exc) from exc
        logger.info("Saved %d record(s) to %s.", len(self.records), path)

    # ------------------------------------------------------------------
    # CREATE OPERATIONS
    # ------------------------------------------------------------------

    # Client records contain more fields than the default Pylint threshold.
    # pylint: disable=too-many-arguments, too-many-positional-arguments
    def add_client(self, client_id, name, address_line_1, address_line_2, address_line_3,
                   city, state, zip_code, country, phone_number):
        """Create a client record (fields as in the brief) and add it to the collection."""
        client_id = int(client_id)
        self._ensure_new_id(schema.CLIENT, client_id)
        record = {
            schema.ID: client_id,
            schema.TYPE: schema.CLIENT,
            schema.NAME: name,
            schema.ADDRESS_LINE_1: address_line_1,
            schema.ADDRESS_LINE_2: address_line_2,
            schema.ADDRESS_LINE_3: address_line_3,
            schema.CITY: city,
            schema.STATE: state,
            schema.ZIP_CODE: zip_code,
            schema.COUNTRY: country,
            schema.PHONE_NUMBER: phone_number,
        }
        self.records.append(record)
        logger.info("Created client %d.", client_id)
        return record

    def add_airline(self, airline_id, company_name):
        """Create an airline-company record."""
        airline_id = int(airline_id)
        self._ensure_new_id(schema.AIRLINE, airline_id)
        record = {schema.ID: airline_id, schema.TYPE: schema.AIRLINE, schema.COMPANY_NAME: company_name}
        self.records.append(record)
        logger.info("Created airline %d.", airline_id)
        return record

    def add_flight(self, client_id, airline_id, date_str, start_city, end_city):
        """Create a flight record linking a client to an airline.

        ``date_str`` is the date/time as ``schema.DATE_FORMAT`` text.
        """
        record = {
            schema.TYPE: schema.FLIGHT,
            schema.CLIENT_ID: int(client_id),
            schema.AIRLINE_ID: int(airline_id),
            schema.DATE: date_str,
            schema.START_CITY: start_city,
            schema.END_CITY: end_city,
        }
        self.records.append(record)
        logger.info("Created flight for client %d on %s.", record[schema.CLIENT_ID], date_str)
        return record

    def _ensure_new_id(self, record_type, record_id):
        """Raise ``DuplicateRecordError`` if ``record_id`` is already used."""
        if self.get_record_by_id(record_id, record_type=record_type) is not None:
            raise DuplicateRecordError(f"A {record_type.lower()} with ID {record_id} already exists.")

    # ------------------------------------------------------------------
    # SEARCH AND RETRIEVAL OPERATIONS
    # ------------------------------------------------------------------

    def search_records(self, query=None, record_type=None):
        """Return records matching an optional type and keyword (any stored value)."""
        results = self.records
        if record_type:
            results = [r for r in results if r.get(schema.TYPE) == record_type]
        if query:
            query_str = str(query).lower()
            return [r for r in results if any(query_str in str(val).lower() for val in r.values())]
        return results

    def get_record_by_id(self, record_id, record_type=None):
        """Return the first record matching an ID and optional record type.

        Raises ``ValueError`` if ``record_id`` is not a whole number.
        """
        wanted = int(record_id)
        for r in self.records:
            if r.get(schema.ID) == wanted and (record_type is None or r.get(schema.TYPE) == record_type):
                return r
        return None

    # ------------------------------------------------------------------
    # UPDATE OPERATIONS
    # ------------------------------------------------------------------

    # pylint: disable=too-many-arguments, too-many-positional-arguments
    @staticmethod
    def _flight_matches(record, client_id, airline_id=None, date=None, start_city=None, end_city=None):
        """True when a flight matches the identifiers given (``None`` means any value)."""
        if record.get(schema.TYPE) != schema.FLIGHT or str(record.get(schema.CLIENT_ID)) != str(client_id):
            return False
        wanted = {schema.AIRLINE_ID: airline_id, schema.DATE: date,
                  schema.START_CITY: start_city, schema.END_CITY: end_city}
        return all(value is None or str(record.get(key)) == str(value) for key, value in wanted.items())

    # Flights have no ID of their own, so they are matched on their other fields.
    # pylint: disable=too-many-arguments, too-many-positional-arguments
    def update_record(self, record_id, updated_data, record_type=None, old_airline_id=None,
                      old_date=None, old_start=None, old_end=None):
        """Update the first record matching the identifiers; return True if one changed.

        For flights ``record_id`` is the client ID and the ``old_*`` values
        identify the flight being changed.
        """
        for r in self.records:
            if record_type == schema.FLIGHT:
                found = self._flight_matches(r, record_id, old_airline_id, old_date, old_start, old_end)
            else:
                found = (str(r.get(schema.ID)) == str(record_id)
                         and (not record_type or r.get(schema.TYPE) == record_type))
            if found:
                r.update(updated_data)
                logger.info("Updated %s %s.", str(r.get(schema.TYPE, "record")).lower(), record_id)
                return True
        logger.warning("Update failed: no %s matching %s.", (record_type or "record").lower(), record_id)
        return False

    # ------------------------------------------------------------------
    # DELETE OPERATIONS
    # ------------------------------------------------------------------

    def _ensure_not_referenced(self, record_type, record_id):
        """Raise ``ReferencedRecordError`` if flights still refer to the record."""
        link = schema.LINK_KEY.get(record_type)
        if link and any(r.get(schema.TYPE) == schema.FLIGHT and str(r.get(link)) == str(record_id)
                        for r in self.records):
            raise ReferencedRecordError(
                f"Cannot delete {record_type} (ID: {record_id}): Active flight bookings exist.")

    # pylint: disable=too-many-arguments, too-many-positional-arguments
    def delete_record(self, record_id, record_type=None, airline_id=None, date=None,
                      start_city=None, end_city=None):
        """Delete matching records while protecting referenced ones; return True if any went.

        For flights ``record_id`` is the client ID and the other values identify
        the flight. Without ``record_type`` every record with the ID is removed.
        """
        self._ensure_not_referenced(record_type, record_id)
        initial_count = len(self.records)
        if record_type == schema.FLIGHT:
            self.records = [r for r in self.records
                            if not self._flight_matches(r, record_id, airline_id, date, start_city, end_city)]
        else:
            self.records = [r for r in self.records
                            if not (str(r.get(schema.ID)) == str(record_id)
                                    and (not record_type or r.get(schema.TYPE) == record_type))]
        removed = initial_count - len(self.records)
        if removed:
            logger.info("Deleted %d %s record(s) for %s.", removed, (record_type or "any").lower(), record_id)
        else:
            logger.warning("Delete found no %s matching %s.", (record_type or "record").lower(), record_id)
        return removed > 0
