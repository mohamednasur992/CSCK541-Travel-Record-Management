# Specialist Travel Agent Record Management System

The Specialist Travel Agent Record Management System is a GUI-based Python application developed by Group B as part of the CSCK541 module coursework.

The application enables a specialist travel agent to create, view and manage three primary record types:

* Client Records
* Flight Records
* Airline Company Records

The system is a local desktop application written in Python. Its interface is an HTML page shown in a
native window by [pywebview](https://pywebview.flowrl.com/); the page talks to Python directly, so no web
server, database or network connection is used.

---

## Features

* **Graphical user interface:** one window with Flights, Clients and Airlines views, a searchable table or card list, and a form to create, update and delete records.
* **Client, airline and flight records:** held in one in-memory list of dictionaries, using the field names of the assignment brief:

  | Record | Fields |
  |---|---|
  | Client | `ID` (int), `Type`, `Name`, `Address Line 1`, `Address Line 2`, `Address Line 3`, `City`, `State`, `Zip Code`, `Country`, `Phone Number` |
  | Airline | `ID` (int), `Type`, `Company Name` |
  | Flight | `Type`, `Client_ID` (int), `Airline_ID` (int), `Date` (date and time, `YYYY-MM-DD HH:MM`), `Start City`, `End City` |
* **Data integrity:** unique IDs, flights only for existing clients and airlines, no deleting a client or airline that flights still use, and a same-day journey rule for each client's flights.
* **Record storage:** JSON Lines (`src/record/record.jsonl`), checked at start-up and written after every change and again on exit.
* **Error handling:** invalid input is explained beside each field; a damaged data file is backed up before the program continues; a failed save is reported and never leaves a half-written file; unexpected errors are logged and shown as a message instead of stopping the program.
* **Logging:** a rotating log file at `logs/travel_records.log` (no personal data is logged).
* **Display settings:** light, dark and high-contrast themes, reduced effects and density, saved in `src/record/settings.json`.

---

## Project Structure

```text
CSCK541-Travel-Record-Management/
    src/
        main.py                  # Entry point: logging, start-up check, window, final save
        config.py                # All settings: paths, window size, logging options, exit codes
        app_logging.py           # Log file and console set-up
        record/
            record.py            # RecordManager: records in memory, JSON Lines load/save
            schema.py            # Record types, field keys and date format
            errors.py            # Exceptions raised by the record layer
            flight_rules.py      # Same-day journey rule for flights
            record.jsonl         # Record storage
        gui/
            launcher.py          # Opens the pywebview window; saves on close
            bridge.py            # WebApi: the methods the page calls (validation, CRUD, search)
            form_schema.py       # How each record type appears in forms and searches
            preferences.py       # Display preferences (settings.json)
            reference_data.py    # Airline, city and country suggestions
            static/              # index.html, css/, js/, fonts/, assets/Logo.png
        tests/                   # Unit tests for every module (see below)
    docs/requirements/           # Functional and non-functional requirements
    logs/                        # Created when the program runs (not in Git)
    requirements.txt
    README.md
```

Each layer only calls the layers below it: `gui` uses `record`; `record` never imports `gui`.

---

## Requirements

* **Python:** 3.8 or higher
* **Third-party package:** `pywebview` (shows the HTML interface in a desktop window). On Windows it uses
  Microsoft Edge WebView2, which is part of Windows 10 and 11.

Install it with:

```bash
pip install -r requirements.txt
```

---

## System Setup

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/mohamednasur992/CSCK541-Travel-Record-Management.git
   cd CSCK541-Travel-Record-Management
   ```

2. **Create a Virtual Environment:**

   * **Windows:**
     ```bash
     python -m venv .venv
     .venv\Scripts\activate
     ```
   * **macOS/Linux:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. **Install the dependency:** `pip install -r requirements.txt`

4. **Configure PyCharm (optional):** right-click the `src` folder → *Mark Directory as* → *Sources Root*.

---

## Running the Application

```bash
python src/main.py
```

On start-up the program loads `src/record/record.jsonl` (or starts empty if it does not exist) and opens the
window. Records are saved after every change and again when the window closes. If the file cannot be
read, a copy is kept as `record.jsonl.corrupt-<date-time>` and the program starts with no records.
A file saved by the earlier version of the program (lower-case keys such as `company_name`) is upgraded to
the field names above when it is loaded.

Exit codes: `0` normal, `1` an error occurred (details in the log), `2` pywebview is not installed.

## Logging

Messages go to the console and to `logs/travel_records.log` (rotated at about 1 MB, three old files kept).
Errors include a full traceback, and errors in the page's JavaScript are written there too. Records are
identified by type and ID only; names, addresses and phone numbers are never logged. The log
location and options are set in `src/config.py`.

## Running the Tests

From the project root:

```bash
python -m unittest discover -s src/tests -t src
```

The tests use temporary files only and never change `record.jsonl`. They do not need a display or pywebview.

| Test file | What it checks |
|---|---|
| `test_travel_records.py` | `RecordManager` create, search, update, delete; duplicate IDs; delete protection |
| `test_travel_persistence.py` | JSON Lines save/load, start-up check, upgrade of earlier-format files, damaged-file backup, atomic save failures |
| `test_flight_booking_rule.py` | The same-day journey rule for creating, updating and deleting flights |
| `test_travel_error_handling.py` | Field validation messages, contained unexpected errors, save failures, logging |
| `test_travel_e2e_integration.py` | A full workflow through the page's API, reloaded from disk |
| `test_travel_ui.py` | Data the page displays: forms, rows, choices, summary, search, preferences |
| `test_travel_autocomplete.py` | Airline, city and country suggestions |
| `test_schema_and_config.py` | Brief field names, date/time format, exceptions, settings constants, form layout, display preferences |
| `test_launcher.py` | Window creation and save-on-close behaviour |
| `test_main.py` | Start-up, missing pywebview, Ctrl+C, unexpected errors and the final save |
| `test_app_logging.py` | Log file rotation, console output and fallback when the log folder is read-only |

---

## Authors and Acknowledgments

   Developed by Group B
   
   * Mohamed Nasur, 
   * Moegamat Sheraad Jacobs, 
   * Syed Raza, and 
   * Mzanempi Abednego Maduna
   
   as part of the CSCK541 Module Coursework.