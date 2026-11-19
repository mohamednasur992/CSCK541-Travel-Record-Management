# Requirements – Specialist Travel Agent Record Management System

Group B · CSCK541

This folder holds the system requirements and the tests that verify them.

| File | Contents |
|---|---|
| [01_Functional_Requirements.md](01_Functional_Requirements.md) | What the system shall do (FR-01 … FR-30) |
| [02_Non_Functional_Requirements.md](02_Non_Functional_Requirements.md) | How well, and under which constraints (NFR-01 … NFR-16) |
| [03_Test_Traceability.md](03_Test_Traceability.md) | Which tests verify which requirement |

## How to read the tables

| Column | Meaning |
|---|---|
| **ID** | `FR-nn` functional, `NFR-nn` non-functional. IDs never change once issued. |
| **Requirement** | Written as "The system shall …" and testable. |
| **Source** | **Core scope** = stated in the project description (README); **Derived** = implied by the core scope; **Group design** = added by the team. |
| **Verification** | The automated test that proves it, or the manual check used. |

Verification values:

* **Automated** – a test under `src/tests/` runs the real code (unit, integration, negative,
  non-functional or end-to-end GUI). Every requirement has at least one.
* **Inspection** – checked by reading the code or the repository (only the Pylint part of NFR-13).

## Status

All 30 functional and 16 non-functional requirements are implemented and verified by the automated
tests (see `03_Test_Traceability.md`). Run them with:

```bash
python -m unittest discover -s src/tests -t src
```

Points to know:

1. The end-to-end GUI tests need pywebview and a display; they skip themselves otherwise
   (`RMS_SKIP_GUI=1` also skips them).
2. NFR-10 uses a generous limit (1 second for 500 records) to catch slowdowns; it is not a benchmark.
3. Records use exactly the field names of the assignment brief (FR-03 to FR-05). Files saved by the
   earlier version of the program are upgraded when they are loaded (FR-26).
