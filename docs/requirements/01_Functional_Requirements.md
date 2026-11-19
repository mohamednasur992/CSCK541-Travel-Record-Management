# Functional Requirements

**Source:** *Core scope* = stated in the project description; *Derived* = implied by it; *Group design* = added by the team.
**Verification:** *Automated* = a test in `src/tests/` runs the real code (paths are relative to `src/tests/`).

## 1. Record management

| ID | Requirement – the system shall… | Source | Verification |
|---|---|---|---|
| FR-01 | manage three record types – **Client**, **Airline** and **Flight** – held together in one in-memory list of dictionaries (`RecordManager.records`). | Core scope | Automated – `unit/test_fr_record_model.py` |
| FR-02 | give every record a `Type` field (`Client`, `Airline` or `Flight`) that identifies its record type. | Derived | Automated – `unit/test_fr_record_model.py` |
| FR-03 | hold for a **Client** exactly the fields of the brief: `ID` (integer), `Type`, `Name`, `Address Line 1`, `Address Line 2`, `Address Line 3`, `City`, `State`, `Zip Code`, `Country`, `Phone Number` (all text apart from `ID`). Required: `ID`, `Name`, `Address Line 1`, `City`, `Country`, `Phone Number`. Optional: `Address Line 2`, `Address Line 3`, `State`, `Zip Code`. | Core scope | Automated – `unit/test_fr_record_model.py` |
| FR-04 | hold for an **Airline**: `ID` (integer), `Type`, `Company Name`. All are required. | Core scope | Automated – `unit/test_fr_record_model.py` |
| FR-05 | hold for a **Flight**: `Client_ID` (integer), `Airline_ID` (integer), `Date` (date and time, stored as `YYYY-MM-DD HH:MM`), `Start City`, `End City` (plus `Type`). All are required. | Core scope | Automated – `unit/test_fr_record_model.py` |

## 2. Create, search, display, update and delete

| ID | Requirement – the system shall… | Source | Verification |
|---|---|---|---|
| FR-06 | let the user **create** a record of each type through the GUI (one tab per type: Clients, Airlines, Flights). | Core scope | Automated – `unit/test_fr_operations.py`; `e2e/test_gui_end_to_end.py` |
| FR-07 | let the user **search** the records of the current tab; the table filters as the user types and matches any stored value of the record. | Core scope | Automated – `unit/test_fr_operations.py`; `e2e/test_gui_end_to_end.py` |
| FR-08 | **display** records of each type in a table, let the user sort it by any column, and show the full details of the selected record in the form. | Core scope | Automated – `unit/test_fr_operations.py`; `e2e/test_gui_end_to_end.py` |
| FR-09 | let the user **update** any field of an existing record except a client's or airline's ID, which is read-only after creation. | Core scope | Automated – `unit/test_fr_operations.py`; `e2e/test_gui_end_to_end.py` |
| FR-10 | let the user **delete** a record after confirming in a dialog that names the record. | Core scope | Automated – `unit/test_fr_operations.py`; `e2e/test_gui_end_to_end.py` |
| FR-11 | identify a flight, which has no ID of its own, by the combination of `Client_ID`, `Airline_ID`, `Date`, `Start City` and `End City` for display, update and delete. | Derived | Automated – `unit/test_fr_operations.py` |
| FR-12 | list clients and airlines as `ID - name` choices when a flight is booked, so the user selects existing records instead of typing IDs. | Group design | Automated – `unit/test_fr_operations.py`; `e2e/test_gui_end_to_end.py` |
| FR-13 | offer searchable suggestions for city and airline-company fields, while still accepting text that is not in the list. | Group design | Automated – `unit/test_fr_operations.py` |
| FR-14 | suggest a country when the user selects a client's city, without overwriting a value the user has already entered. | Group design | Automated – `unit/test_fr_operations.py`; `e2e/test_gui_end_to_end.py` |
| FR-15 | show the result of every action (success, failure or cancellation) to the user as a short notification, and show field errors beside the field they belong to. | Group design | Automated – `unit/test_fr_operations.py`; `e2e/test_gui_end_to_end.py` |

## 3. Validation and data integrity

| ID | Requirement – the system shall… | Source | Verification |
|---|---|---|---|
| FR-16 | validate input before storing a record: required fields present; a phone number has at least 7 digits and only digits, spaces and `+ - ( )`; a flight's date and time is a valid `YYYY-MM-DD HH:MM` value; a flight's end city differs from its start city (ignoring case); and a city name (a client's city, a flight's start and end city) is 2 to 60 letters of any alphabet joined by spaces, hyphens, apostrophes or full stops, so digits and symbols such as `@#$%` are refused with a message that shows an example. | Derived | Automated – `unit/test_fr_validation_integrity.py` (TestFieldValidation, TestCityNames); `negative/test_error_injection.py`; `e2e/test_gui_end_to_end.py` |
| FR-17 | generate the next free ID (highest existing ID + 1) for a new client or airline, and reject a new client or airline whose ID already exists. | Derived | Automated – `unit/test_fr_validation_integrity.py`; `negative/test_error_injection.py` |
| FR-18 | reject an airline whose company name (ignoring case and surrounding spaces) is already used by another airline. | Derived | Automated – `unit/test_fr_validation_integrity.py`; `e2e/test_gui_end_to_end.py` |
| FR-19 | allow a flight only for an existing client and an existing airline, chosen from the drop-downs. | Derived | Automated – `unit/test_fr_validation_integrity.py` |
| FR-20 | refuse to delete a client or airline that is referenced by a flight, and tell the user why. | Derived | Automated – `unit/test_fr_validation_integrity.py`; `e2e/test_gui_end_to_end.py` |
| FR-21 | keep each client's flights on one calendar day (the date part of `Date`) as a single linear journey: the first leg is always allowed; each next leg starts at the previous leg's destination; no city is used as a start city twice; an identical booking is rejected. City comparison ignores case and surrounding spaces. This rule applies when a flight is created, updated or deleted, so an update or delete cannot break the remaining journey. | Group design | Automated – `unit/test_flight_booking_rule.py` (15 tests); `unit/test_fr_validation_integrity.py`; `e2e/test_gui_end_to_end.py` |

## 4. Persistence

| ID | Requirement – the system shall… | Source | Verification |
|---|---|---|---|
| FR-22 | store records on the file system as **JSON Lines** (`src/record/record.jsonl`): UTF-8, one record per line. Records are written after every create, update and delete, and again when the application closes. | Core scope | Automated – `integration/test_fr_persistence_files.py`; `negative/test_error_injection.py`; `e2e/test_gui_end_to_end.py` |
| FR-23 | check for an existing records file when it starts and load it; if there is no file, start with an empty list and create the storage folder. | Core scope | Automated – `integration/test_fr_persistence_files.py` |
| FR-24 | if the records file cannot be read or contains invalid JSON, copy the damaged file to `record.jsonl.corrupt-<date-time>`, warn the user in the interface, and start with an empty list instead of crashing. | Derived | Automated – `integration/test_fr_persistence_files.py`; `negative/test_error_injection.py` |
| FR-25 | save all records when the application closes normally, and also when it is stopped from the keyboard (Ctrl+C). | Core scope | Automated – `integration/test_fr_persistence_files.py`; `unit/test_main.py` |
| FR-26 | keep every record in the file in a form that reloads to the same data (integer IDs stay integers, text stays text), and upgrade records saved by the earlier version of the program (lower-case keys) to the brief's field names when they are loaded. | Derived | Automated – `integration/test_fr_persistence_files.py` |
| FR-27 | show the application's logo in the interface when the image file is present, and start without it when the file is missing. | Group design | Automated – `integration/test_fr_persistence_files.py`; `e2e/test_gui_end_to_end.py` |
| FR-28 | let the user undo the most recent delete (the Undo button in the notification, or Ctrl+Z) until the next change; the record returns to its original position, so a flight journey is not reordered. | Group design | Automated – `unit/test_fr_operations.py`; `e2e/test_gui_end_to_end.py` |
| FR-29 | keep the display preferences (theme, contrast, effects, density, panel width) in `settings.json` beside the records file; unknown or damaged values fall back to the defaults. | Group design | Automated – `unit/test_schema_and_config.py`; `integration/test_workflows.py`; `negative/test_error_injection.py`; `e2e/test_gui_end_to_end.py` |
| FR-30 | list, for every client and airline, the individual flights that refer to it (date, route and the airline or client), as an expandable list on its card and in the message shown when a delete is blocked; selecting a flight in the list opens it in the Flights view. | Group design | Automated – `unit/test_fr_operations.py` (TestLinkedFlights); `e2e/test_gui_end_to_end.py` |
