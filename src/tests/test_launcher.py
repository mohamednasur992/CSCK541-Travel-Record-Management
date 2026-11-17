"""The pywebview launcher: window creation and the save-on-close handler."""

import types
import unittest
from unittest import mock

import config
from gui import launcher
from record.errors import RecordStorageError
from tests.helpers import TempStore


class FakeEvent(list):
    """Mimics pywebview's event object: ``event += handler`` registers a handler."""

    def __iadd__(self, handler):
        self.append(handler)
        return self


class FakeWindow:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.events = types.SimpleNamespace(closing=FakeEvent())
        self.scripts = []
        self.destroyed = False

    def evaluate_js(self, script):
        self.scripts.append(script)

    def destroy(self):
        self.destroyed = True


class FakeWebview:
    def __init__(self):
        self.window = None
        self.started = False

    def create_window(self, title, **kwargs):
        self.window = FakeWindow(title=title, **kwargs)
        return self.window

    def start(self):
        self.started = True


class TestLauncher(unittest.TestCase):
    def setUp(self):
        self.store = TempStore()
        self.addCleanup(self.store.cleanup)
        self.rm = self.store.manager()
        # Threads run inline so the close prompts can be checked.
        patcher = mock.patch("gui.launcher.threading.Thread",
                             lambda target, daemon: types.SimpleNamespace(start=target))
        patcher.start()
        self.addCleanup(patcher.stop)

    def open(self, warnings=None):
        webview = FakeWebview()
        code = launcher.run(self.rm, webview=webview, warnings=warnings)
        return code, webview.window, webview

    def test_window_loads_the_local_page(self):
        code, window, webview = self.open(["a warning"])
        self.assertEqual(code, config.EXIT_OK)
        self.assertTrue(webview.started)
        self.assertEqual(window.kwargs["url"], config.INDEX_FILE.as_uri())
        self.assertTrue(window.kwargs["url"].startswith("file://"))
        self.assertTrue(window.kwargs["zoomable"])
        api = window.kwargs["js_api"]
        self.assertIs(api._window, window)  # pylint: disable=protected-access
        self.assertEqual(api.bootstrap()["warnings"], ["a warning"])

    def test_closing_saves_records(self):
        _, window, _ = self.open()
        self.rm.add_airline(1, "A")
        self.assertTrue(window.events.closing[0]())
        self.assertEqual(len(self.store.manager().records), 1)

    def test_unsaved_form_keeps_window_open_and_asks_page(self):
        _, window, _ = self.open()
        api = window.kwargs["js_api"]
        api.set_form_dirty(True)
        self.assertFalse(window.events.closing[0]())
        self.assertIn("unsaved-form", window.scripts[0])
        api.request_close(save=True)
        self.assertTrue(window.destroyed)

    def test_failed_save_keeps_window_open_and_explains(self):
        _, window, _ = self.open()
        with mock.patch.object(self.rm, "save_to_file",
                               side_effect=RecordStorageError("f", OSError("disk full"))), \
                self.assertLogs("gui.launcher", level="ERROR"):
            self.assertFalse(window.events.closing[0]())
        self.assertIn("save-failed", window.scripts[0])
        self.assertIn("disk full", window.scripts[0])
        window.kwargs["js_api"].request_close(save=False)
        self.assertTrue(window.events.closing[0]())                 # user chose to close without saving

    def test_prompt_errors_after_window_closed_are_only_logged(self):
        window = mock.Mock()
        window.evaluate_js.side_effect = RuntimeError("window gone")
        with self.assertLogs("gui.launcher", level="DEBUG") as logs:
            launcher.notify_page(window, "unsaved-form")
        self.assertIn("window gone", logs.output[0])

    def test_webview_available_checks_the_package(self):
        with mock.patch("gui.launcher.importlib.util.find_spec", return_value=None):
            self.assertFalse(launcher.webview_available())


if __name__ == "__main__":
    unittest.main()
