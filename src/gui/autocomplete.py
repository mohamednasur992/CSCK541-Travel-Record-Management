"""Reusable autocomplete Combobox widget for searchable selection fields."""

import tkinter as tk
from tkinter import ttk


# ttk.Combobox inherits through several Tkinter base classes by design.
# pylint: disable=too-many-ancestors
class AutocompleteCombobox(ttk.Combobox):
    """Combobox that dynamically filters an alphabetically sorted item list."""

    def __init__(self, master, list_of_items, **kwargs):
        """Initialise the Combobox with a searchable list of values."""
        super().__init__(master, **kwargs)

        # Keep one sorted source list so filtering does not modify
        # the original set of available options.
        self.all_items = sorted(list_of_items)
        self["values"] = self.all_items

        # Refresh suggestions whenever the user enters searchable text.
        self.bind("<KeyRelease>", self.handle_key_release)

    def handle_key_release(self, event):
        """Filter available suggestions using the user's current input."""

        # Navigation keys should control the widget rather than trigger filtering.
        if event.keysym in (
            "BackSpace",
            "Left",
            "Right",
            "Up",
            "Down",
            "Return",
        ):
            return

        typed = str(self.get()).lower()

        if not typed:
            # Restore the complete list when the search field is empty.
            self["values"] = self.all_items
        else:
            # Match anywhere in each item and preserve alphabetical ordering.
            self["values"] = [
                item
                for item in self.all_items
                if typed in str(item).lower()
            ]

        try:
            # Keep the suggestion list visible after filtering so the user
            # can immediately select one of the matching values.
            self.tk.call("ttk::combobox::PopdownWindow", self)
        except tk.TclError:
            # The dropdown may be unavailable while the widget is closing.
            pass
