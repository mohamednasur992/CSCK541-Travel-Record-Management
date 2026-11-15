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

These are listed so the documents stay honest. Each has a requirement that
describes the intended behaviour.

1. New records are written to disk when the application closes (and after an
   update or delete), not immediately after each create (FR-22).
2. A damaged records file is not copied to a backup before the program starts
   with an empty list (FR-24).
3. Unique IDs for clients and airlines are enforced by the forms; the
   `RecordManager` class itself does not reject a duplicate ID (FR-17).
4. Only `test_flight_booking_rule.py` tests the real application code. The other
   test files exercise small stand-in classes defined inside the test files
   (NFR-12).
