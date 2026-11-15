# Non-Functional Requirements

**Source:** *Core scope* = stated in the project description; *Derived* = implied by it; *Group design* = added by the team.
**Verification:** *Automated* = unit test on the real code; *Manual* = checked by hand; *Inspection* = checked by reading the code or repository.

## 1. Usability

| ID | Requirement – the system shall… | Source | Verification |
|---|---|---|---|
| NFR-01 | make Create, Search, Update and Delete obvious: one tab per record type, with the form beside the table and clearly labelled buttons. | Core scope | Manual |
| NFR-02 | prevent errors where possible (drop-downs for client and airline, calendar for dates, read-only generated IDs, suggestions for cities) and ask for confirmation before a delete. | Group design | Manual |
| NFR-03 | state errors in plain language that says which field is wrong and how to fix it. | Group design | Manual |

## 2. Portability and constraints

| ID | Requirement – the system shall… | Source | Verification |
|---|---|---|---|
| NFR-04 | run locally as a desktop application on Python 3 with Tkinter, started with `python src/main.py`. It is developed and tested on Windows; macOS and Linux are expected to work because only portable libraries are used. | Core scope | Manual (Windows) |
| NFR-05 | use only the packages listed in `requirements.txt` (`jsonlines`, `tkcalendar`, `Pillow`) and the Python standard library. | Core scope | Inspection |
| NFR-06 | not use a database server, web server, cloud service or network connection; all data stays in the local JSON Lines file. | Core scope | Inspection |

## 3. Reliability

| ID | Requirement – the system shall… | Source | Verification |
|---|---|---|---|
| NFR-07 | never store a record that fails validation, and leave the existing data unchanged when an action is rejected. | Derived | Manual |
| NFR-08 | keep the interface running when the records file is missing or unreadable (see FR-23, FR-24). | Derived | Manual |
| NFR-09 | write the file again after every update and delete, so a crash soon after such a change loses nothing. | Group design | Manual |

## 4. Performance

| ID | Requirement – the system shall… | Source | Verification |
|---|---|---|---|
| NFR-10 | keep all records in memory so that searching, sorting and filtering respond without a noticeable delay for the small data sets a single travel agent holds (tens to a few hundred records). No formal benchmark has been run, and none is claimed. | Derived | Manual |

## 5. Maintainability and testability

| ID | Requirement – the system shall… | Source | Verification |
|---|---|---|---|
| NFR-11 | be organised in separate modules: `main.py` (start-up), `gui/` (one module per tab plus the main window, styles, constants and autocomplete widget) and `record/record.py` (record storage and rules). | Core scope | Inspection |
| NFR-12 | have unit tests under `src/tests/`. The booking-journey rule is tested against the real code; the remaining test files check generic behaviour (search, sort, pagination, persistence, error handling) with stand-in classes and still need to be pointed at `RecordManager`. | Group design | Automated (`test_flight_booking_rule.py`); other files partial |
| NFR-13 | document modules, classes and methods with docstrings and pass the project's Pylint settings, with each suppression explained by a comment. | Group design | Inspection |

## 6. Security and privacy

| ID | Requirement – the system shall… | Source | Verification |
|---|---|---|---|
| NFR-14 | keep all personal data (names, emails, phone numbers, passport numbers) on the user's computer, and keep caches and local settings out of version control. | Derived | Inspection |
