import tkinter as tk
from tkinter import ttk
import unittest


class AutocompleteEntry(ttk.Entry):
    def __init__(self, parent, complete_list, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.complete_list = complete_list
        self.var = self["textvariable"]
        if not self.var:
            self.var = tk.StringVar()
            self["textvariable"] = self.var

        self.var.trace_add("write", self.on_text_change)

        self.listbox = None
        self.bind("<FocusOut>", self.hide_listbox)
        self.bind("<Down>", self.focus_listbox)

    def on_text_change(self, *args):
        pattern = self.var.get().lower()
        if not pattern:
            self.hide_listbox()
            return

        # Filter matching locations (e.g., city name or airport code)
        matches = [item for item in self.complete_list if pattern in item.lower()]

        if matches:
            self.show_listbox(matches)
        else:
            self.hide_listbox()

    def show_listbox(self, matches):
        if not self.listbox:
            self.listbox = tk.Listbox(self.winfo_toplevel(), height=min(len(matches), 4))
            self.listbox.bind("<<ListboxSelect>>", self.on_select)

        # Position listbox directly underneath the entry widget
        x = self.winfo_rootx() - self.winfo_toplevel().winfo_rootx()
        y = self.winfo_rooty() - self.winfo_toplevel().winfo_rooty() + self.winfo_height()

        self.listbox.place(x=x, y=y, width=self.winfo_width())

        self.listbox.delete(0, tk.END)
        for item in matches:
            self.listbox.insert(tk.END, item)
        self.listbox.lift()

    def hide_listbox(self, event=None):
        # Small delay to allow click events on the listbox to register
        if self.listbox:
            self.after(200, self._destroy_listbox)

    def _destroy_listbox(self):
        # Check if focus moved to the listbox itself
        if self.listbox:
            try:
                if self.winfo_toplevel().focus_get() == self.listbox:
                    return
            except tk.TclError:
                pass
            self.listbox.place_forget()
            self.listbox.destroy()
            self.listbox = None

    def on_select(self, event):
        if self.listbox and self.listbox.curselection():
            index = self.listbox.curselection()[0]
            value = self.listbox.get(index)
            self.var.set(value)
            self.icursor(tk.END)
            self.hide_listbox()

    def focus_listbox(self, event):
        if self.listbox and self.listbox.size() > 0:
            self.listbox.focus_set()
            self.listbox.selection_set(0)


class TravelAutocompleteApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Autocomplete Test App")
        self.geometry("400x250")

        # Geographical reference list
        self.locations = [
            "JNB - OR Tambo International, Johannesburg",
            "CPT - Cape Town International, Cape Town",
            "DUR - King Shaka International, Durban",
            "PLZ - Chief Dawid Stuurman International, Gqeberha",
            "LHR - Heathrow Airport, London",
            "FRA - Frankfurt Airport, Frankfurt"
        ]

        self.lbl = ttk.Label(self, text="Select Origin/Destination:")
        self.lbl.pack(pady=10)

        self.autocomplete_entry = AutocompleteEntry(self, self.locations)
        self.autocomplete_entry.pack(pady=5, padx=20, fill=tk.X)


class TestAutocompleteUI(unittest.TestCase):

    def setUp(self):
        self.app = TravelAutocompleteApp()
        self.app.update_idletasks()

    def tearDown(self):
        self.app.destroy()

    def test_autocomplete_filtering_matches(self):
        """Test that typing characters filters the popup listbox with correct matching entries."""
        entry = self.app.autocomplete_entry

        # Simulate typing 'JNB'
        entry.var.set("JNB")
        self.app.update_idletasks()

        # Verify listbox was created and displays matching items
        self.assertIsNotNone(entry.listbox, "Listbox should appear when matches are found.")
        self.assertEqual(entry.listbox.size(), 1, "Should find exactly 1 match for 'JNB'.")
        self.assertEqual(entry.listbox.get(0), "JNB - OR Tambo International, Johannesburg")

    def test_autocomplete_multiple_matches(self):
        """Test partial string search matching multiple locations (e.g. 'International')."""
        entry = self.app.autocomplete_entry

        # Simulate typing 'International'
        entry.var.set("International")
        self.app.update_idletasks()

        self.assertIsNotNone(entry.listbox)
        self.assertGreaterEqual(entry.listbox.size(), 4, "Should match multiple international airports.")

    def test_autocomplete_no_matches(self):
        """Test that typing non-existent locations hides/does not create the listbox."""
        entry = self.app.autocomplete_entry

        # Simulate typing gibberish
        entry.var.set("XYZ999")
        self.app.update_idletasks()

        # Listbox should not exist or should be hidden
        if entry.listbox:
            # If it exists, ensure it's not placed/visible or empty
            self.assertFalse(entry.listbox.winfo_ismapped())


if __name__ == '__main__':
    unittest.main()