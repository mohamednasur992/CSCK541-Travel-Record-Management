import tkinter as tk
from tkinter import ttk
import unittest


class TravelApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Travel Record Manager")
        self.geometry("500x300")

        # Sample travel data
        self.data = [
            ("FA123", "JNB", "CPT", "2026-11-15"),
            ("ZB456", "DUR", "JNB", "2026-11-10"),
            ("AA111", "PLZ", "JNB", "2026-11-12")
        ]

        # Search entry field
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self, textvariable=self.search_var)
        self.search_entry.pack(pady=5)
        self.search_var.trace_add("write", self.filter_table)

        # Treeview data table
        self.tree = ttk.Treeview(self, columns=("Flight", "Origin", "Destination", "Date"), show="headings")
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_column(c, False))
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.populate_table(self.data)

    def populate_table(self, rows):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in rows:
            self.tree.insert("", tk.END, values=row)

    def filter_table(self, *args):
        query = self.search_var.get().lower()
        filtered = [r for r in self.data if any(query in str(val).lower() for val in r)]
        self.populate_table(filtered)

    def sort_column(self, col, reverse):
        col_idx = self.tree["columns"].index(col)
        rows = [self.tree.item(item)['values'] for item in self.tree.get_children()]
        rows.sort(key=lambda x: str(x[col_idx]), reverse=reverse)
        self.populate_table(rows)
        # Toggle sort order for subsequent clicks
        self.tree.heading(col, command=lambda: self.sort_column(col, not reverse))


class TestTravelAppUI(unittest.TestCase):

    def setUp(self):
        """Initialize the Tkinter application instance before each test."""
        self.app = TravelApp()
        # Process pending GUI events so widgets render properly
        self.app.update_idletasks()

    def tearDown(self):
        """Safely destroy the application window after each test to free resources."""
        self.app.destroy()

    def test_initial_table_population(self):
        """Test that all initial records load into the Treeview on startup."""
        children = self.app.tree.get_children()
        self.assertEqual(len(children), 3, "Should display 3 initial rows.")

    def test_search_filtering_ui(self):
        """Test that updating the search StringVar dynamically filters the table view."""
        # Simulate typing 'CPT' into the search box
        self.app.search_var.set("CPT")

        children = self.app.tree.get_children()
        self.assertEqual(len(children), 1, "Filter should match exactly 1 record.")

        row_values = self.app.tree.item(children[0], 'values')
        self.assertIn("CPT", row_values)

    def test_column_sorting_ui(self):
        """Test that triggering column sorting reorders the rows alphabetically/numerically."""
        # Sort by Flight number ascending
        self.app.sort_column("Flight", reverse=False)

        children = self.app.tree.get_children()
        first_row_values = self.app.tree.item(children[0], 'values')

        # 'AA111' should be first alphabetically
        self.assertEqual(first_row_values[0], "AA111")


if __name__ == '__main__':
    unittest.main()