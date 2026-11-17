"""The bridge between the HTML page and the record manager.

pywebview exposes the public methods of one Python object to the page's
JavaScript (``window.pywebview.api.<method>(...)``). Calls go straight from
the window to Python, with no web server or HTTP API involved.

``WebApi`` is that object. It translates between the page's field names
("Phone Number", "Client_ID", ...) and this project's record keys
("phone_number", "client_id", ...), validates input, applies the flight
journey rule and calls ``RecordManager``. Every result is JSON-friendly:

* success: ``{"ok": True, ...}``
* invalid input: ``{"ok": False, "errors": {field: message}, "messages": [...]}``
* blocked or missing: ``{"ok": False, "error": "explanation"}``

Attributes start with an underscore so pywebview does not expose them to
the page. pywebview runs each JavaScript call on its own thread, so every
public method takes one lock and the records are never read while changing.

Display preferences (theme, contrast, effects, density, panel width) are
kept in ``settings.json`` next to the data file.
"""

import functools
import json
import os
import tempfile
import threading
from datetime import date, datetime
from pathlib import Path

# pylint: disable=import-error
from gui.constants import CITY_TO_NATIONALITY, WORLD_AIRLINES, WORLD_CITIES
from gui.flight_tab import FlightBookingRules

CLIENT = "Client"
AIRLINE = "Airline"
FLIGHT = "Flight"
RECORD_TYPES = (CLIENT, AIRLINE, FLIGHT)
ALL_FIELDS = "All fields"
DATE_FORMAT = "%Y-%m-%d"

# Page field name -> stored record key, per record type.
FIELD_MAP = {
    CLIENT: {
        "ID": "id", "Name": "name", "Email": "email",
        "Phone Number": "phone_number", "Emergency Contact": "emergency_contact",
        "City": "city", "Nationality": "nationality", "Address": "address",
        "Passport Number": "passport_number",
    },
    AIRLINE: {"ID": "id", "Company Name": "company_name"},
    FLIGHT: {
        "Client_ID": "client_id", "Airline_ID": "airline_id", "Date": "date",
        "Start City": "start_city", "End City": "end_city",
    },
}
# (page name, label, kind, required, max length, hint)
FIELD_SPECS = {
    CLIENT: (
        ("ID", "Client ID", "int", True, 9, ""),
        ("Name", "Full Name", "str", True, 100, ""),
        ("Email", "Email", "str", False, 100, "optional"),
        ("Phone Number", "Phone Number", "str", False, 30, "optional"),
        ("Emergency Contact", "Emergency Contact", "str", False, 100, "optional"),
        ("City", "City", "str", False, 100, "optional"),
        ("Nationality", "Nationality", "str", False, 60, "suggested from city"),
        ("Address", "Address", "str", False, 200, "optional"),
        ("Passport Number", "Passport / ID", "str", True, 50, ""),
    ),
    AIRLINE: (
        ("ID", "Airline ID", "int", True, 9, ""),
        ("Company Name", "Company Name", "str", True, 100, ""),
    ),
    FLIGHT: (
        ("Client_ID", "Client", "int", True, 9, "must already exist"),
        ("Airline_ID", "Airline", "int", True, 9, "must already exist"),
        ("Date", "Travel Date", "date", True, 10, "YYYY-MM-DD"),
        ("Start City", "Start City", "str", True, 100, ""),
        ("End City", "Destination", "str", True, 100, ""),
    ),
}
FORM_ROWS = {
    CLIENT: [["ID", "Name"], ["Email"], ["Phone Number", "Emergency Contact"],
             ["City", "Nationality"], ["Address"], ["Passport Number"]],
    AIRLINE: [["ID", "Company Name"]],
    FLIGHT: [["Client_ID"], ["Airline_ID"], ["Date"], ["Start City", "End City"]],
}
LINK_FIELDS = {"Client_ID": CLIENT, "Airline_ID": AIRLINE}

# Display preferences: allowed values (first = default) or a numeric range.
PREFERENCE_CHOICES = {
    "theme": ("system", "light", "dark"),
    "contrast": ("system", "standard", "high"),
    "effects": ("system", "standard", "low"),
    "density": ("comfortable", "compact"),
}
PANEL_WIDTH_RANGE = (360, 720)
DEFAULT_PREFERENCES = {**{k: v[0] for k, v in PREFERENCE_CHOICES.items()},
                       "panel_width": 440}
SETTINGS_FILE = "settings.json"


def _valid_preference(name, value):
    if name == "panel_width":
        low, high = PANEL_WIDTH_RANGE
        return (isinstance(value, int) and not isinstance(value, bool)
                and low <= value <= high)
    return name in PREFERENCE_CHOICES and value in PREFERENCE_CHOICES[name]


def _locked(method):
    """Run a bridge method while holding the instance's lock."""
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        with self._lock:  # pylint: disable=protected-access
            return method(self, *args, **kwargs)
    return wrapper


def field_message(message):
    """Sentence-case error text shown under a field."""
    text = message[0].upper() + message[1:] if message else message
    return text if text.endswith(".") else text + "."


class WebApi:  # pylint: disable=too-many-public-methods
    """Methods callable from JavaScript. Every result is JSON-serialisable."""

    def __init__(self, record_manager, warnings=None, today=date.today,
                 settings_path=None):
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
        self._settings_path = (Path(settings_path) if settings_path
                               else self._path.with_name(SETTINGS_FILE))
        self._preferences = self._load_preferences()

    # ------------------------------------------------------- conversions
    def _records(self, record_type):
        return [r for r in self._rm.records if r.get("type") == record_type]

    def _name_of(self, record_type, record_id):
        record = self._rm.get_record_by_id(record_id, record_type=record_type)
        if not record:
            return ""
        return record.get("name" if record_type == CLIENT else "company_name", "")

    def _flights_for(self, field, record_id):
        return [r for r in self._records(FLIGHT) if str(r.get(field)) == str(record_id)]

    @staticmethod
    def _flight_key(record):
        return [record["client_id"], record["airline_id"], record["date"],
                record["start_city"], record["end_city"]]

    def _row(self, record):
        """A record as page values (page field names) plus display helpers."""
        record_type = record["type"]
        row = {page: record.get(key, "") for page, key in FIELD_MAP[record_type].items()}
        if record_type == FLIGHT:
            row["key"] = self._flight_key(record)
            row["client_name"] = self._name_of(CLIENT, record["client_id"])
            row["airline_name"] = self._name_of(AIRLINE, record["airline_id"])
            row["upcoming"] = str(record["date"]) >= self._today().isoformat()
        else:
            row["key"] = record["id"]
            link = "client_id" if record_type == CLIENT else "airline_id"
            row["flights"] = len(self._flights_for(link, record["id"]))
        return row

    def _to_record(self, record_type, data):
        """Page form values -> record dict (strings trimmed, IDs left raw)."""
        record = {"type": record_type}
        for page, key in FIELD_MAP[record_type].items():
            record[key] = str(data.get(page, "") if data.get(page) is not None else "").strip()
        return record

    @staticmethod
    def _invalid(errors):
        messages = [f"{field}: {msg}" for field, msg in errors.items()]
        return {"ok": False,
                "errors": {f: field_message(m) for f, m in errors.items()},
                "messages": messages}

    # -------------------------------------------------------- validation
    @staticmethod
    def _parse_int(text):
        text = str(text).strip()
        if not text.isdigit() or int(text) < 1:
            raise ValueError("must be a whole number of 1 or more")
        return int(text)

    def _validate(self, record_type, data, editing_key=None):
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
            elif value and kind == "int":
                try:
                    record[keys[page]] = self._parse_int(value)
                except ValueError as exc:
                    errors[page] = str(exc)
        if record_type == CLIENT:
            self._validate_client(record, errors, editing_key)
        elif record_type == AIRLINE:
            self._validate_airline(record, errors, editing_key)
        else:
            self._validate_flight(record, errors, editing_key)
        return record, errors

    def _validate_client(self, record, errors, editing_key):
        email = record["email"]
        if email and "Email" not in errors and (
                "@" not in email or "." not in email.rsplit("@", 1)[-1]):
            errors["Email"] = "enter a valid email address or leave it blank"
        if (editing_key is None and "ID" not in errors and self._rm.get_record_by_id(
                record["id"], record_type=CLIENT)):
            errors["ID"] = f"a client with ID {record['id']} already exists"

    def _validate_airline(self, record, errors, editing_key):
        wanted = record["company_name"].casefold()
        if wanted and any(
                r["id"] != editing_key and r.get("company_name", "").strip().casefold() == wanted
                for r in self._records(AIRLINE)):
            errors["Company Name"] = "another airline already uses this name"
        if (editing_key is None and "ID" not in errors and self._rm.get_record_by_id(
                record["id"], record_type=AIRLINE)):
            errors["ID"] = f"an airline with ID {record['id']} already exists"

    def _validate_flight(self, record, errors, editing_key):
        for page, record_type in LINK_FIELDS.items():
            key = FIELD_MAP[FLIGHT][page]
            if page not in errors and self._rm.get_record_by_id(
                    record[key], record_type=record_type) is None:
                errors[page] = f"that {record_type.lower()} no longer exists"
        if "Date" not in errors:
            try:
                datetime.strptime(record["date"], DATE_FORMAT)
            except ValueError:
                errors["Date"] = "use the format YYYY-MM-DD"
        if ("Start City" not in errors and "End City" not in errors
                and record["start_city"].casefold() == record["end_city"].casefold()):
            errors["End City"] = "must differ from the start city"
        if not errors:
            self._rules.original_flight_key = editing_key
            message = self._rules.booking_conflict_message(
                record, exclude_original=editing_key is not None)
            self._rules.original_flight_key = None
            if message:
                errors["Start City"] = message

    # ------------------------------------------------------------- reads
    @_locked
    def bootstrap(self):
        """Everything the page needs when it opens."""
        fields = {
            t: [{"name": n, "label": label, "kind": kind, "required": req,
                 "max_length": length, "hint": hint}
                for n, label, kind, req, length, hint in FIELD_SPECS[t]]
            for t in RECORD_TYPES
        }
        search_fields = {
            t: [{"value": ALL_FIELDS, "label": "All fields"}]
               + [{"value": f["name"], "label": f["label"]} for f in fields[t]]
            for t in RECORD_TYPES
        }
        return {"ok": True, "data_file": str(self._path),
                "preferences": dict(self._preferences),
                "fields": fields, "form_rows": FORM_ROWS,
                "search_fields": search_fields,
                "cities": sorted(WORLD_CITIES), "airlines": sorted(WORLD_AIRLINES),
                "city_nationality": CITY_TO_NATIONALITY,
                "warnings": self._warnings, **self.snapshot()}

    @_locked
    def snapshot(self):
        """Current records, drop-down choices, suggested IDs and summary."""
        def next_id(record_type):
            return max((r["id"] for r in self._records(record_type)), default=0) + 1

        return {
            "ok": True,
            "records": {t: [self._row(r) for r in self._sorted(t)] for t in RECORD_TYPES},
            "choices": {
                CLIENT: [{"id": r["id"], "name": r.get("name", ""),
                          "detail": self._choice_detail(CLIENT, r)}
                         for r in self._sorted(CLIENT)],
                AIRLINE: [{"id": r["id"], "name": r.get("company_name", ""),
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
        return sorted(records, key=lambda r: r["id"])

    def _choice_detail(self, record_type, record):
        link = "client_id" if record_type == CLIENT else "airline_id"
        count = len(self._flights_for(link, record["id"]))
        flights = f"{count} flight{'s' * (count != 1)}"
        if record_type == CLIENT:
            place = ", ".join(p for p in (record.get("city"), record.get("nationality")) if p)
            return f"{place or 'no city'} · {flights}"
        return f"ID {record['id']} · {flights}"

    @_locked
    def summary(self):
        """Counts shown in the summary cards."""
        flights = self._records(FLIGHT)
        today = self._today().isoformat()
        upcoming = [f for f in flights if str(f["date"]) >= today]
        nxt = min(upcoming, key=lambda f: str(f["date"])) if upcoming else None
        return {
            "clients": len(self._records(CLIENT)),
            "airlines": len(self._records(AIRLINE)),
            "flights": len(flights), "upcoming": len(upcoming),
            "past": len(flights) - len(upcoming),
            "clients_with_flights": len({f["client_id"] for f in flights}),
            "airlines_with_flights": len({f["airline_id"] for f in flights}),
            "next": self._row(nxt) if nxt else None,
            "modified": False,
        }

    @_locked
    def search(self, record_type, text="", field=ALL_FIELDS):
        """Return rows matching ``text`` (case-insensitive substring)."""
        if record_type not in RECORD_TYPES:
            return {"ok": False, "error": f"Unknown record type {record_type!r}."}
        query = (text or "").strip().casefold()
        field = field or ALL_FIELDS
        if field != ALL_FIELDS and field not in FIELD_MAP[record_type]:
            return {"ok": False, "error": f"'{field}' is not a {record_type} field."}
        rows = []
        for record in self._sorted(record_type):
            row = self._row(record)
            if not query or self._matches(row, query, field, record_type):
                rows.append(row)
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
            if not isinstance(key, (list, tuple)) or len(key) != 5:
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

    @_locked
    def get(self, record_type, key):
        """One record by key."""
        record = self._find(record_type, key)
        if record is None:
            return {"ok": False, "error": f"No {record_type.lower()} record found."}
        return {"ok": True, "record": self._row(record)}

    # ----------------------------------------------------------- changes
    def _persist(self):
        self._rm.save_to_file()

    @_locked
    def create(self, record_type, data):
        """Validate and add a record."""
        if record_type not in RECORD_TYPES:
            return {"ok": False, "error": f"Unknown record type {record_type!r}."}
        record, errors = self._validate(record_type, data)
        if errors:
            return self._invalid(errors)
        if record_type == CLIENT:
            stored = self._rm.add_client(
                record["id"], record["name"], record["email"], record["phone_number"],
                record["city"], record["address"], record["passport_number"],
                record["nationality"], record["emergency_contact"])
        elif record_type == AIRLINE:
            stored = self._rm.add_airline(record["id"], record["company_name"])
        else:
            stored = self._rm.add_flight(
                record["client_id"], record["airline_id"], record["date"],
                record["start_city"], record["end_city"])
        self._persist()
        self._form_dirty = False
        self._last_deleted = None
        return {"ok": True, "record": self._row(stored), **self.snapshot()}

    @_locked
    def update(self, record_type, key, data):
        """Validate and replace the record identified by ``key``."""
        original = self._find(record_type, key)
        if original is None:
            return {"ok": False, "error": f"No {record_type.lower()} record found."}
        data = dict(data)
        if record_type != FLIGHT:
            data["ID"] = original["id"]          # the ID cannot be changed
        record, errors = self._validate(
            record_type, data,
            editing_key=dict(original) if record_type == FLIGHT else original["id"])
        if errors:
            return self._invalid(errors)
        if record_type == FLIGHT:
            updated = self._rm.update_record(
                original["client_id"], record, record_type=FLIGHT,
                old_airline_id=original["airline_id"], old_date=original["date"],
                old_start=original["start_city"], old_end=original["end_city"])
        else:
            updated = self._rm.update_record(original["id"], record,
                                             record_type=record_type)
        if not updated:
            return {"ok": False, "error": f"The {record_type.lower()} could not be updated."}
        self._form_dirty = False
        self._last_deleted = None
        return {"ok": True, "record": self._row(self._find(
            record_type, self._flight_key(record) if record_type == FLIGHT
            else record["id"])), **self.snapshot()}

    @_locked
    def delete_check(self, record_type, key):
        """Say up front whether a delete is allowed (before asking to confirm)."""
        record = self._find(record_type, key)
        if record is None:
            return {"ok": False, "error": f"No {record_type.lower()} record found."}
        if record_type == FLIGHT:
            self._rules.original_flight_key = None
            reason = self._rules.deletion_conflict_message(record)
            return {"ok": True, "allowed": reason is None, "linked_flights": 0,
                    "reason": reason or "", "record": self._row(record)}
        link = "client_id" if record_type == CLIENT else "airline_id"
        linked = len(self._flights_for(link, record["id"]))
        return {"ok": True, "allowed": linked == 0, "linked_flights": linked,
                "record": self._row(record)}

    @_locked
    def delete(self, record_type, key):
        """Delete a record that passed ``delete_check``."""
        check = self.delete_check(record_type, key)
        if not check["ok"]:
            return check
        if not check["allowed"]:
            return {"ok": False, "blocked": True,
                    "error": check.get("reason") or "Flights still refer to this record."}
        record = self._find(record_type, key)
        index = next(i for i, r in enumerate(self._rm.records) if r is record)
        try:
            if record_type == FLIGHT:
                deleted = self._rm.delete_record(
                    record["client_id"], record_type=FLIGHT,
                    airline_id=record["airline_id"], date=record["date"],
                    start_city=record["start_city"], end_city=record["end_city"])
            else:
                deleted = self._rm.delete_record(record["id"], record_type=record_type)
        except ValueError as exc:
            return {"ok": False, "error": str(exc), "blocked": True}
        if not deleted:
            return {"ok": False, "error": "The record could not be found."}
        self._persist()
        self._form_dirty = False
        self._last_deleted = (record_type, index, dict(record))
        return {"ok": True, "undo": True, "record": self._row(record), **self.snapshot()}

    @_locked
    def undo_delete(self):
        """Put the most recently deleted record back where it was."""
        if self._last_deleted is None:
            return {"ok": False, "error": "There is no delete to undo."}
        record_type, index, record = self._last_deleted
        self._rm.records.insert(min(index, len(self._rm.records)), record)
        self._last_deleted = None
        self._persist()
        return {"ok": True, "record": self._row(record), **self.snapshot()}

    @_locked
    def save_all(self):
        """Write every record to the data file now."""
        try:
            self._persist()
        except OSError as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "path": str(self._path), "summary": self.summary()}

    # ------------------------------------------------------- preferences
    def _load_preferences(self):
        prefs = dict(DEFAULT_PREFERENCES)
        try:
            stored = json.loads(self._settings_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return prefs                       # missing or damaged: defaults
        if isinstance(stored, dict):
            prefs.update({k: v for k, v in stored.items() if _valid_preference(k, v)})
        return prefs

    @_locked
    def preferences(self):
        """The current display preferences."""
        return {"ok": True, "preferences": dict(self._preferences)}

    @_locked
    def set_preference(self, name, value):
        """Change one display preference and write settings.json at once."""
        if not _valid_preference(name, value):
            return {"ok": False, "error": f"Unknown preference {name!r} or value {value!r}."}
        self._preferences[name] = value
        try:
            self._settings_path.parent.mkdir(parents=True, exist_ok=True)
            handle, tmp = tempfile.mkstemp(dir=self._settings_path.parent,
                                           prefix=".settings-", suffix=".tmp")
            try:
                with os.fdopen(handle, "w", encoding="utf-8") as stream:
                    json.dump(self._preferences, stream, indent=2)
                os.replace(tmp, self._settings_path)
            except BaseException:
                os.unlink(tmp)
                raise
        except OSError as exc:
            return {"ok": False, "error": f"Preference applied but not saved: {exc}",
                    "preferences": dict(self._preferences)}
        return {"ok": True, "preferences": dict(self._preferences)}

    # --------------------------------------------------- window plumbing
    @_locked
    def set_form_dirty(self, dirty):
        """The page reports unsaved edits in its form (used when closing)."""
        self._form_dirty = bool(dirty)
        return {"ok": True}

    def request_close(self, save=True):
        """Close the window after the user answered a close prompt."""
        self._form_dirty = False
        if not save:
            self._close_approved = True
        if self._window is not None:
            self._window.destroy()
        return {"ok": True}
