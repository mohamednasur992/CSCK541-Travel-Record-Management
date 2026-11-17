# Non-Functional Requirements

**Source:** *Core scope* = stated in the project description; *Derived* = implied by it; *Group design* = added by the team.
**Verification:** *Automated* = a test in `src/tests/` runs the real code; *Inspection* = checked by reading the code or repository. Test paths are relative to `src/tests/`.

## 1. Usability

| ID | Requirement – the system shall… | Source | Verification |
|---|---|---|---|
| NFR-01 | make Create, Search, Update and Delete obvious: one tab per record type, with the form beside the table and clearly labelled buttons. | Core scope | Automated – `e2e/test_gui_end_to_end.py` |
| NFR-02 | prevent errors where possible (drop-downs for client and airline, calendar for dates, read-only generated IDs, suggestions for cities) and ask for confirmation before a delete. | Group design | Automated – `e2e/test_gui_end_to_end.py` |
| NFR-03 | state errors in plain language that says which field is wrong and how to fix it. | Group design | Automated – `nfr/test_nfr_requirements.py`; `e2e/test_gui_end_to_end.py` |

## 2. Portability and constraints

| ID | Requirement – the system shall… | Source | Verification |
|---|---|---|---|
| NFR-04 | run locally as a desktop application on Python 3, started with `python src/main.py`, showing the HTML interface in a native window through pywebview. It is developed and tested on Windows; macOS and Linux need pywebview's back-end for their platform. | Core scope | Automated – `unit/test_main.py`; `unit/test_launcher.py`; `e2e/test_gui_end_to_end.py` (Windows) |
| NFR-05 | use only `pywebview` (listed in `requirements.txt`) and the Python standard library. | Core scope | Automated – `nfr/test_nfr_requirements.py` |
| NFR-06 | not use a database server, web server, cloud service or network connection; all data stays in the local JSON Lines file. | Core scope | Automated – `nfr/test_nfr_requirements.py` |

## 3. Reliability

| ID | Requirement – the system shall… | Source | Verification |
|---|---|---|---|
| NFR-07 | never store a record that fails validation, and leave the existing data unchanged when an action is rejected. | Derived | Automated – `nfr/test_nfr_requirements.py`; `negative/test_error_injection.py` |
| NFR-08 | keep the interface running when the records file is missing or unreadable (see FR-23, FR-24). | Derived | Automated – `nfr/test_nfr_requirements.py`; `negative/test_error_injection.py` |
| NFR-09 | write the file after every create, update and delete, and replace it atomically (temporary file, then rename), so a crash or a failed save never loses data or leaves a half-written file. | Group design | Automated – `nfr/test_nfr_requirements.py`; `negative/test_error_injection.py` |
| NFR-16 | contain unexpected errors so the window stays usable: a failed action returns a plain explanation to the page and the details, with a traceback, go to the log. | Group design | Automated – `negative/test_error_injection.py` |

## 4. Performance

| ID | Requirement – the system shall… | Source | Verification |
|---|---|---|---|
| NFR-10 | keep all records in memory so that searching, sorting and filtering respond without a noticeable delay for the small data sets a single travel agent holds (tens to a few hundred records). The test allows 1 second for 500 records; it guards against slowdowns and is not a benchmark. | Derived | Automated – `nfr/test_nfr_requirements.py` |

## 5. Maintainability and testability

| ID | Requirement – the system shall… | Source | Verification |
|---|---|---|---|
| NFR-11 | be organised in separate modules: `main.py` (start-up), `config.py` and `app_logging.py`, `gui/` (bridge, launcher, form schema, preferences, reference data and the static page) and `record/` (record manager, schema, errors and flight rules), with the record layer independent of the interface. | Core scope | Automated – `nfr/test_nfr_requirements.py` |
| NFR-12 | have automated tests under `src/tests/`, sorted into unit, integration, negative, non-functional and end-to-end folders, with tests for every application module that run on temporary files and never touch the real records file. | Group design | Automated – `nfr/test_nfr_requirements.py` |
| NFR-13 | document modules, classes and methods with docstrings and pass the project's Pylint settings, with each suppression explained by a comment. | Group design | Automated – `nfr/test_nfr_requirements.py` (docstrings); Inspection (Pylint) |

## 6. Security and privacy

| ID | Requirement – the system shall… | Source | Verification |
|---|---|---|---|
| NFR-14 | keep all personal data (names, addresses, phone numbers) on the user's computer, and keep caches and local settings out of version control. | Derived | Automated – `nfr/test_nfr_requirements.py` |
| NFR-15 | write a rotating log file (`logs/travel_records.log`) with errors and tracebacks, identifying records by type and ID only, never by name, address or phone number. | Group design | Automated – `unit/test_app_logging.py`; `integration/test_workflows.py`; `nfr/test_nfr_requirements.py` |
