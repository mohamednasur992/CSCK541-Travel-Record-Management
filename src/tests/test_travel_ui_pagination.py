import tkinter as tk
from tkinter import ttk
import unittest


class PaginatedTravelApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Paginated Travel Manager")
        self.geometry("600x400")

        # Larger dataset for pagination testing (7 records, page size 3)
        self.data = [
            ("FA123", "JNB", "CPT", "2026-11-15"),
            ("ZB456", "DUR", "JNB", "2026-11-10"),
            ("AA111", "PLZ", "JNB", "2026-11-12"),
            ("SA789", "JNB", "DUR", "2026-11-20"),
            ("BA055", "JNB", "LHR", "2026-12-01"),
            ("SA312", "CPT", "JNB", "2026-12-05"),
            ("LH432", "JNB", "FRA", "2026-12-10")
        ]

        self.page_size = 3
        self.current_page = 0

        # Treeview data table
        self.tree = ttk.Treeview(self, columns=("Flight", "Origin", "Destination", "Date"), show="headings")
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Pagination Controls Frame
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)

        self.prev_btn = ttk.Button(btn_frame, text="Previous", command=self.prev_page)
        self.prev_btn.pack(side=tk.LEFT, padx=5)

        self.page_label = ttk.Label(btn_frame, text="")
        self.page_label.pack(side=tk.LEFT, padx=5)

        self.next_btn = ttk.Button(btn_frame, text="Next", command=self.next_page)
        self.next_btn.pack(side=tk.LEFT, padx=5)

        self.update_table_view()

    def update_table_view(self):
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Calculate slice boundaries
        start_idx = self.current_page * self.page_size
        end_idx = start_idx + self.page_size
        current_slice = self.data[start_idx:end_idx]

        # Insert rows for the current page
        for row in current_slice:
            self.tree.insert("", tk.END, values=row)

        # Update page label text
        total_pages = max(1, (len(self.data) + self.page_size - 1) // self.page_size)
        self.page_label.config(text=f"Page {self.current_page + 1} of {total_pages}")

        # Enable/Disable buttons based on boundaries
        self.prev_btn.config(state=tk.NORMAL if self.current_page > 0 else tk.DISABLED)
        self.next_btn.config(state=tk.NORMAL if end_idx < len(self.data) else tk.DISABLED)

    def next_page(self):
        if (self.current_page + 1) * self.page_size < len(self.data):
            self.current_page += 1
            self.update_table_view()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_table_view()


class TestPaginatedTravelApp(unittest.TestCase):

    def setUp(self):
        self.app = PaginatedTravelApp()
        self.app.update_idletasks()

    def tearDown(self):
        self.app.destroy()

    def test_initial_pagination_state(self):
        """Test that page 1 loads the correct page size (3 items) and disables 'Previous'."""
        children = self.app.tree.get_children()
        self.assertEqual(len(children), 3, "Page 1 should display exactly 3 records.")
        self.assertEqual(str(self.app.prev_btn['state']), 'disabled', "Previous button should be disabled on page 1.")
        self.assertEqual(str(self.app.next_btn['state']), 'normal', "Next button should be enabled.")

    def test_next_page_transition(self):
        """Test clicking 'Next' advances the page, displays the next slice, and updates states."""
        # Click Next
        self.app.next_page()

        self.assertEqual(self.app.current_page, 1)
        children = self.app.tree.get_children()
        self.assertEqual(len(children), 3, "Page 2 should display 3 records.")

        # Verify first item on page 2 matches index 3 of data array ('SA789')
        first_row_values = self.app.tree.item(children[0], 'values')
        self.assertEqual(first_row_values[0], "SA789")

        # Previous button should now be enabled
        self.assertEqual(str(self.app.prev_btn['state']), 'normal')

    def test_pagination_bounds_end(self):
        """Test navigating to the last page disables the 'Next' button."""
        # Total 7 items, page size 3 -> 3 pages total (indices 0, 1, 2)
        self.app.next_page()  # Page 2
        self.app.next_page()  # Page 3 (Last page, contains 1 item)

        children = self.app.tree.get_children()
        self.assertEqual(len(children), 1, "Last page should display the remaining 1 record.")
        self.assertEqual(str(self.app.next_btn['state']), 'disabled',
                         "Next button should be disabled on the final page.")


if __name__ == '__main__':
    unittest.main()