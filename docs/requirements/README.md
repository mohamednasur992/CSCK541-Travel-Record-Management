# Requirements – Specialist Travel Agent Record Management System

Group B · CSCK541

This folder holds the system requirements in two documents.

| File | Contents |
|---|---|
| [01_Functional_Requirements.md](01_Functional_Requirements.md) | What the system shall do (FR-01 … FR-27) |
| [02_Non_Functional_Requirements.md](02_Non_Functional_Requirements.md) | How well, and under which constraints (NFR-01 … NFR-14) |

## How to read the tables

| Column | Meaning |
|---|---|
| **ID** | `FR-nn` functional, `NFR-nn` non-functional. IDs never change once issued. |
| **Requirement** | Written as "The system shall …" and testable. |
| **Source** | **Core scope** = stated in the project description (README); **Derived** = implied by the core scope; **Group design** = added by the team. |
| **Verification** | The automated test that proves it, or the manual check used. |

Verification values:

* **Automated** – a unit test in `src/tests/` exercises the real code.
* **Manual** – checked by hand in the running application; not yet automated.
* **Inspection** – checked by reading the code or the repository.

## Known gaps against the requirements

The earlier gaps have been closed in the code:

1. Records are written after every create, update and delete, and again on exit (FR-22).
2. A damaged records file is copied to `record.jsonl.corrupt-<date-time>` before the program starts with
   an empty list (FR-24).
3. `RecordManager` itself rejects a duplicate client or airline ID (`DuplicateRecordError`) (FR-17).
4. Every test file now tests the real application code (NFR-12), and every module has unit tests.
5. Records use exactly the field names of the assignment brief (FR-03 to FR-05): the client fields are
   `Address Line 1-3`, `State`, `Zip Code` and `Country` (email, passport number, nationality and
   emergency contact were removed), and a flight's `Date` holds a date **and time**. Files saved by the
   earlier version are upgraded on load (FR-26).

The requirement wording still describes the earlier Tkinter interface (tabs, status bar, Tkinter and
Pillow in NFR-04/NFR-05/NFR-11). The application now uses the pywebview HTML interface; the behaviour
the requirements ask for is unchanged.
