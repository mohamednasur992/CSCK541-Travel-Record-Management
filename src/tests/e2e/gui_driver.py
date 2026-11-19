"""Drives the real application window for the end-to-end tests (run as a separate process).

    python gui_driver.py <records file> <settings file> <result json>

It opens the real page in a pywebview window, talks to the real ``WebApi``
and ``RecordManager`` on temporary files, and clicks and types in the page
exactly as a user would. Every check is recorded as ``{"ok": bool, "detail": str}``
in the result file; ``test_gui_end_to_end.py`` turns each one into a test.

pywebview can only be started once per process, which is why this is a
script and not part of the unittest process.
"""

import json
import sys
import time
import traceback
from pathlib import Path

SRC = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SRC))

import webview  # noqa: E402  pylint: disable=wrong-import-position
from gui import launcher  # noqa: E402  pylint: disable=wrong-import-position
from gui.bridge import WebApi  # noqa: E402  pylint: disable=wrong-import-position
from record.record import RecordManager  # noqa: E402  pylint: disable=wrong-import-position

HELPERS = """
window.__errors = [];
window.addEventListener('error', e => window.__errors.push(String(e.message)));
window.addEventListener('unhandledrejection', e => window.__errors.push('rejection: ' + String(e.reason)));
window.__t = {
  fill(id, value) {
    const el = document.getElementById(id);
    if (!el) throw new Error('no element #' + id);
    el.focus(); el.value = value;
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    return true;
  },
  click(sel) {
    const el = document.querySelector(sel);
    if (!el) throw new Error('nothing matches ' + sel);
    el.click(); return true;
  },
  text(sel) { const el = document.querySelector(sel); return el ? el.textContent.trim() : null; },
  value(id) { const el = document.getElementById(id); return el ? el.value : null; },
  count(sel) { return document.querySelectorAll(sel).length; },
  pick(triggerId, label) {
    document.getElementById(triggerId).click();
    const options = Array.from(document.querySelectorAll('#' + triggerId + 'Wrapper .custom-select-option'));
    const option = options.find(o => o.textContent.includes(label));
    if (!option) throw new Error('no option "' + label + '" in ' + triggerId);
    option.click(); return true;
  },
  key(key, init) {
    document.dispatchEvent(new KeyboardEvent('keydown', Object.assign({ key: key, bubbles: true, cancelable: true }, init || {})));
    return true;
  },
  dialogOpen() { return document.getElementById('dialogOverlay').classList.contains('open'); },
  dialogTitle() { return this.text('#dialogTitle'); },
  dialogBody() { return this.text('#dialogBody'); },
  answer(value) { return this.click('#dialogActions button[data-value="' + value + '"]'); },
  errorOf(field) {
    const el = document.getElementById('err-f-' + field);
    return el && el.classList.contains('active') ? el.textContent.trim() : '';
  },
};
true;
"""


class Driver:
    """Small helpers for talking to the page."""

    def __init__(self, window, results):
        self.window = window
        self.results = results

    def js(self, code):
        return self.window.evaluate_js(code)

    def call(self, name, *args):
        """Call a ``window.__t`` helper; raise if the page raised."""
        arguments = ", ".join(json.dumps(a) for a in args)
        answer = self.js(f"(() => {{ try {{ return JSON.stringify({{ok: true, v: window.__t.{name}({arguments})}}); }} "
                         f"catch (e) {{ return JSON.stringify({{ok: false, e: String(e)}}); }} }})()")
        data = json.loads(answer) if answer else {"ok": False, "e": "no answer from the page"}
        if not data["ok"]:
            raise RuntimeError(f"{name}{args}: {data['e']}")
        return data["v"]

    def wait(self, name, *args, expect=True, timeout=8.0):
        """Poll a helper until it returns ``expect`` (or a truthy value if ``expect`` is True)."""
        deadline = time.time() + timeout
        last = None
        while time.time() < deadline:
            try:
                last = self.call(name, *args)
            except RuntimeError as exc:
                last = str(exc)
            if (expect is True and last) or (expect is not True and last == expect):
                return last
            time.sleep(0.1)
        raise AssertionError(f"timed out waiting for {name}{args} == {expect!r}; last value {last!r}")

    def settle(self, seconds=0.35):
        time.sleep(seconds)

    def click(self, selector):
        self.call("click", selector)
        self.settle(0.2)

    def fill(self, field, value):
        self.call("fill", "f-" + field.replace(" ", "_"), value)

    def leave_form(self):
        """Answer 'Discard' if leaving the form asks about unsaved typing."""
        self.settle(0.25)
        if self.call("dialogOpen"):
            self.call("answer", "discard")
            self.settle(0.25)

    def open_tab(self, record_type):
        self.click(f"#tab-{record_type}")
        self.leave_form()
        self.wait("count", f"#view-{record_type}:not(.hidden)", expect=1)

    def new_record(self):
        self.click("#headerNewBtn")
        self.leave_form()

    def save(self):
        self.click("#saveBtn")

    def toast(self):
        return self.js("(() => { const t = document.querySelectorAll('.toast-card .toast-title');"
                       " return t.length ? t[t.length - 1].textContent : ''; })()")

    def wait_toast(self, text):
        deadline = time.time() + 8
        while time.time() < deadline:
            if text.lower() in (self.toast() or "").lower():
                return self.toast()
            time.sleep(0.1)
        raise AssertionError(f"no toast containing {text!r}; last toast {self.toast()!r}")

    def create_client(self, name, address, city, phone):
        self.open_tab("Client")
        self.new_record()
        self.fill("Name", name)
        self.fill("Address Line 1", address)
        self.fill("City", city)
        self.fill("Phone Number", phone)
        self.save()
        self.wait_toast("created")

    def create_airline(self, name):
        self.open_tab("Airline")
        self.new_record()
        self.fill("Company Name", name)
        self.save()
        self.wait_toast("created")

    def fill_flight(self, client, airline, start, end):
        self.call("pick", "f-Client_ID", client)
        self.call("pick", "f-Airline_ID", airline)
        self.click('.preset-pill-btn[data-preset="tomorrow"]')
        self.fill("Start City", start)
        self.fill("End City", end)


def run_checks(driver, record):
    """Every end-to-end check, in the order a user would meet them."""
    d = driver

    @record("page_ready")
    def _():
        deadline = time.time() + 15
        while time.time() < deadline and d.js("document.body.getAttribute('data-ready')") != "true":
            time.sleep(0.2)
        assert d.js("document.body.getAttribute('data-ready')") == "true"
        d.js(HELPERS)
        return "page loaded and bridge bootstrapped"

    @record("logo_is_shown")
    def _():
        ok = d.js("(() => { const i = document.querySelector('img.brand-logo'); return !!i && i.complete && i.naturalWidth > 0; })()")
        assert ok, "logo image did not load"

    @record("three_tabs_and_new_button")
    def _():
        assert d.call("count", ".nav-tabs .tab-btn") == 3
        assert "New Flight" in d.call("text", "#headerNewText")

    @record("create_client_and_country_suggestion")
    def _():
        d.open_tab("Client")
        d.new_record()
        d.fill("Name", "Ada Lovelace")
        d.fill("Address Line 1", "1 Main St")
        d.fill("City", "London")
        assert d.call("value", "f-Country") == "United Kingdom", d.call("value", "f-Country")
        d.fill("Phone Number", "+44 151 123 4567")
        d.save()
        title = d.wait_toast("created")
        d.wait("count", "#clientCards .entity-card", expect=1)
        return title

    @record("country_suggestion_never_overwrites_typed_value")
    def _():
        d.new_record()
        d.fill("Country", "Atlantis")
        d.fill("City", "Paris")
        assert d.call("value", "f-Country") == "Atlantis"

    @record("required_field_error_is_shown_beside_the_field")
    def _():
        d.new_record()
        d.save()
        message = d.wait("errorOf", "Name")
        assert message.endswith("."), message
        assert "required" in message.lower(), message
        assert d.call("text", "#formBanner")

    @record("invalid_phone_number_error_explains_the_fix")
    def _():
        d.fill("Name", "Bad Phone")
        d.fill("Address Line 1", "1 Road")
        d.fill("City", "Leeds")
        d.fill("Country", "UK")
        d.fill("Phone Number", "abc")
        d.save()
        message = d.wait("errorOf", "Phone_Number")
        assert "7 digits" in message, message
        assert d.call("count", "#clientCards .entity-card") == 1

    @record("invalid_city_is_rejected_beside_the_field")
    def _():
        d.fill("City", "Dubai@#$%&*!?")
        d.fill("Phone Number", "+44 151 123 4567")
        d.save()
        message = d.wait("errorOf", "City")
        assert "letters" in message, message
        assert d.call("count", "#clientCards .entity-card") == 1

    @record("create_airline_and_reject_duplicate_name")
    def _():
        d.create_airline("British Airways (BA)")
        d.wait("count", "#airlineCards .entity-card", expect=1)
        d.new_record()
        d.fill("Company Name", "british airways (ba)")
        d.save()
        message = d.wait("errorOf", "Company_Name")
        assert "already uses" in message, message

    @record("create_flight_with_dropdowns_and_quick_date")
    def _():
        d.open_tab("Flight")
        d.new_record()
        d.fill_flight("Ada Lovelace", "British Airways", "London", "Paris")
        d.save()
        d.wait_toast("created")
        d.wait("count", "#flightTableBody tr[data-key]", expect=1)
        assert "Paris" in d.call("text", "#flightTableBody tr[data-key]")

    @record("same_start_and_end_city_is_flagged_while_typing")
    def _():
        d.new_record()
        d.fill("Start City", "Rome")
        d.fill("End City", "rome")
        d.wait("count", "#routeConflictAlert.active", expect=1)

    @record("journey_rule_blocks_a_second_departure_from_the_same_city")
    def _():
        d.new_record()
        d.fill_flight("Ada Lovelace", "British Airways", "London", "Rome")
        d.save()
        message = d.wait("errorOf", "Start_City")
        assert "London" in message, message
        assert d.call("count", "#flightTableBody tr[data-key]") == 1

    @record("search_filters_and_show_all_restores")
    def _():
        d.create_client("Grace Hopper", "9 Navy Rd", "New York", "+1 212 555 0100")
        d.open_tab("Client")
        d.wait("count", "#clientCards .entity-card", expect=2)
        d.call("fill", "search-Client", "grace")
        d.wait("count", "#clientCards .entity-card", expect=1)
        d.call("fill", "search-Client", "zzz-none")
        d.wait("count", "#clientCards .entity-card", expect=0)
        d.wait("count", '[data-empty="Client"]:not(.hidden)', expect=1)
        d.click('[data-toolbar="Client"] .btn-secondary')
        d.wait("count", "#clientCards .entity-card", expect=2)

    @record("table_columns_sort_both_ways")
    def _():
        d.open_tab("Flight")
        d.click('#flightTable th[data-sort="Start City"]')
        assert d.js("document.querySelector('#flightTable th[data-sort=\"Start City\"]').getAttribute('aria-sort')") == "ascending"
        d.click('#flightTable th[data-sort="Start City"]')
        assert d.js("document.querySelector('#flightTable th[data-sort=\"Start City\"]').getAttribute('aria-sort')") == "descending"

    @record("client_card_lists_its_flights_and_opens_one")
    def _():
        d.open_tab("Client")
        d.wait("count", "#clientCards .card-flights", expect=1)
        d.click("#clientCards .card-flights summary")
        d.wait("count", "#clientCards .card-flights[open] .flight-link", expect=1)
        assert "London → Paris" in d.call("text", "#clientCards .card-flights")
        d.click("#clientCards .flight-link")
        d.wait("count", "#view-Flight:not(.hidden)", expect=1)
        d.wait("text", "#formTitle", expect="Edit Flight · Ada Lovelace")

    @record("edit_a_client_with_the_id_locked")
    def _():
        d.open_tab("Client")
        d.js("Array.from(document.querySelectorAll('#clientCards .entity-card')).find(c => c.textContent.includes('Ada')).click()")
        d.wait("text", "#formTitle", expect="Edit Client #1")
        assert d.js("document.getElementById('f-ID').disabled") is True
        d.fill("Name", "Ada King")
        d.save()
        d.wait_toast("updated")
        deadline = time.time() + 8
        while time.time() < deadline and "Ada King" not in (d.call("text", "#clientCards") or ""):
            time.sleep(0.1)
        assert "Ada King" in d.call("text", "#clientCards")
        assert d.call("count", "#clientCards .entity-card") == 2

    @record("deleting_a_client_with_flights_is_blocked_with_an_explanation")
    def _():
        d.click("#deleteBtn")
        d.wait("dialogOpen")
        assert d.call("dialogTitle") == "Cannot delete"
        body = d.call("dialogBody")
        assert "flight" in body.lower() and "London → Paris" in body, body
        d.call("answer", "ok")
        d.settle()
        assert d.call("count", "#clientCards .entity-card") == 2

    @record("delete_asks_first_cancel_keeps_confirm_removes_undo_restores")
    def _():
        d.open_tab("Flight")
        d.click("#flightTableBody tr[data-key]")
        d.wait("text", "#formTitle", expect=d.call("text", "#formTitle"))
        d.click("#deleteBtn")
        d.wait("dialogOpen")
        assert d.call("dialogTitle") == "Confirm delete"
        d.call("answer", "no")
        d.settle()
        assert d.call("count", "#flightTableBody tr[data-key]") == 1
        d.click("#deleteBtn")
        d.wait("dialogOpen")
        d.call("answer", "yes")
        d.wait("count", "#flightTableBody tr[data-key]", expect=0)
        d.wait("count", ".toast-card .toast-action-btn", expect=1)
        d.click(".toast-card .toast-action-btn")
        d.wait("count", "#flightTableBody tr[data-key]", expect=1)

    @record("keyboard_shortcuts_new_search_help_escape")
    def _():
        d.call("key", "n", {"ctrlKey": True})
        d.wait("text", "#formTitle", expect="Create New Flight")
        d.js("document.activeElement.blur()")
        d.call("key", "/")
        assert d.js("document.activeElement && document.activeElement.id") == "search-Flight"
        d.js("document.activeElement.blur()")
        d.call("key", "F1")
        d.wait("dialogOpen")
        assert "Keyboard shortcuts" in d.call("dialogTitle")
        d.call("key", "Escape")
        d.wait("dialogOpen", expect=False)

    @record("display_settings_change_the_theme_and_are_saved")
    def _():
        d.click("#displayBtn")
        d.js("document.querySelector('input[name=\"pref-theme\"][value=\"dark\"]').click()")
        deadline = time.time() + 6
        while time.time() < deadline and d.js("document.documentElement.getAttribute('data-theme')") != "dark":
            time.sleep(0.1)
        assert d.js("document.documentElement.getAttribute('data-theme')") == "dark"

    @record("no_javascript_errors_during_the_whole_session")
    def _():
        errors = d.js("window.__errors")
        assert errors == [], errors


def main():
    """Open the window, run every check, write the results and close."""
    data_file, settings_file, result_file = sys.argv[1:4]
    manager = RecordManager(filepath=data_file)
    api = WebApi(manager, warnings=manager.load_warnings, settings_path=settings_file)
    window = webview.create_window("e2e", url=launcher.config.INDEX_FILE.as_uri(), js_api=api,
                                   width=1440, height=900)
    api._window = window  # pylint: disable=protected-access
    results = {}

    def record(name):
        def decorate(function):
            started = time.time()
            try:
                detail = function()
                results[name] = {"ok": True, "detail": str(detail or "")}
            except Exception as exc:  # pylint: disable=broad-except
                results[name] = {"ok": False, "detail": f"{type(exc).__name__}: {exc}\n{traceback.format_exc(limit=3)}"}
            results[name]["seconds"] = round(time.time() - started, 2)
            return function
        return decorate

    def work():
        time.sleep(1.0)
        try:
            run_checks(Driver(window, results), record)
        except Exception:  # pylint: disable=broad-except
            results["driver_crashed"] = {"ok": False, "detail": traceback.format_exc()}
        finally:
            Path(result_file).write_text(json.dumps(results, indent=2), encoding="utf-8")
            api._close_approved = True  # pylint: disable=protected-access
            window.destroy()

    webview.start(work)


if __name__ == "__main__":
    main()
