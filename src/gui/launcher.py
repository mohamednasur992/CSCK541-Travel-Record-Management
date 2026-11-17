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
import logging
import threading

import config
from gui.bridge import WebApi

logger = logging.getLogger(__name__)

# pylint: disable=protected-access  # the launcher owns the bridge's window state


def webview_available():
    """True when the optional ``pywebview`` package is installed."""
    return importlib.util.find_spec("webview") is not None


def notify_page(window, kind, message=""):
    """Ask the page (from a background thread) to show a close prompt."""
    payload = json.dumps({"kind": kind, "message": message})

    def call():
        try:
            window.evaluate_js(f"window.rmsCloseBlocked && window.rmsCloseBlocked({payload})")
        except Exception as exc:  # pylint: disable=broad-except
            # Any back-end error here means the window is already closing.
            logger.debug("Could not show the %s prompt: %s", kind, exc)

    threading.Thread(target=call, daemon=True).start()


def on_closing(api, window):
    """Return True to let the window close, False to keep it open."""
    if api._close_approved:
        return True
    if api._form_dirty:
        logger.info("Close postponed: the form has unsaved changes.")
        notify_page(window, "unsaved-form")
        return False
    result = api.save_all()
    if result["ok"]:
        logger.info("Window closing; records saved.")
        return True
    logger.error("Close postponed: %s", result["error"])
    notify_page(window, "save-failed", result["error"])
    return False


def run(record_manager, webview=None, warnings=None):
    """Open the window for ``record_manager`` and block until it is closed."""
    if webview is None:
        import webview  # pylint: disable=import-outside-toplevel,redefined-outer-name
    api = WebApi(record_manager, warnings=warnings)
    window = webview.create_window(
        config.APP_TITLE, url=config.INDEX_FILE.as_uri(), js_api=api,
        width=config.WINDOW_SIZE[0], height=config.WINDOW_SIZE[1], min_size=config.MIN_WINDOW_SIZE,
        background_color=config.WINDOW_BACKGROUND, text_select=True,
        zoomable=True)   # Ctrl + / Ctrl - resize text; pywebview disables this by default
    api._window = window
    window.events.closing += lambda: on_closing(api, window)
    logger.info("Opening the window.")
    webview.start()
    logger.info("Window closed.")
    return config.EXIT_OK
