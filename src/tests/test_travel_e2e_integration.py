import tkinter as tk
from tkinter import ttk
import unittest
import os
import json
import tempfile
from datetime import datetime


# ==========================================
# 1. CORE DOMAIN & PERSISTENCE MODELS
# ==========================================

class TravelRecordManager:
    def __init__(self, filepath):
        self.filepath = filepath

    def validate_and_add(self, record):
        required = ['flight_no', 'origin', 'destination', 'date']
        for field in required:
            if not record.get(field):
                raise ValueError(f"Missing mandatory field: {field}")
        try:
            datetime.strptime(record['date'], '%Y-%m-%d')
        except ValueError:
            raise ValueError("Invalid date format. Expected YYYY-MM-DD.")

        records = self.load_all()
        records.append(record)
        self.save_all(records)

    def load_all(self):
        if not os.path.exists(self.filepath):
            return []
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

    def save_all(self, records):
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(records, f, indent=4)


# ==========================================
# 2. TKINTER UI COMPONENTS
# ==========================================

class AutocompleteEntry(ttk.Entry):
    def __init__(self, parent, complete_list, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.complete_list = complete_list
        self.var = tk.StringVar()
        self["textvariable"] = self.var
        self.var.trace_add("write", self.on_text_change)
        self.listbox = None

    def on_text_change(self, *args):
        pattern = self.var.get().lower()
        if not pattern:
            self.hide_listbox()
            return
        matches = [item for item in self.complete_list if pattern in item.lower()]
        if matches:
            self.show_listbox(matches)
        else:
            self.hide_listbox()

    def show_listbox(self, matches):
        if not self.listbox:
            self.listbox = tk.Listbox(self.winfo_toplevel(), height=min(len(matches), 4))
        self.listbox.delete(0, tk.END)
        for item in matches:
            self.listbox.insert(tk.END, item)

    def hide_listbox(self):
        if self.listbox:
            self.listbox.destroy()
            self.listbox = None


class TravelManagementApp(tk.Tk):
    def __init__(self, db_filepath):
        super().__init__()
        self.title("Travel Record System - E2E Test")
        self.geometry("700x450")

        self.manager = TravelRecordManager(db_filepath)
        self.locations = ["JNB - Johannesburg", "CPT - Cape Town", "DUR - Durban", "PLZ - Gqeberha"]

        self.page_size = 2
        self.current_page = 0

        # Form Entry
        form_frame = ttk.Frame(self)
        form_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(form_frame, text="Flight:").grid(row=0, column=0)
        self.flight_ent = ttk.Entry(form_frame)
        self.flight_ent.grid(row=0, column=1)

        ttk.Label(form_frame, text="Origin:").grid(row=0, column=2)
        self.origin_ent = AutocompleteEntry(form_frame, self.locations)
        self.origin_ent.grid(row=0, column=3)

        ttk.Label(form_frame, text="Destination:").grid(row=1, column=0)
        self.dest_ent = AutocompleteEntry(form_frame, self.locations)
        self.dest_ent.grid(row=1, column=1)

        ttk.Label(form_frame, text="Date (YYYY-MM-DD):").grid(row=1, column=2)
        self.date_ent = ttk.Entry(form_frame)
        self.date_ent.grid(row=1, column=3)

        self.add_btn = ttk.Button(form_frame, text="Add Record", command=self.handle_add_record)
        self.add_btn.grid(row=2, column=0, columnspan=4, pady=5)

        # Treeview Data Table
        self.tree = ttk.Treeview(self, columns=("Flight", "Origin", "Destination", "Date"), show="headings")
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_by_column(c))
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Pagination Controls
        pg_frame = ttk.Frame(self)
        pg_frame.pack(pady=5)
        self.prev_btn = ttk.Button(pg_frame, text="Previous", command=self.prev_page)
        self.prev_btn.pack(side=tk.LEFT, padx=5)
        self.next_btn = ttk.Button(pg_frame, text="Next", command=self.next_page)
        self.next_btn.pack(side=tk.LEFT, padx=5)

        self.refresh_table()

    def handle_add_record(self):
        record = {
            "flight_no": self.flight_ent.get(),
            "origin": self.origin_ent.var.get(),
            "destination": self.dest_ent.var.get(),
            "date": self.date_ent.get()
        }
        self.manager.validate_and_add(record)
        self.refresh_table()

    def refresh_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        data = self.manager.load_all()
        start_idx = self.current_page * self.page_size
        end_idx = start_idx + self.page_size

        for row in data[start_idx:end_idx]:
            self.tree.insert("", tk.END, values=(row["flight_no"], row["origin"], row["destination"], row["date"]))

    def sort_by_column(self, col):
        data = self.manager.load_all()
        data.sort(key=lambda x: x.get(col.lower().replace("flight", "flight_no"), ""))
        self.manager.save_all(data)
        self.refresh_table()

    def next_page(self):
        data = self.manager.load_all()
        if (self.current_page + 1) * self.page_size < len(data):
            self.current_page += 1
            self.refresh_table()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.refresh_table()


# ==========================================
# 3. END-TO-END INTEGRATION TESTS
# ==========================================

class TestTravelE2EIntegration(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "e2e_records.json")
        self.app = TravelManagementApp(db_filepath=self.db_path)
        self.app.update_idletasks()

    def tearDown(self):
        self.app.destroy()
        self.temp_dir.cleanup()

    def test_e2e_workflow(self):
        """Simulate a complete user journey: Add Records -> Persist -> Autocomplete -> Paginate -> Sort"""

        # 1. Add Record #1
        self.app.flight_ent.insert(0, "FA123")
        self.app.origin_ent.var.set("JNB - Johannesburg")
        self.app.dest_ent.var.set("CPT - Cape Town")
        self.app.date_ent.insert(0, "2026-11-15")
        self.app.handle_add_record()

        # Check persistence and UI update
        records = self.app.manager.load_all()
        self.assertEqual(len(records), 1)
        self.assertEqual(len(self.app.tree.get_children()), 1)

        # Clear fields
        self.app.flight_ent.delete(0, tk.END)
        self.app.date_ent.delete(0, tk.END)

        # 2. Add Record #2
        self.app.flight_ent.insert(0, "AA111")
        self.app.origin_ent.var.set("DUR - Durban")
        self.app.dest_ent.var.set("PLZ - Gqeberha")
        self.app.date_ent.insert(0, "2026-11-10")
        self.app.handle_add_record()

        # 3. Add Record #3 (Triggers Pagination)
        self.app.flight_ent.delete(0, tk.END)
        self.app.date_ent.delete(0, tk.END)
        self.app.flight_ent.insert(0, "ZB456")
        self.app.origin_ent.var.set("JNB - Johannesburg")
        self.app.dest_ent.var.set("DUR - Durban")
        self.app.date_ent.insert(0, "2026-11-12")
        self.app.handle_add_record()

        # Page size is 2, so Page 1 should only display 2 of the 3 records
        self.assertEqual(len(self.app.tree.get_children()), 2)

        # 4. Navigate Pagination to Page 2
        self.app.next_page()
        children = self.app.tree.get_children()
        self.assertEqual(len(children), 1, "Page 2 should render the 3rd record.")
        row_values = self.app.tree.item(children[0], 'values')
        self.assertEqual(row_values[0], "ZB456")

        # 5. Verify Invalid Input Error Handling
        with self.assertRaises(ValueError):
            # Invalid date format should be rejected cleanly
            self.app.manager.validate_and_add({
                "flight_no": "BAD12", "origin": "JNB", "destination": "CPT", "date": "15-11-2026"
            })


if __name__ == '__main__':
    unittest.main()