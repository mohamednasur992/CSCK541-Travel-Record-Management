"""Tests for the non-functional requirements that can be checked automatically.

NFR-03 error wording, NFR-05 dependencies, NFR-06 no network or database,
NFR-07/08/09 reliability, NFR-10 responsiveness, NFR-11 layering,
NFR-12 test coverage of every module, NFR-13 documentation and
NFR-14 privacy.
"""

import ast
import re
import shutil
import subprocess
import sys
import time
import unittest
from pathlib import Path

import config
from record.record import RecordManager
from tests.helpers import AIRLINE_FORM, CLIENT_FORM, FLIGHT_FORM, StoreTestCase, TempStore

SRC = Path(config.SRC_DIR)
ROOT = Path(config.PROJECT_ROOT)
TESTS = SRC / "tests"
STATIC = Path(config.STATIC_DIR)
LOCAL_MODULES = {"config", "app_logging", "gui", "record", "main", "tests"}
APPLICATION_FILES = sorted(p for p in SRC.rglob("*.py") if "tests" not in p.parts)


def imported_modules(path):
    """Top-level module names imported by a Python file."""
    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names


class TestDependenciesAndConstraints(unittest.TestCase):
    """NFR-05, NFR-06."""

    def test_nfr05_requirements_file_lists_only_pywebview(self):
        lines = [line.strip() for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
                 if line.strip() and not line.startswith("#")]
        names = {re.split(r"[<>=!~\[;\s]", line)[0].lower() for line in lines}
        self.assertEqual(names, {"pywebview"})

    def test_nfr05_the_application_imports_only_the_standard_library_pywebview_and_itself(self):
        allowed = set(sys.stdlib_module_names) | LOCAL_MODULES | {"webview"}
        for path in APPLICATION_FILES:
            with self.subTest(module=path.relative_to(SRC).as_posix()):
                self.assertEqual(imported_modules(path) - allowed, set())

    def test_nfr06_no_database_web_server_or_network_library_is_imported(self):
        forbidden = {"sqlite3", "dbm", "socket", "ssl", "http", "urllib", "ftplib", "smtplib", "poplib", "imaplib",
                     "telnetlib", "xmlrpc", "socketserver", "wsgiref", "requests", "flask", "django", "fastapi",
                     "aiohttp", "sqlalchemy", "psycopg2", "pymongo", "redis", "boto3", "docker"}
        for path in APPLICATION_FILES + sorted(TESTS.rglob("*.py")):
            with self.subTest(module=path.relative_to(SRC).as_posix()):
                self.assertEqual(imported_modules(path) & forbidden, set())

    def test_nfr06_the_page_makes_no_network_requests_and_loads_nothing_from_the_internet(self):
        page_files = [p for p in STATIC.rglob("*") if p.suffix in {".html", ".js", ".css"}]
        self.assertTrue(page_files)
        for path in page_files:
            text = path.read_text(encoding="utf-8")
            with self.subTest(file=path.name):
                for call in ("fetch(", "XMLHttpRequest", "WebSocket", "EventSource", "sendBeacon", "importScripts"):
                    self.assertNotIn(call, text)
                external = [u for u in re.findall(r"https?://[^\s\"')]+", text)
                            if "w3.org" not in u]                   # SVG namespaces are not requests
                self.assertEqual(external, [])

    def test_nfr06_fonts_are_bundled_with_the_application(self):
        css = (STATIC / "css" / "app.css").read_text(encoding="utf-8")
        for name in re.findall(r"url\(['\"]?([^)'\"]+)", css):
            if not name.startswith("data:"):
                target = (STATIC / "css" / name).resolve()
                self.assertTrue(target.exists(), name)


class TestReliability(StoreTestCase):
    """NFR-07, NFR-08, NFR-09."""

    def test_nfr07_a_rejected_action_leaves_memory_and_file_unchanged(self):
        self.seed()
        records, content = [dict(r) for r in self.rm.records], self.store.data_file.read_bytes()
        rejected = [self.api.create("Client", {**CLIENT_FORM, "Name": ""}),
                    self.api.create("Airline", AIRLINE_FORM),
                    self.api.create("Flight", FLIGHT_FORM),
                    self.api.delete("Client", 1), self.api.delete("Airline", 1),
                    self.api.update("Flight", ["x"], FLIGHT_FORM)]
        self.assertFalse(any(r["ok"] for r in rejected))
        self.assertEqual(self.rm.records, records)
        self.assertEqual(self.store.data_file.read_bytes(), content)

    def test_nfr08_the_interface_keeps_running_with_a_missing_file(self):
        manager = RecordManager(filepath=self.store.folder / "gone" / "record.jsonl")
        api, _ = self.store.api(manager)
        self.assertTrue(api.bootstrap()["ok"])
        self.assertTrue(api.create("Airline", AIRLINE_FORM)["ok"])

    def test_nfr08_the_interface_keeps_running_with_an_unreadable_file(self):
        self.store.data_file.write_bytes(b"\xff\xfe\x00garbage")
        with self.assertLogs("record.record", level="ERROR"):
            manager = self.store.manager()
        api, _ = self.store.api(manager)
        self.assertTrue(api.bootstrap()["ok"])
        self.assertTrue(api.create("Airline", AIRLINE_FORM)["ok"])

    def test_nfr09_the_file_is_rewritten_after_every_update_and_delete(self):
        self.seed()
        self.create("Airline", {"ID": "2", "Company Name": "Air France (AF)"})
        before = self.store.data_file.read_bytes()
        self.api.update("Airline", 2, {"ID": "2", "Company Name": "Air Nouveau"})
        after_update = self.store.data_file.read_bytes()
        self.assertNotEqual(after_update, before)
        self.api.delete("Airline", 2)
        self.assertNotEqual(self.store.data_file.read_bytes(), after_update)
        self.assertEqual(len(self.store.manager().records), 3)

    def test_nfr09_a_save_never_leaves_temporary_files(self):
        self.seed()
        self.api.save_all()
        self.assertEqual([p.name for p in self.store.folder.iterdir() if p.name.endswith(".tmp")], [])


class TestResponsiveness(StoreTestCase):
    """NFR-10: searching and loading stay quick for a few hundred records."""

    RECORDS = 500
    LIMIT_SECONDS = 1.0           # generous: typical machines need a few milliseconds

    def fill(self):
        for number in range(1, 101):
            self.rm.add_client(number, f"Client {number}", f"{number} Road", "", "", "Leeds", "", "", "UK",
                               "+44 113 000 0000")
        for number in range(1, 51):
            self.rm.add_airline(number, f"Air {number}")
        for number in range(self.RECORDS - 150):
            day = 1 + number % 28
            self.rm.add_flight(1 + number % 100, 1 + number % 50, f"2027-{1 + number % 12:02d}-{day:02d} 0{number % 10}:00",
                               f"City {number}", f"City {number + 1}")
        self.rm.save_to_file()

    def test_nfr10_search_over_500_records_is_quick(self):
        self.fill()
        for args in (("Flight", "City 17"), ("Client", "Client 5"), ("Flight", "air 7", "All fields"),
                     ("Client", "leeds", "City")):
            started = time.perf_counter()
            result = self.api.search(*args)
            elapsed = time.perf_counter() - started
            self.assertTrue(result["ok"])
            self.assertLess(elapsed, self.LIMIT_SECONDS, args)

    def test_nfr10_loading_and_the_first_page_data_for_500_records_is_quick(self):
        self.fill()
        started = time.perf_counter()
        manager = self.store.manager()
        api, _ = self.store.api(manager)
        boot = api.bootstrap()
        elapsed = time.perf_counter() - started
        self.assertEqual(len(manager.records), self.RECORDS)
        self.assertTrue(boot["ok"])
        self.assertLess(elapsed, 2 * self.LIMIT_SECONDS)


class TestStructureAndDocumentation(unittest.TestCase):
    """NFR-11, NFR-12, NFR-13."""

    def test_nfr11_the_expected_modules_exist(self):
        for name in ("main.py", "config.py", "app_logging.py", "gui/bridge.py", "gui/launcher.py",
                     "gui/form_schema.py", "gui/preferences.py", "gui/reference_data.py",
                     "gui/static/index.html", "gui/static/js/app.js", "gui/static/css/app.css",
                     "record/record.py", "record/schema.py", "record/errors.py", "record/flight_rules.py"):
            self.assertTrue((SRC / name).is_file(), name)

    def test_nfr11_the_record_layer_does_not_depend_on_the_interface(self):
        for path in (SRC / "record").glob("*.py"):
            with self.subTest(module=path.name):
                self.assertEqual(imported_modules(path) & {"gui", "webview", "main"}, set())

    def test_nfr11_only_the_launcher_and_main_know_about_the_window_library(self):
        for path in APPLICATION_FILES:
            if "webview" in imported_modules(path):
                self.assertIn(path.name, {"launcher.py"}, path.name)

    def test_nfr12_every_application_module_has_a_test(self):
        sources = "\n".join(p.read_text(encoding="utf-8") for p in TESTS.rglob("test_*.py"))
        for module in ("main", "config", "app_logging", "gui.bridge", "gui.launcher", "gui.form_schema",
                       "gui.preferences", "gui.reference_data", "record.record", "record.schema",
                       "record.errors", "record.flight_rules"):
            with self.subTest(module=module):
                short = module.split(".")[-1]
                pattern = rf"(import {re.escape(module)}\b|from {re.escape(module)} import|from {re.escape(module.split('.')[0])} import .*\b{short}\b|\b{short}\.)"
                self.assertRegex(sources, pattern)

    def test_nfr12_the_tests_are_sorted_into_one_folder_per_test_type(self):
        for folder in ("unit", "integration", "negative", "nfr", "e2e"):
            self.assertTrue((TESTS / folder / "__init__.py").is_file(), folder)
        for stray in TESTS.glob("test_*.py"):
            self.fail(f"{stray.name} should be inside a test-type folder")

    def test_nfr12_tests_never_use_the_real_records_file(self):
        for path in TESTS.rglob("test_*.py"):
            if path.name == "test_nfr_requirements.py":
                continue
            text = path.read_text(encoding="utf-8")
            with self.subTest(file=path.name):
                for line in text.splitlines():
                    if "DATA_FILE" in line:
                        self.assertRegex(line, r"(assert|#|self\.assert)", line)    # only compared, never opened

    def test_nfr13_every_module_class_and_public_function_has_a_docstring(self):
        missing = []
        for path in APPLICATION_FILES:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            name = path.relative_to(SRC).as_posix()
            if path.stat().st_size and not ast.get_docstring(tree):
                missing.append(f"{name}: module")
            # Module-level functions and classes, and the methods of those classes
            # (small nested helper functions are not part of the public interface).
            nodes = list(tree.body)
            nodes += [n for c in tree.body if isinstance(c, ast.ClassDef) for n in c.body]
            for node in nodes:
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    public = not node.name.startswith("_")
                    if public and not ast.get_docstring(node):
                        missing.append(f"{name}: {node.name}")
        self.assertEqual(missing, [])


class TestPrivacyAndRepository(unittest.TestCase):
    """NFR-14: personal data and local files stay out of version control."""

    def ignored(self, name):
        git = shutil.which("git")
        if not git or not (ROOT / ".git").exists():
            self.skipTest("not a git checkout")
        result = subprocess.run([git, "check-ignore", "-q", name], cwd=ROOT, check=False)
        return result.returncode == 0

    def test_nfr14_logs_settings_backups_and_caches_are_ignored(self):
        for name in ("logs/travel_records.log", "src/record/settings.json",
                     "src/record/record.jsonl.corrupt-20261110-120000", "src/record/.record.jsonl-abc.tmp",
                     "src/__pycache__/main.cpython-313.pyc", ".coverage"):
            with self.subTest(path=name):
                self.assertTrue(self.ignored(name), name)

    def test_nfr14_no_log_settings_or_backup_file_is_tracked(self):
        git = shutil.which("git")
        if not git or not (ROOT / ".git").exists():
            self.skipTest("not a git checkout")
        tracked = subprocess.run([git, "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
        for bad in ("logs/", "settings.json", ".corrupt-", ".tmp", "__pycache__", ".pyc"):
            self.assertNotIn(bad, tracked, bad)

    def test_nfr14_the_default_log_and_data_locations_are_on_the_local_disk(self):
        for path in (config.DATA_FILE, config.LOG_FILE):
            self.assertTrue(Path(path).is_absolute())
            self.assertTrue(str(path).startswith(str(ROOT)))

    def test_nfr14_the_page_logs_do_not_contain_record_contents(self):
        store = TempStore()
        self.addCleanup(store.cleanup)
        api, _ = store.api()
        with self.assertLogs(level="DEBUG") as logs:
            api.create("Client", CLIENT_FORM)
            api.create("Client", {**CLIENT_FORM, "Phone Number": "bad"})
        joined = "\n".join(logs.output)
        for personal in ("Ada Lovelace", "1 Main St", "+44 151 123 4567", "SW1A 1AA"):
            self.assertNotIn(personal, joined)


class TestErrorWording(StoreTestCase):
    """NFR-03: errors say which field is wrong and how to fix it."""

    def test_nfr03_each_error_is_a_sentence_that_tells_the_user_what_to_do(self):
        result = self.api.create("Client", {**CLIENT_FORM, "Name": "", "Phone Number": "abc", "ID": "0",
                                            "Zip Code": "9" * 30})
        self.assertEqual(set(result["errors"]), {"Name", "Phone Number", "ID", "Zip Code"})
        hints = ("required", "use at least", "whole number", "at most")
        for field, message in result["errors"].items():
            self.assertTrue(any(h in message.lower() for h in hints), (field, message))
            self.assertTrue(message[0].isupper() and message.endswith("."), message)

    def test_nfr03_a_date_error_shows_an_example(self):
        self.create("Client", CLIENT_FORM)
        self.create("Airline", AIRLINE_FORM)
        result = self.api.create("Flight", {**FLIGHT_FORM, "Date": "1 Dec"})
        self.assertIn("2026-12-01 09:30", result["errors"]["Date"])

    def test_nfr03_blocked_actions_explain_why(self):
        self.seed()
        self.assertIn("flight", self.api.delete("Client", 1)["error"].lower())
        reason = self.api.create("Flight", {**FLIGHT_FORM, "Start City": "Rome", "End City": "Oslo"})
        self.assertIn("Paris", reason["errors"]["Start City"])


if __name__ == "__main__":
    unittest.main()
