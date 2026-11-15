# Functional Requirements

**Source:** *Core scope* = stated in the project description; *Derived* = implied by it; *Group design* = added by the team.
**Verification:** *Automated* = unit test on the real code; *Manual* = checked by hand in the running application.

## 1. Record management

| ID | Requirement – the system shall… | Source | Verification |
|---|---|---|---|
| FR-01 | manage three record types – **Client**, **Airline** and **Flight** – held together in one in-memory list of dictionaries (`RecordManager.records`). | Core scope | Manual |
| FR-02 | give every record a `type` field (`Client`, `Airline` or `Flight`) that identifies its record type. | Derived | Manual |
| FR-03 | hold for a **Client**: `id` (integer), `type`, `name`, `email`, `phone_number`, `city`, `address`, `passport_number`, `nationality`, `emergency_contact`. Required: `name`, `passport_number`. Optional: all other fields. | Core scope | Manual |
| FR-04 | hold for an **Airline**: `id` (integer), `type`, `company_name`. `company_name` is required. | Core scope | Manual |
| FR-05 | hold for a **Flight**: `client_id` (integer), `airline_id` (integer), `date` (`YYYY-MM-DD`), `start_city`, `end_city`. All are required. | Core scope | Manual |

## 2. Create, search, display, update and delete

| ID | Requirement – the system shall… | Source | Verification |
|---|---|---|---|
| FR-06 | let the user **create** a record of each type through the GUI (one tab per type: Clients, Airlines, Flights). | Core scope | Manual |
| FR-07 | let the user **search** the records of the current tab; the table filters as the user types and matches any stored value of the record. | Core scope | Manual |
| FR-08 | **display** records of each type in a table, let the user sort it by any column, and show the full details of the selected record in the form. | Core scope | Manual |
| FR-09 | let the user **update** any field of an existing record except a client's or airline's ID, which is read-only after creation. | Core scope | Manual |
| FR-10 | let the user **delete** a record after confirming in a dialog that names the record. | Core scope | Manual |
| FR-11 | identify a flight, which has no ID of its own, by the combination of `client_id`, `airline_id`, `date`, `start_city` and `end_city` for display, update and delete. | Derived | Manual |
| FR-12 | list clients and airlines as `ID - name` choices when a flight is booked, so the user selects existing records instead of typing IDs. | Group design | Manual |
| FR-13 | offer searchable suggestions for city and airline-company fields, while still accepting text that is not in the list. | Group design | Manual |
| FR-14 | suggest a nationality when the user selects a client's city, without overwriting a value the user has already entered. | Group design | Manual |
| FR-15 | show the result of every action (success, failure or cancellation) in the status bar. | Group design | Manual |

## 3. Validation and data integrity

| ID | Requirement – the system shall… | Source | Verification |
|---|---|---|---|
| FR-16 | validate input before storing a record: required fields present, an email (if given) contains `@` and a dot after it, a flight's date is a valid `YYYY-MM-DD` date, and a flight's end city differs from its start city (ignoring case). | Derived | Manual |
| FR-17 | generate the next free ID (highest existing ID + 1) for a new client or airline, and reject a new client or airline whose ID already exists. | Derived | Manual |
| FR-18 | reject an airline whose company name (ignoring case and surrounding spaces) is already used by another airline. | Derived | Manual |
| FR-19 | allow a flight only for an existing client and an existing airline, chosen from the drop-downs. | Derived | Manual |
| FR-20 | refuse to delete a client or airline that is referenced by a flight, and tell the user why. | Derived | Manual |
| FR-21 | keep each client's flights on one date as a single linear journey: the first leg is always allowed; each next leg starts at the previous leg's destination; no city is used as a start city twice; an identical booking is rejected. City comparison ignores case and surrounding spaces. This rule applies when a flight is created, updated or deleted, so an update or delete cannot break the remaining journey. | Group design | Automated – `BookingDateConflictTests` in `test_flight_booking_rule.py` (15 tests) |

## 4. Persistence

| ID | Requirement – the system shall… | Source | Verification |
|---|---|---|---|
| FR-22 | store records on the file system as **JSON Lines** (`src/record/record.jsonl`): UTF-8, one record per line. Records are written when the application closes, and also after every update and delete. | Core scope | Manual |
| FR-23 | check for an existing records file when it starts and load it; if there is no file, start with an empty list and create the storage folder. | Core scope | Manual |
| FR-24 | if the records file cannot be read or contains invalid JSON, report the error and start with an empty list instead of crashing. | Derived | Manual |
| FR-25 | save all records when the application closes normally, and also when it is stopped from the keyboard (Ctrl+C). | Core scope | Manual |
| FR-26 | keep every record in the file in a form that reloads to the same data (integer IDs stay integers, text stays text). | Derived | Manual |
| FR-27 | show the application's logo in the interface when the image file is present, and start without it when the file is missing. | Group design | Manual |
