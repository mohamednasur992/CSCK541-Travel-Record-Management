"""Open the HTML interface in a desktop window with pywebview.

The page is loaded from a ``file://`` URL, so no web server runs and nothing
listens on the network.

Closing (``on_closing``): every record is saved before the window may
close. If the form has unsaved typing, or the save fails, closing is
cancelled and the page asks the user what to do. The page then calls
``WebApi.request_close``. Native dialogs are avoided inside the closing
handler because they can deadlock some webview back-ends.
"""

import importlib.util
import json
import threading
from pathlib import Path

# pylint: disable=import-error, protected-access
from gui.bridge import WebApi

APP_TITLE = "Specialist Travel Agent Record Management System — Group B"
STATIC_DIR = Path(__file__).resolve().parent / "static"
INDEX_FILE = STATIC_DIR / "index.html"
WINDOW_SIZE = (1440, 900)
MIN_SIZE = (400, 560)    # narrow windows switch to the compact layout


def webview_available():
    """True when the optional ``pywebview`` package is installed."""
    return importlib.util.find_spec("webview") is not None


def notify_page(window, kind, message=""):
    """Ask the page (from a background thread) to show a close prompt."""
    payload = json.dumps({"kind": kind, "message": message})

    def call():
        try:
            window.evaluate_js(f"window.rmsCloseBlocked && window.rmsCloseBlocked({payload})")
        except Exception:  # pylint: disable=broad-except
            pass  # the window is already gone

    threading.Thread(target=call, daemon=True).start()


def on_closing(api, window):
    """Return True to let the window close, False to keep it open."""
    if api._close_approved:
        return True
    if api._form_dirty:
        notify_page(window, "unsaved-form")
        return False
    result = api.save_all()
    if result["ok"]:
        return True
    notify_page(window, "save-failed", result["error"])
    return False


def run(record_manager, webview=None):
    """Open the window for ``record_manager`` and block until it is closed."""
    if webview is None:
        import webview  # pylint: disable=import-outside-toplevel,redefined-outer-name
    api = WebApi(record_manager)
    window = webview.create_window(
        APP_TITLE, url=INDEX_FILE.as_uri(), js_api=api,
        width=WINDOW_SIZE[0], height=WINDOW_SIZE[1], min_size=MIN_SIZE,
        background_color="#F8FAFC", text_select=True,
        zoomable=True)   # Ctrl + / Ctrl - resize text; pywebview disables this by default
    api._window = window
    window.events.closing += lambda: on_closing(api, window)
    webview.start()
    return 0
