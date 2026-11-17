# Test Traceability

Which tests verify which requirement. Tests are sorted into one folder per
test type under `src/tests/`.

| Folder | Test type | What it does |
|---|---|---|
| `unit/` | Unit | One class or function at a time, with temporary files only |
| `integration/` | Integration | Bridge, rules, record manager, files, preferences and start-up working together |
| `negative/` | Negative and error injection | Forces disk, file, log and input failures and checks the program copes |
| `nfr/` | Non-functional | Dependencies, network and database use, responsiveness, layering, documentation, privacy |
| `e2e/` | End-to-end GUI | Opens the real window and clicks and types in the real page |

Run everything from the project root:

```bash
python -m unittest discover -s src/tests -t src
```

Run one type with `-s src/tests/<folder>`, for example `-s src/tests/negative`.
The end-to-end tests open a window and take about 25 seconds; they skip themselves
when `pywebview` is missing, when there is no display, or when `RMS_SKIP_GUI=1` is set.

## Functional requirements

| Requirement | Unit | Integration | Negative | End-to-end |
|---|---|---|---|---|
| FR-01 one list of dictionaries | `test_fr_record_model` (TestRecordTypes), `test_travel_records` | | | |
| FR-02 `Type` field | `test_fr_record_model` (TestRecordTypes) | | `test_error_injection` (extra fields ignored) | |
| FR-03 client fields | `test_fr_record_model` (TestClientRecord), `test_schema_and_config` | | | |
| FR-04 airline fields | `test_fr_record_model` (TestAirlineRecord) | | | |
| FR-05 flight fields | `test_fr_record_model` (TestFlightRecord) | | | |
| FR-06 create | `test_fr_operations` (TestCreate) | `test_workflows` (TestAgentSession) | | `test_fr06_*` |
| FR-07 search | `test_fr_operations` (TestSearch), `test_travel_ui` | | | `test_fr07_search_filters_*` |
| FR-08 display and sort | `test_fr_operations` (TestDisplay), `test_travel_ui` | | | `test_fr08_table_columns_sort_*` |
| FR-09 update, ID locked | `test_fr_operations` (TestUpdate) | `test_workflows` | | `test_fr09_a_client_can_be_edited_*` |
| FR-10 delete | `test_fr_operations` (TestDelete) | `test_workflows` | | `test_fr10_delete_asks_first_*` |
| FR-11 flight identity | `test_fr_operations` (TestFlightIdentity) | | | |
| FR-12 `ID - name` choices | `test_fr_operations` (TestChoicesAndSuggestions) | | | `test_fr06_create_a_flight_*` |
| FR-13 suggestions, free text accepted | `test_fr_operations`, `test_travel_autocomplete` | | | |
| FR-14 country suggestion | `test_fr_operations`, `test_travel_autocomplete` | | | `test_fr14_*` |
| FR-15 feedback for every action | `test_fr_operations` (TestFeedback) | | | `test_fr06_fr14_fr15_*` |
| FR-16 field validation | `test_fr_validation_integrity` (TestFieldValidation), `test_travel_error_handling` | | `test_error_injection` (random invalid forms) | `test_fr16_*`, `test_nfr03_*` |
| FR-17 next ID, duplicate IDs | `test_fr_validation_integrity` (TestUniqueIds), `test_travel_records` | | `test_error_injection` (parallel creates) | |
| FR-18 airline names unique | `test_fr_validation_integrity` (TestAirlineNames) | | | `test_fr06_create_an_airline_*` |
| FR-19 flight needs real client and airline | `test_fr_validation_integrity` (TestFlightReferences) | | | |
| FR-20 referenced records not deletable | `test_fr_validation_integrity` (TestReferencedRecords), `test_travel_records` | `test_workflows` | | `test_fr20_*` |
| FR-21 same-day journey rule | `test_flight_booking_rule` (15 tests), `test_fr_validation_integrity` (TestJourneyRuleThroughTheBridge) | `test_workflows` | | `test_fr21_*` |
| FR-22 JSON Lines file | `test_travel_persistence` | `test_fr_persistence_files` (TestFileFormat) | `test_error_injection` (TestSaveFailures) | `test_fr22_*` |
| FR-23 start-up check | `test_travel_persistence` | `test_fr_persistence_files` (TestStartUp) | | |
| FR-24 damaged file | `test_travel_persistence` | `test_fr_persistence_files` (TestStartUp), `test_workflows` | `test_error_injection` (TestDamagedFiles) | |
| FR-25 save on exit and Ctrl+C | `test_main`, `test_launcher` | `test_fr_persistence_files` (TestSavingOnExit), `test_workflows` | | |
| FR-26 reload and upgrade | `test_travel_persistence` | `test_fr_persistence_files` (TestReloadAndUpgrade) | | |
| FR-28 undo the last delete | `test_fr_operations` (TestDelete) | `test_workflows` | | `test_fr10_delete_asks_first_*` |
| FR-29 display preferences | `test_schema_and_config` (TestPreferences) | `test_workflows` (TestPreferencesAcrossRestarts) | `test_error_injection` | `test_display_settings_*` |
| FR-27 logo | | `test_fr_persistence_files` (TestLogo) | | `test_fr27_logo_is_shown` |

## Non-functional requirements

| Requirement | Verified by | Type |
|---|---|---|
| NFR-01 obvious create, search, update, delete | `test_nfr01_three_tabs_and_a_new_button`, the whole end-to-end session | End-to-end |
| NFR-02 errors prevented, delete confirmed, keyboard use | `test_nfr02_keyboard_shortcuts_work`, `test_fr10_delete_asks_first_*` | End-to-end |
| NFR-03 plain-language errors | `test_nfr_requirements` (TestErrorWording), `test_nfr03_*` | NFR, end-to-end |
| NFR-04 runs locally with `python src/main.py` | `test_main`, `test_launcher`, the end-to-end session | Unit, end-to-end |
| NFR-05 only the listed packages | `test_nfr_requirements` (TestDependenciesAndConstraints) | NFR |
| NFR-06 no database, server or network | `test_nfr_requirements` (TestDependenciesAndConstraints) | NFR |
| NFR-07 invalid input never changes data | `test_nfr_requirements` (TestReliability), `test_error_injection` (random invalid forms, malformed arguments) | NFR, negative |
| NFR-08 keeps running with a bad file | `test_nfr_requirements` (TestReliability), `test_error_injection` (TestDamagedFiles) | NFR, negative |
| NFR-09 file rewritten after each change; failed save loses nothing | `test_nfr_requirements` (TestReliability), `test_error_injection` (TestSaveFailures) | NFR, negative |
| NFR-10 responsive for a few hundred records | `test_nfr_requirements` (TestResponsiveness: 500 records, 1 s limit) | NFR |
| NFR-11 separate modules, record layer independent of the interface | `test_nfr_requirements` (TestStructureAndDocumentation) | NFR |
| NFR-12 unit tests for every module, sorted by type, real files never used | `test_nfr_requirements` (TestStructureAndDocumentation) | NFR |
| NFR-13 docstrings | `test_nfr_requirements` (TestStructureAndDocumentation) | NFR |
| NFR-15 rotating log, no personal details | `test_app_logging`, `test_nfr_requirements` (TestPrivacyAndRepository) | `test_workflows` (TestStartUpToShutdown) | | Unit, integration |
| NFR-16 unexpected errors contained | | | `test_error_injection` (TestInjectedFailuresInsideTheApplication, TestHostileAndMalformedInput) | Negative |
| NFR-14 personal data local, logs and settings not in version control | `test_nfr_requirements` (TestPrivacyAndRepository), `test_workflows` (log holds no personal details) | NFR, integration |

## Notes

* NFR-10 uses a deliberately generous limit (1 second for 500 records). It catches an
  accidental slowdown; it is not a performance benchmark.
* Failures found by the new tests were fixed in the code: IDs written with non-ASCII digits
  were accepted (`gui/bridge.py`), and a record that could not be written as JSON left a
  temporary file behind (`record/record.py`).
