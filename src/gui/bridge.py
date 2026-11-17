"""The bridge between the HTML page and the record manager.

pywebview exposes the public methods of one Python object to the page's
JavaScript (``window.pywebview.api.<method>(...)``). Calls go straight from
the window to Python, with no web server or HTTP API involved.

``WebApi`` is that object. It translates between the page's field names
("Phone Number", "Client_ID", ...) and the stored record keys, validates
input, applies the flight journey rule and calls ``RecordManager``. Every
result is JSON-friendly:

* success: ``{"ok": True, ...}``
* invalid input: ``{"ok": False, "errors": {field: message}, "messages": [...]}``
* blocked, missing or failed: ``{"ok": False, "error": "explanation"}``
* changed but not written to disk: ``{"ok": True, ..., "save_error": "explanation"}``

Error handling: every public method runs through ``_api_call``, which holds
one lock (pywebview runs each JavaScript call on its own thread) and turns
any unexpected exception into a logged traceback plus a plain error result,
so the page never hangs on a failed call. Attributes start with an
underscore so pywebview does not expose them to the page.
"""

import functools
import logging
import re
import threading
from datetime import date, datetime
from pathlib import Path

import config
from gui.form_schema import ALL_FIELDS, FIELD_MAP, FIELD_SPECS, FORM_ROWS, INT, LINK_FIELDS
from gui.preferences import PreferenceStore
from gui.reference_data import CITY_TO_COUNTRY, WORLD_AIRLINES, WORLD_CITIES
from record import schema
from record.errors import RecordStorageError, ReferencedRecordError
from record.flight_rules import FlightBookingRules
from record.schema import AIRLINE, CLIENT, FLIGHT, RECORD_TYPES

logger = logging.getLogger(__name__)

PHONE_ALLOWED = re.compile(r"^\+?[0-9 ()\-]+$")   # digits, spaces, ( ) - and a leading +
PHONE_MIN_DIGITS = 7

UNEXPECTED_ERROR = ("Something went wrong: {error}. Nothing else was changed. "
                    "Details were written to the log file.")


def _api_call(method):
    """Run a bridge method under the instance lock and contain unexpected errors."""
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        with self._lock:  # pylint: disable=protected-access
            try:
                return method(self, *args, **kwargs)
            except Exception as exc:  # pylint: disable=broad-except
                # The last line of defence: log everything, keep the window usable.
                logger.exception("Unexpected error in %s", method.__name__)
                return {"ok": False, "error": UNEXPECTED_ERROR.format(error=exc)}
    return wrapper


def field_message(message):
    """Sentence-case error text shown under a field."""
    text = message[0].upper() + message[1:] if message else message
    return text if text.endswith(".") else text + "."


def _not_found(record_type):
    return {"ok": False, "error": f"No {record_type.lower()} record found."}


def _unknown_type(record_type):
    logger.warning("Page asked for unknown record type %r.", record_type)
    return {"ok": False, "error": f"Unknown record type {record_type!r}."}


# One object must expose every page action and hold the window state.
class WebApi:  # pylint: disable=too-many-public-methods, too-many-instance-attributes
    """Methods callable from JavaScript. Every result is JSON-serialisable."""

    def __init__(self, record_manager, warnings=None, today=date.today, settings_path=None):
        self._rm = record_manager
        self._warnings = list(warnings or [])
        self._today = today
        self._rules = FlightBookingRules(record_manager)
        self._form_dirty = False
        self._close_approved = False
        self._window = None          # set by the launcher once the window exists
        self._lock = threading.RLock()
        self._last_deleted = None    # (record type, index, record)
        self._path = Path(record_manager.filepath)
        self._preferences = PreferenceStore(
            settings_path or self._path.with_name(config.SETTINGS_FILE_NAME))

    # ------------------------------------------------------- conversions
    def _records(self, record_type):
        return [r for r in self._rm.records if r.get(schema.TYPE) == record_type]

    def _name_of(self, record_type, record_id):
        record = self._rm.get_record_by_id(record_id, record_type=record_type)
        if not record:
            return ""
        return record.get(schema.NAME if record_type == CLIENT else schema.COMPANY_NAME, "")

    def _flights_for(self, key, record_id):
        return [r for r in self._records(FLIGHT) if str(r.get(key)) == str(record_id)]

    @staticmethod
    def _flight_key(record):
        return [record[key] for key in schema.FLIGHT_KEY_FIELDS]

    def _row(self, record):
        """A record as page values (page field names) plus display helpers."""
        record_type = record[schema.TYPE]
        row = {page: record.get(key, "") for page, key in FIELD_MAP[record_type].items()}
        if record_type == FLIGHT:
            row["key"] = self._flight_key(record)
            row["client_name"] = self._name_of(CLIENT, record[schema.CLIENT_ID])
            row["airline_name"] = self._name_of(AIRLINE, record[schema.AIRLINE_ID])
            row["upcoming"] = str(record[schema.DATE]) >= self._today().isoformat()
        else:
            row["key"] = record[schema.ID]
            row["flights"] = len(self._flights_for(schema.LINK_KEY[record_type], record[schema.ID]))
        return row

    @staticmethod
    def _to_record(record_type, data):
        """Page form values -> record dict (strings trimmed, IDs left raw)."""
        record = {schema.TYPE: record_type}
        for page, key in FIELD_MAP[record_type].items():
            value = data.get(page)
            record[key] = str(value if value is not None else "").strip()
        return record

    @staticmethod
    def _invalid(errors):
        logger.info("Input rejected: %s", ", ".join(sorted(errors)))
        return {"ok": False,
                "errors": {f: field_message(m) for f, m in errors.items()},
                "messages": [f"{field}: {msg}" for field, msg in errors.items()]}

    # -------------------------------------------------------- validation
    @staticmethod
    def _parse_int(text):
        text = str(text).strip()
        if not text.isdigit() or int(text) < 1:
            raise ValueError("must be a whole number of 1 or more")
        return int(text)

    # One loop over the field specification needs each spec value by name.
    def _validate(self, record_type, data, editing_key=None):  # pylint: disable=too-many-locals
        """Return ``(record, errors)``; ``record`` is typed and ready to store."""
        record = self._to_record(record_type, data)
        errors = {}
        keys = FIELD_MAP[record_type]
        for page, _label, kind, required, max_length, _hint in FIELD_SPECS[record_type]:
            value = record[keys[page]]
            if required and not value:
                errors[page] = ("select an existing " + LINK_FIELDS[page].lower()
                                if page in LINK_FIELDS else "is required")
            elif len(value) > max_length:
                errors[page] = f"may be at most {max_length} characters"
            elif value and kind == INT:
                try:
                    record[keys[page]] = self._parse_int(value)
                except ValueError as exc:
                    errors[page] = str(exc)
        validators = {CLIENT: self._validate_client, AIRLINE: self._validate_airline,
                      FLIGHT: self._validate_flight}
        validators[record_type](record, errors, editing_key)
        return record, errors

    def _validate_client(self, record, errors, editing_key):
        phone = record[schema.PHONE_NUMBER]
        if phone and "Phone Number" not in errors and (
                not PHONE_ALLOWED.match(phone) or sum(c.isdigit() for c in phone) < PHONE_MIN_DIGITS):
            errors["Phone Number"] = (f"use at least {PHONE_MIN_DIGITS} digits; only spaces, "
                                      "( ) - and a leading + are allowed")
        if (editing_key is None and "ID" not in errors
                and self._rm.get_record_by_id(record[schema.ID], record_type=CLIENT)):
            errors["ID"] = f"a client with ID {record[schema.ID]} already exists"

    def _validate_airline(self, record, errors, editing_key):
        wanted = record[schema.COMPANY_NAME].casefold()
        if wanted and any(
                r[schema.ID] != editing_key
                and r.get(schema.COMPANY_NAME, "").strip().casefold() == wanted
                for r in self._records(AIRLINE)):
            errors["Company Name"] = "another airline already uses this name"
        if (editing_key is None and "ID" not in errors
                and self._rm.get_record_by_id(record[schema.ID], record_type=AIRLINE)):
            errors["ID"] = f"an airline with ID {record[schema.ID]} already exists"

    def _validate_flight(self, record, errors, editing_key):
        for page, record_type in LINK_FIELDS.items():
            key = FIELD_MAP[FLIGHT][page]
            if page not in errors and self._rm.get_record_by_id(
                    record[key], record_type=record_type) is None:
                errors[page] = f"that {record_type.lower()} no longer exists"
        if "Date" not in errors:
            try:
                datetime.strptime(record[schema.DATE], schema.DATE_FORMAT)
            except ValueError:
                errors["Date"] = f"use the format {schema.DATE_FORMAT_HINT}, for example 2026-12-01 09:30"
        if ("Start City" not in errors and "End City" not in errors
                and record[schema.START_CITY].casefold() == record[schema.END_CITY].casefold()):
            errors["End City"] = "must differ from the start city"
        if not errors:
            self._rules.original_flight_key = editing_key
            try:
                message = self._rules.booking_conflict_message(
                    record, exclude_original=editing_key is not None)
            finally:
                self._rules.original_flight_key = None
            if message:
                errors["Start City"] = message

    # ------------------------------------------------------------- reads
    @_api_call
    def bootstrap(self):
        """Everything the page needs when it opens."""
        fields = {
            t: [{"name": n, "label": label, "kind": kind, "required": req,
                 "max_length": length, "hint": hint}
                for n, label, kind, req, length, hint in FIELD_SPECS[t]]
            for t in RECORD_TYPES
        }
        search_fields = {
            t: [{"value": ALL_FIELDS, "label": ALL_FIELDS}]
               + [{"value": f["name"], "label": f["label"]} for f in fields[t]]
            for t in RECORD_TYPES
        }
        logger.info("Page opened: %d record(s) loaded.", len(self._rm.records))
        return {"ok": True, "data_file": str(self._path),
                "preferences": dict(self._preferences.values),
                "fields": fields, "form_rows": FORM_ROWS,
                "search_fields": search_fields,
                "cities": sorted(WORLD_CITIES), "airlines": sorted(WORLD_AIRLINES),
                "city_country": CITY_TO_COUNTRY,
                "warnings": self._warnings, **self.snapshot()}

    @_api_call
    def snapshot(self):
        """Current records, drop-down choices, suggested IDs and summary."""
        def next_id(record_type):
            return max((r[schema.ID] for r in self._records(record_type)), default=0) + 1

        return {
            "ok": True,
            "records": {t: [self._row(r) for r in self._sorted(t)] for t in RECORD_TYPES},
            "choices": {
                CLIENT: [{"id": r[schema.ID], "name": r.get(schema.NAME, ""),
                          "detail": self._choice_detail(CLIENT, r)}
                         for r in self._sorted(CLIENT)],
                AIRLINE: [{"id": r[schema.ID], "name": r.get(schema.COMPANY_NAME, ""),
                           "detail": self._choice_detail(AIRLINE, r)}
                          for r in self._sorted(AIRLINE)],
            },
            "next_id": {CLIENT: next_id(CLIENT), AIRLINE: next_id(AIRLINE)},
            "summary": self.summary(),
        }

    def _sorted(self, record_type):
        records = self._records(record_type)
        if record_type == FLIGHT:
            return records            # stored order = journey order
        return sorted(records, key=lambda r: r[schema.ID])

    def _choice_detail(self, record_type, record):
        count = len(self._flights_for(schema.LINK_KEY[record_type], record[schema.ID]))
        flights = f"{count} flight{'s' * (count != 1)}"
        if record_type == CLIENT:
            place = ", ".join(p for p in (record.get(schema.CITY), record.get(schema.COUNTRY)) if p)
            return f"{place or 'no city'} · {flights}"
        return f"ID {record[schema.ID]} · {flights}"

    @_api_call
    def summary(self):
        """Counts shown in the summary cards."""
        flights = self._records(FLIGHT)
        today = self._today().isoformat()
        upcoming = [f for f in flights if str(f[schema.DATE]) >= today]
        nxt = min(upcoming, key=lambda f: str(f[schema.DATE])) if upcoming else None
        return {
            "clients": len(self._records(CLIENT)),
            "airlines": len(self._records(AIRLINE)),
            "flights": len(flights), "upcoming": len(upcoming),
            "past": len(flights) - len(upcoming),
            "clients_with_flights": len({f[schema.CLIENT_ID] for f in flights}),
            "airlines_with_flights": len({f[schema.AIRLINE_ID] for f in flights}),
            "next": self._row(nxt) if nxt else None,
            "modified": False,
        }

    @_api_call
    def search(self, record_type, text="", field=ALL_FIELDS):
        """Return rows matching ``text`` (case-insensitive substring)."""
        if record_type not in RECORD_TYPES:
            return _unknown_type(record_type)
        query = (text or "").strip().casefold()
        field = field or ALL_FIELDS
        if field != ALL_FIELDS and field not in FIELD_MAP[record_type]:
            return {"ok": False, "error": f"'{field}' is not a {record_type} field."}
        rows = [row for row in (self._row(r) for r in self._sorted(record_type))
                if not query or self._matches(row, query, field, record_type)]
        return {"ok": True, "records": rows}

    @staticmethod
    def _matches(row, query, field, record_type):
        extras = [row.get("client_name", ""), row.get("airline_name", "")]
        if field == ALL_FIELDS:
            values = [str(row.get(p, "")) for p in FIELD_MAP[record_type]] + extras
        elif field == "Client_ID":
            values = [str(row["Client_ID"]), row["client_name"]]
        elif field == "Airline_ID":
            values = [str(row["Airline_ID"]), row["airline_name"]]
        else:
            values = [str(row.get(field, ""))]
        return any(query in str(v).casefold() for v in values)

    def _find(self, record_type, key):
        """The stored record for a page key, or ``None``."""
        if record_type == FLIGHT:
            if not isinstance(key, (list, tuple)) or len(key) != len(schema.FLIGHT_KEY_FIELDS):
                return None
            wanted = [str(k) for k in key]
            for record in self._records(FLIGHT):
                if [str(v) for v in self._flight_key(record)] == wanted:
                    return record
            return None
        try:
            return self._rm.get_record_by_id(int(key), record_type=record_type)
        except (TypeError, ValueError):
            return None

    @_api_call
    def get(self, record_type, key):
        """One record by key."""
        record = self._find(record_type, key)
        if record is None:
            return _not_found(record_type)
        return {"ok": True, "record": self._row(record)}

    # ----------------------------------------------------------- changes
    def _persist(self):
        """Write the records file; return ``{}`` or ``{"save_error": ...}`` for the page."""
        try:
            self._rm.save_to_file()
        except RecordStorageError as exc:
            # The change stays in memory and is saved again on close.
            return {"save_error": f"{exc} The change is kept and will be saved again when you close the program."}
        return {}

    @_api_call
    def create(self, record_type, data):
        """Validate and add a record."""
        if record_type not in RECORD_TYPES:
            return _unknown_type(record_type)
        record, errors = self._validate(record_type, data)
        if errors:
            return self._invalid(errors)
        if record_type == CLIENT:
            stored = self._rm.add_client(*(record[key] for key in schema.CLIENT_FIELDS if key != schema.TYPE))
        elif record_type == AIRLINE:
            stored = self._rm.add_airline(record[schema.ID], record[schema.COMPANY_NAME])
        else:
            stored = self._rm.add_flight(*self._flight_key(record))
        saved = self._persist()
        self._form_dirty = False
        self._last_deleted = None
        return {"ok": True, "record": self._row(stored), **self.snapshot(), **saved}

    @_api_call
    def update(self, record_type, key, data):
        """Validate and replace the record identified by ``key``."""
        original = self._find(record_type, key)
        if original is None:
            return _not_found(record_type)
        data = dict(data)
        if record_type != FLIGHT:
            data["ID"] = original[schema.ID]          # the ID cannot be changed
        record, errors = self._validate(
            record_type, data,
            editing_key=dict(original) if record_type == FLIGHT else original[schema.ID])
        if errors:
            return self._invalid(errors)
        if record_type == FLIGHT:
            client_id, airline_id, travel_date, start, end = self._flight_key(original)
            updated = self._rm.update_record(client_id, record, record_type=FLIGHT,
                                             old_airline_id=airline_id, old_date=travel_date,
                                             old_start=start, old_end=end)
        else:
            updated = self._rm.update_record(original[schema.ID], record, record_type=record_type)
        if not updated:
            return {"ok": False, "error": f"The {record_type.lower()} could not be updated."}
        saved = self._persist()
        self._form_dirty = False
        self._last_deleted = None
        new_key = self._flight_key(record) if record_type == FLIGHT else record[schema.ID]
        return {"ok": True, "record": self._row(self._find(record_type, new_key)),
                **self.snapshot(), **saved}

    @_api_call
    def delete_check(self, record_type, key):
        """Say up front whether a delete is allowed (before asking to confirm)."""
        record = self._find(record_type, key)
        if record is None:
            return _not_found(record_type)
        if record_type == FLIGHT:
            self._rules.original_flight_key = None
            reason = self._rules.deletion_conflict_message(record)
            return {"ok": True, "allowed": reason is None, "linked_flights": 0,
                    "reason": reason or "", "record": self._row(record)}
        linked = len(self._flights_for(schema.LINK_KEY[record_type], record[schema.ID]))
        return {"ok": True, "allowed": linked == 0, "linked_flights": linked,
                "record": self._row(record)}

    @_api_call
    def delete(self, record_type, key):
        """Delete a record that passes ``delete_check``."""
        check = self.delete_check(record_type, key)
        if not check["ok"]:
            return check
        if not check["allowed"]:
            logger.info("Delete of %s %s blocked.", record_type.lower(), key)
            return {"ok": False, "blocked": True,
                    "error": check.get("reason") or "Flights still refer to this record."}
        record = self._find(record_type, key)
        index = next(i for i, r in enumerate(self._rm.records) if r is record)
        try:
            if record_type == FLIGHT:
                client_id, airline_id, travel_date, start, end = self._flight_key(record)
                deleted = self._rm.delete_record(client_id, record_type=FLIGHT, airline_id=airline_id,
                                                 date=travel_date, start_city=start, end_city=end)
            else:
                deleted = self._rm.delete_record(record[schema.ID], record_type=record_type)
        except ReferencedRecordError as exc:
            return {"ok": False, "error": str(exc), "blocked": True}
        if not deleted:
            return {"ok": False, "error": "The record could not be found."}
        saved = self._persist()
        self._form_dirty = False
        self._last_deleted = (record_type, index, dict(record))
        return {"ok": True, "undo": True, "record": self._row(record), **self.snapshot(), **saved}

    @_api_call
    def undo_delete(self):
        """Put the most recently deleted record back where it was."""
        if self._last_deleted is None:
            return {"ok": False, "error": "There is no delete to undo."}
        record_type, index, record = self._last_deleted
        self._rm.records.insert(min(index, len(self._rm.records)), record)
        self._last_deleted = None
        logger.info("Undid the delete of a %s.", record_type.lower())
        saved = self._persist()
        return {"ok": True, "record": self._row(record), **self.snapshot(), **saved}

    @_api_call
    def save_all(self):
        """Write every record to the data file now."""
        saved = self._persist()
        if saved:
            return {"ok": False, "error": saved["save_error"]}
        return {"ok": True, "path": str(self._path), "summary": self.summary()}

    # ------------------------------------------------------- preferences
    @_api_call
    def preferences(self):
        """The current display preferences."""
        return {"ok": True, "preferences": dict(self._preferences.values)}

    @_api_call
    def set_preference(self, name, value):
        """Change one display preference and write settings.json at once."""
        try:
            self._preferences.set(name, value)
        except ValueError as exc:
            logger.warning("Rejected display preference: %s", exc)
            return {"ok": False, "error": str(exc)}
        except OSError as exc:
            logger.error("Could not save display preferences: %s", exc)
            return {"ok": False, "error": f"Preference applied but not saved: {exc}",
                    "preferences": dict(self._preferences.values)}
        return {"ok": True, "preferences": dict(self._preferences.values)}

    # --------------------------------------------------- window plumbing
    @_api_call
    def set_form_dirty(self, dirty):
        """The page reports unsaved edits in its form (used when closing)."""
        self._form_dirty = bool(dirty)
        return {"ok": True}

    @_api_call
    def log_client_error(self, message, source="", line=0):
        """Record a JavaScript error from the page in the log file."""
        text = str(message)[:config.CLIENT_ERROR_MAX_LENGTH]
        logger.error("Page error: %s (%s:%s)", text, str(source)[:200], line)
        return {"ok": True}

    def request_close(self, save=True):
        """Close the window after the user answered a close prompt.

        Not locked: destroying the window runs the closing handler, which
        calls ``save_all`` on another thread.
        """
        self._form_dirty = False
        if not save:
            self._close_approved = True
            logger.warning("User chose to close without saving.")
        if self._window is not None:
            self._window.destroy()
        return {"ok": True}
