"""Airline management tab for the Travel Record Management System."""

import tkinter as tk
from tkinter import messagebox, ttk

# pylint: disable=import-error
from gui.autocomplete import AutocompleteCombobox
from gui.constants import WORLD_AIRLINES


# Explicit column definitions provide user-friendly Treeview headings.
AIRLINE_COLUMNS = {
    "airline_id": "Airline ID",
    "company_name": "Company Name",
}

# Field order used when displaying and filtering airline records.
AIRLINE_RECORD_FIELDS = (
    "id",
    "company_name",
)

# Subtle row colours improve record scanning without adding visual clutter.
TABLE_ROW_EVEN = "#FFFFFF"
TABLE_ROW_ODD = "#F3F7FA"

class AirlineTab:  # pylint: disable=too-many-instance-attributes
    """Manage airline data entry, validation, searching, and CRUD operations."""

    def __init__(self, notebook, main_window):
        """Create the airline tab and initialise its interface components."""
        self.notebook = notebook
        self.main = main_window
        self.rm = main_window.rm

        # Widget references are initialised here and configured in init_widgets().
        self.airline_search_var = None
        self.airline_id_entry = None
        self.airline_name_entry = None
        self.airline_tree = None

        self.tab = ttk.Frame(self.notebook)
        self.notebook.add(self.tab, text=" ✈️ Airlines ")

        # The left-hand frame contains the airline data-entry form.
        self.form_frame = ttk.LabelFrame(
            self.tab,
            text=" Airline Details ",
            padding=15,
        )
        self.form_frame.pack(
            side="left",
            fill="y",
            padx=10,
            pady=10,
        )
        self.form_frame.columnconfigure(1, weight=1)

        # The right-hand frame contains search controls and the airline table.
        self.display_frame = ttk.LabelFrame(
            self.tab,
            text=" Airline List ",
            padding=15,
        )
        self.display_frame.pack(
            side="right",
            fill="both",
            expand=True,
            padx=10,
            pady=10,
        )

        self.init_widgets()

    def init_widgets(self):
        """Create the airline form, actions, search controls, and Treeview."""

        # Search controls filter displayed airline records as the user types.
        search_frame = ttk.Frame(self.display_frame)
        search_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(
            search_frame,
            text="Search Filter:",
        ).pack(side="left", padx=(0, 5))

        self.airline_search_var = tk.StringVar()

        # Use trace_add instead of the older trace method.
        self.airline_search_var.trace_add(
            "write",
            self.filter_airline_table,
        )

        search_entry = ttk.Entry(
            search_frame,
            textvariable=self.airline_search_var,
            width=30,
        )
        search_entry.pack(side="left", padx=5)

        ttk.Button(
            search_frame,
            text="Clear Search",
            command=lambda: self.airline_search_var.set(""),
        ).pack(side="left", padx=5)

        # Airline details are captured in the left-hand form.
        ttk.Label(
            self.form_frame,
            text="Airline ID:",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=5,
        )

        self.airline_id_entry = ttk.Entry(
            self.form_frame,
            state="readonly",
        )
        self.airline_id_entry.grid(
            row=0,
            column=1,
            sticky="ew",
            pady=5,
        )

        ttk.Label(
            self.form_frame,
            text="Company Name:",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            pady=5,
        )

        self.airline_name_entry = AutocompleteCombobox(
            self.form_frame,
            list_of_items=WORLD_AIRLINES,
        )
        self.airline_name_entry.grid(
            row=1,
            column=1,
            sticky="ew",
            pady=5,
        )

        # Assign the next available ID when an airline is selected.
        self.airline_name_entry.bind(
            "<<ComboboxSelected>>",
            self.on_airline_name_selected,
        )

        # CRUD actions operate on the current form values.
        button_frame = ttk.Frame(self.form_frame)
        button_frame.grid(
            row=10,
            column=0,
            columnspan=2,
            pady=15,
        )

        ttk.Button(
            button_frame,
            text="Add",
            command=self.on_add_airline,
        ).pack(side="left", padx=2)

        ttk.Button(
            button_frame,
            text="Update",
            command=self.on_update_airline,
        ).pack(side="left", padx=2)

        ttk.Button(
            button_frame,
            text="Clear",
            command=self.clear_form,
        ).pack(side="left", padx=2)

        ttk.Button(
            button_frame,
            text="Delete",
            style="Danger.TButton",
            command=self.on_delete_airline,
        ).pack(side="left", padx=2)

        self.main.add_logo_to_frame(self.form_frame)

        # The Treeview provides a searchable and sortable airline list.
        self.airline_tree = ttk.Treeview(
            self.display_frame,
            columns=tuple(AIRLINE_COLUMNS),
            show="headings",
        )

        # Apply alternating row colours to improve readability.
        self.airline_tree.tag_configure(
            "even_row",
            background=TABLE_ROW_EVEN,
        )

        self.airline_tree.tag_configure(
            "odd_row",
            background=TABLE_ROW_ODD,
        )

        for column, heading in AIRLINE_COLUMNS.items():
            self.airline_tree.heading(
                column,
                text=heading,
                command=lambda selected_column=column: (
                    self.main.sort_treeview_column(
                        self.airline_tree,
                        selected_column,
                        False,
                    )
                ),
            )

            self.airline_tree.column(
                column,
                width=150,
                anchor="center",
            )

        vertical_scrollbar = ttk.Scrollbar(
            self.display_frame,
            orient="vertical",
            command=self.airline_tree.yview,
        )

        self.airline_tree.configure(
            yscrollcommand=vertical_scrollbar.set,
        )

        self.airline_tree.pack(
            side="left",
            fill="both",
            expand=True,
        )

        vertical_scrollbar.pack(
            side="right",
            fill="y",
        )

        # Double-clicking a row loads that airline into the editing form.
        self.airline_tree.bind(
            "<Double-1>",
            self.load_to_form,
        )

        self.refresh_table()
        self.clear_form(report_status=False)

    def get_next_airline_id(self):
        """Return the next available sequential airline ID."""
        airlines = self.rm.search_records(record_type="Airline")

        # Use the highest valid numeric ID rather than relying on record order.
        valid_ids = [
            int(airline["id"])
            for airline in airlines
            if str(airline.get("id", "")).isdigit()
        ]

        return max(valid_ids, default=0) + 1

    def on_airline_name_selected(self, _event=None):
        """Assign an ID when the user selects an airline company."""

        if self.airline_id_entry.get().strip():
            return

        self.set_airline_id(self.get_next_airline_id())

    def set_airline_id(self, airline_id):
        """Display an airline ID while preserving the read-only field state."""
        self.airline_id_entry.configure(state="normal")
        self.airline_id_entry.delete(0, tk.END)

        if airline_id not in (None, ""):
            self.airline_id_entry.insert(
                0,
                str(airline_id),
            )

        self.airline_id_entry.configure(state="readonly")

    def validate_airline_form(self):
        """Validate the fields required to create or update an airline."""

        company_name = self.airline_name_entry.get().strip()

        if not company_name:
            messagebox.showerror(
                "Missing Information",
                "Company name is required.",
            )
            self.airline_name_entry.focus_set()
            return False

        airline_id = self.airline_id_entry.get().strip()

        if not airline_id:
            # Support manually typed company names that do not generate
            # a ComboboxSelected event.
            self.set_airline_id(self.get_next_airline_id())
            airline_id = self.airline_id_entry.get().strip()

        if not airline_id.isdigit():
            messagebox.showerror(
                "Invalid Airline ID",
                "Airline ID must be a valid number.",
            )
            return False

        return True

    def get_form_data(self):
        """Return the current airline-form values as a record dictionary."""
        airline_id = self.airline_id_entry.get().strip()

        if not airline_id:
            raise ValueError("Airline ID could not be generated.")

        return {
            "id": int(airline_id),
            "type": "Airline",
            "company_name": self.airline_name_entry.get().strip(),
        }

    def on_add_airline(self):
        """Validate and add a new airline record."""

        if not self.validate_airline_form():
            return

        try:
            airline = self.get_form_data()

            # Prevent accidental creation of a duplicate airline identifier.
            existing_airline = self.rm.get_record_by_id(
                airline["id"],
                record_type="Airline",
            )

            if existing_airline:
                messagebox.showerror(
                    "Duplicate Airline",
                    f"Airline ID {airline['id']} already exists.",
                )
                return

            # Prevent duplicate company records even when the ID differs.
            company_name = str(
                airline["company_name"]
            ).strip().casefold()

            duplicate_name = any(
                str(
                    record.get("company_name", "")
                ).strip().casefold() == company_name
                for record in self.rm.search_records(record_type="Airline")
            )

            if duplicate_name:
                messagebox.showerror(
                    "Duplicate Airline",
                    "An airline with this company name already exists.",
                )
                return

            self.rm.add_airline(
                airline["id"],
                airline["company_name"],
            )

            company_name = airline["company_name"]

            self.refresh_table()
            self.clear_form()

            self.main.update_status(
                f'Airline "{company_name}" added successfully.'
            )

        except (TypeError, ValueError) as error:
            self.main.update_status(f"Airline creation failed: {error}")
            messagebox.showerror(
                "Unable to Add Airline",
                str(error),
            )

    def on_update_airline(self):
        """Validate and update the airline currently loaded in the form."""
        airline_id = self.airline_id_entry.get().strip()

        if not airline_id:
            messagebox.showwarning(
                "No Airline Selected",
                "Select an airline to update.",
            )
            return

        if not self.validate_airline_form():
            return

        try:
            updated_data = self.get_form_data()

            # Prevent an edited company name from duplicating another airline.
            company_name = str(
                updated_data["company_name"]
            ).strip().casefold()

            duplicate_name = any(
                str(record.get("id")) != str(airline_id)
                and str(
                    record.get("company_name", "")
                ).strip().casefold() == company_name
                for record in self.rm.search_records(record_type="Airline")
            )

            if duplicate_name:
                messagebox.showerror(
                    "Duplicate Airline",
                    "Another airline already uses this company name.",
                )
                return

            updated = self.rm.update_record(
                airline_id,
                updated_data,
                record_type="Airline",
            )

            if not updated:
                messagebox.showwarning(
                    "Update Failed",
                    "The selected airline could not be found.",
                )
                return

            self.refresh_table()
            self.clear_form(report_status=False)

            self.main.update_status(
                f'Airline "{updated_data["company_name"]}" updated successfully.'
            )

            messagebox.showinfo(
                "Success",
                "Airline updated successfully.",
            )

        except (TypeError, ValueError) as error:
            self.main.update_status(f"Airline update failed: {error}")
            messagebox.showerror(
                "Unable to Update Airline",
                str(error),
            )

    def on_delete_airline(self):
        """Delete the airline selected in the Treeview."""
        selected_items = self.airline_tree.selection()

        if not selected_items:
            self.main.update_status("Select an airline to delete.")
            messagebox.showwarning(
                "No Airline Selected",
                "Select an airline to delete.",
            )
            return

        selected_item = selected_items[0]
        values = self.airline_tree.item(
            selected_item,
            "values",
        )
        airline_id = values[0]
        company_name = values[1]

        if not messagebox.askyesno(
            "Confirm Deletion",
            f"Delete {company_name} (Airline ID {airline_id})?",
        ):
            self.main.update_status("Airline deletion cancelled.")
            return

        try:
            deleted = self.rm.delete_record(
                airline_id,
                record_type="Airline",
            )

            if not deleted:
                messagebox.showwarning(
                    "Delete Failed",
                    "The selected airline could not be found.",
                )
                return

            self.refresh_table()
            self.clear_form(report_status=False)

            self.main.update_status(
                f'Airline "{company_name}" deleted successfully.'
            )

            messagebox.showinfo(
                "Success",
                "Airline deleted successfully.",
            )

        except ValueError as error:
            # RecordManager protects airlines referenced by Flight records.
            self.main.update_status(f"Airline deletion blocked: {error}")
            messagebox.showerror(
                "Integrity Constraint",
                str(error),
            )

    def load_to_form(self, _event=None):
        """Load the selected airline record into the form for editing."""
        selected_items = self.airline_tree.selection()

        if not selected_items:
            return

        selected_item = selected_items[0]
        values = self.airline_tree.item(
            selected_item,
            "values",
        )

        self.clear_form(report_status=False)

        # Temporarily unlock the generated ID field while loading the record.
        self.set_airline_id(values[0])

        self.airline_name_entry.insert(
            0,
            values[1],
        )

        self.main.update_status(f'Loaded airline "{values[1]}" for editing.')

    def clear_form(self, report_status=True):
        """Clear all airline fields and return the form to its initial state."""
        self.set_airline_id("")
        self.airline_name_entry.delete(0, tk.END)
        self.airline_name_entry.focus_set()

        if report_status:
            self.main.update_status("Airline form cleared.")

    @staticmethod
    def airline_to_values(airline):
        """Convert an airline record into the Treeview column order."""
        return tuple(
            str(airline.get(field, ""))
            for field in AIRLINE_RECORD_FIELDS
        )

    def insert_airline_row(self, airline, row_index=None):
        """Insert one airline record using alternating row colours."""
        if row_index is None:
            row_index = len(self.airline_tree.get_children())

        row_tag = (
            "even_row"
            if row_index % 2 == 0
            else "odd_row"
        )

        self.airline_tree.insert(
            "",
            "end",
            values=self.airline_to_values(airline),
            tags=(row_tag,),
        )

    def clear_tree(self):
        """Remove all currently displayed rows from the airline Treeview."""
        for item in self.airline_tree.get_children():
            self.airline_tree.delete(item)

    def refresh_table(self):
        """Reload the airline table from the current RecordManager data."""
        self.clear_tree()

        airlines = self.rm.search_records(
            record_type="Airline"
        )

        for row_index, airline in enumerate(airlines):
            self.insert_airline_row(
                airline,
                row_index,
            )

        # Airline changes affect the choices available when creating flights.
        self.main.refresh_flight_dropdowns()

    def filter_airline_table(self, *_args):
        """Filter displayed airlines by ID or company name."""
        query = self.airline_search_var.get().strip().casefold()

        self.clear_tree()

        airlines = self.rm.search_records(
            record_type="Airline"
        )

        matches = []

        for airline in airlines:
            values = self.airline_to_values(airline)

            if not query or any(
                    query in str(value).casefold()
                    for value in values
            ):
                matches.append(airline)

        # Recalculate row colours for the filtered result set so the
        # zebra-striping remains continuous after a search.
        for row_index, airline in enumerate(matches):
            self.insert_airline_row(
                airline,
                row_index,
            )

        if query:
            self.main.update_status(
                f"Airline search returned {len(matches)} record(s)."
            )
        else:
            self.main.update_status(
                f"Showing {len(matches)} airline record(s)."
            )
