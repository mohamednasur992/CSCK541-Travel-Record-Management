"""Flight booking tab for the Travel Record Management System."""

import tkinter as tk
from tkinter import messagebox, ttk

from tkcalendar import DateEntry

from gui.autocomplete import AutocompleteCombobox
from gui.constants import WORLD_CITIES

# Explicit Treeview headings provide user-friendly column names.
FLIGHT_COLUMNS = {
    "client_id": "Client ID",
    "airline_id": "Airline ID",
    "date": "Travel Date",
    "start_city": "Start City",
    "end_city": "Destination",
}

# Field order used when displaying and filtering flight records.
FLIGHT_RECORD_FIELDS = (
    "client_id",
    "airline_id",
    "date",
    "start_city",
    "end_city",
)


class FlightTab:
    """
    Manage flight data entry, validation, searching, and CRUD operations.

    Flight records associate an existing client with an existing airline.
    Record storage and integrity rules are delegated to RecordManager.
    """

    def __init__(self, notebook, main_window):
        """Create the flight tab and initialise its interface components."""
        self.notebook = notebook
        self.main = main_window
        self.rm = main_window.rm

        # Flights currently use a composite key instead of a standalone ID.
        # The original values are retained when a record is loaded for editing.
        self.original_flight_key = None

        self.tab = ttk.Frame(self.notebook)
        self.notebook.add(self.tab, text=" 🎫 Flights ")

        # The left-hand frame contains the flight-booking form.
        self.form_frame = ttk.LabelFrame(
            self.tab,
            text=" Flight Booking Details ",
            padding=15,
        )
        self.form_frame.pack(
            side="left",
            fill="y",
            padx=10,
            pady=10,
        )
        self.form_frame.columnconfigure(1, weight=1)

        # The right-hand frame contains search controls and the flight table.
        self.display_frame = ttk.LabelFrame(
            self.tab,
            text=" Flight Schedule List ",
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
        """Create the flight form, actions, search controls, and Treeview."""

        # Search controls filter displayed flight records as the user types.
        search_frame = ttk.Frame(self.display_frame)
        search_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(
            search_frame,
            text="Search Filter:",
        ).pack(side="left", padx=(0, 5))

        self.flight_search_var = tk.StringVar()
        self.flight_search_var.trace_add(
            "write",
            self.filter_flight_table,
        )

        search_entry = ttk.Entry(
            search_frame,
            textvariable=self.flight_search_var,
            width=30,
        )
        search_entry.pack(side="left", padx=5)

        ttk.Button(
            search_frame,
            text="Clear Search",
            command=lambda: self.flight_search_var.set(""),
        ).pack(side="left", padx=5)

        # A flight must reference an existing client.
        ttk.Label(
            self.form_frame,
            text="Client:",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=5,
        )

        self.flight_client_combo = AutocompleteCombobox(
            self.form_frame,
            list_of_items=self.main.get_client_dropdown_items(),
        )
        self.flight_client_combo.grid(
            row=0,
            column=1,
            sticky="ew",
            pady=5,
        )

        # A flight must reference an existing airline.
        ttk.Label(
            self.form_frame,
            text="Airline:",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            pady=5,
        )

        self.flight_airline_combo = AutocompleteCombobox(
            self.form_frame,
            list_of_items=self.main.get_airline_dropdown_items(),
        )
        self.flight_airline_combo.grid(
            row=1,
            column=1,
            sticky="ew",
            pady=5,
        )

        ttk.Label(
            self.form_frame,
            text="Travel Date:",
        ).grid(
            row=2,
            column=0,
            sticky="w",
            pady=5,
        )

        self.flight_date_entry = DateEntry(
            self.form_frame,
            background="darkblue",
            foreground="white",
            date_pattern="yyyy-mm-dd",
        )
        self.flight_date_entry.grid(
            row=2,
            column=1,
            sticky="ew",
            pady=5,
        )

        # Start with no travel date selected so the user must choose a travel date.
        self.flight_date_entry.delete(0, tk.END)

        ttk.Label(
            self.form_frame,
            text="Start City:",
        ).grid(
            row=3,
            column=0,
            sticky="w",
            pady=5,
        )

        self.flight_start_entry = AutocompleteCombobox(
            self.form_frame,
            list_of_items=WORLD_CITIES,
        )
        self.flight_start_entry.grid(
            row=3,
            column=1,
            sticky="ew",
            pady=5,
        )

        ttk.Label(
            self.form_frame,
            text="Destination:",
        ).grid(
            row=4,
            column=0,
            sticky="w",
            pady=5,
        )

        self.flight_end_entry = AutocompleteCombobox(
            self.form_frame,
            list_of_items=WORLD_CITIES,
        )
        self.flight_end_entry.grid(
            row=4,
            column=1,
            sticky="ew",
            pady=5,
        )

        # CRUD actions operate on the values currently shown in the form.
        button_frame = ttk.Frame(self.form_frame)
        button_frame.grid(
            row=10,
            column=0,
            columnspan=2,
            pady=15,
        )

        ttk.Button(
            button_frame,
            text="Book",
            command=self.on_add_flight,
        ).pack(side="left", padx=2)

        ttk.Button(
            button_frame,
            text="Update",
            command=self.on_update_flight,
        ).pack(side="left", padx=2)

        ttk.Button(
            button_frame,
            text="Clear",
            command=self.clear_form,
        ).pack(side="left", padx=2)

        ttk.Button(
            button_frame,
            text="Delete",
            command=self.on_delete_flight,
        ).pack(side="left", padx=2)

        self.main.add_logo_to_frame(self.form_frame)

        # The Treeview provides a searchable and sortable flight schedule.
        self.flight_tree = ttk.Treeview(
            self.display_frame,
            columns=tuple(FLIGHT_COLUMNS),
            show="headings",
        )

        for column, heading in FLIGHT_COLUMNS.items():
            self.flight_tree.heading(
                column,
                text=heading,
                command=lambda selected_column=column: (
                    self.main.sort_treeview_column(
                        self.flight_tree,
                        selected_column,
                        False,
                    )
                ),
            )

            self.flight_tree.column(
                column,
                width=125,
                anchor="center",
            )

        vertical_scrollbar = ttk.Scrollbar(
            self.display_frame,
            orient="vertical",
            command=self.flight_tree.yview,
        )

        horizontal_scrollbar = ttk.Scrollbar(
            self.display_frame,
            orient="horizontal",
            command=self.flight_tree.xview,
        )

        self.flight_tree.configure(
            yscrollcommand=vertical_scrollbar.set,
            xscrollcommand=horizontal_scrollbar.set,
        )

        horizontal_scrollbar.pack(
            side="bottom",
            fill="x",
        )

        vertical_scrollbar.pack(
            side="right",
            fill="y",
        )

        self.flight_tree.pack(
            side="left",
            fill="both",
            expand=True,
        )

        # Double-clicking a row loads that flight into the editing form.
        self.flight_tree.bind(
            "<Double-1>",
            self.load_to_form,
        )

        self.refresh_table()
        self.clear_form()

    @staticmethod
    def extract_id_from_selection(selection_str):
        """
        Extract an integer ID from an 'ID - Display Name' dropdown value.

        A plain numeric value is also accepted for existing records and tests.
        """
        if not selection_str:
            return None

        selection_str = str(selection_str).strip()

        if selection_str.isdigit():
            return int(selection_str)

        identifier = selection_str.split(" - ", maxsplit=1)[0].strip()

        if identifier.isdigit():
            return int(identifier)

        return None

    def refresh_dropdowns(self):
        """Refresh client and airline choices from current stored records."""

        client_items = self.main.get_client_dropdown_items()
        airline_items = self.main.get_airline_dropdown_items()

        # Replace both the active values and source lists used by autocomplete.
        self.flight_client_combo.all_items = sorted(client_items)
        self.flight_client_combo["values"] = (
            self.flight_client_combo.all_items
        )

        self.flight_airline_combo.all_items = sorted(airline_items)
        self.flight_airline_combo["values"] = (
            self.flight_airline_combo.all_items
        )

    def validate_flight_form(self):
        """Validate the fields required to create or update a flight."""
        client_id = self.extract_id_from_selection(
            self.flight_client_combo.get()
        )
        airline_id = self.extract_id_from_selection(
            self.flight_airline_combo.get()
        )
        travel_date = self.flight_date_entry.get().strip()
        start_city = self.flight_start_entry.get().strip()
        end_city = self.flight_end_entry.get().strip()

        if client_id is None:
            messagebox.showerror(
                "Invalid Client",
                "Select a valid client.",
            )
            self.flight_client_combo.focus_set()
            return False

        if airline_id is None:
            messagebox.showerror(
                "Invalid Airline",
                "Select a valid airline.",
            )
            self.flight_airline_combo.focus_set()
            return False

        if not travel_date:
            messagebox.showerror(
                "Missing Information",
                "Travel date is required.",
            )
            self.flight_date_entry.focus_set()
            return False

        # Confirm that both referenced records still exist.
        client = self.rm.get_record_by_id(
            client_id,
            record_type="Client",
        )
        if client is None:
            messagebox.showerror(
                "Client Not Found",
                "The selected client no longer exists.",
            )
            return False

        airline = self.rm.get_record_by_id(
            airline_id,
            record_type="Airline",
        )
        if airline is None:
            messagebox.showerror(
                "Airline Not Found",
                "The selected airline no longer exists.",
            )
            return False

        if not start_city:
            messagebox.showerror(
                "Missing Information",
                "Start city is required.",
            )
            self.flight_start_entry.focus_set()
            return False

        if not end_city:
            messagebox.showerror(
                "Missing Information",
                "Destination is required.",
            )
            self.flight_end_entry.focus_set()
            return False

        if start_city.casefold() == end_city.casefold():
            messagebox.showerror(
                "Invalid Route",
                "Start city and destination must be different.",
            )
            self.flight_end_entry.focus_set()
            return False

        return True

    def get_form_data(self):
        """Return the current flight-form values as a record dictionary."""
        client_id = self.extract_id_from_selection(
            self.flight_client_combo.get()
        )
        airline_id = self.extract_id_from_selection(
            self.flight_airline_combo.get()
        )

        return {
            "type": "Flight",
            "client_id": client_id,
            "airline_id": airline_id,
            "date": self.flight_date_entry.get().strip(),
            "start_city": self.flight_start_entry.get().strip(),
            "end_city": self.flight_end_entry.get().strip(),
        }

    def flight_exists(self, flight_data, exclude_original=False):
        """Return True when an identical flight booking already exists."""

        for record in self.rm.search_records(record_type="Flight"):
            same_flight = (
                str(record.get("client_id"))
                == str(flight_data["client_id"])
                and str(record.get("airline_id"))
                == str(flight_data["airline_id"])
                and str(record.get("date"))
                == str(flight_data["date"])
                and str(record.get("start_city", "")).casefold()
                == flight_data["start_city"].casefold()
                and str(record.get("end_city", "")).casefold()
                == flight_data["end_city"].casefold()
            )

            if not same_flight:
                continue

            if exclude_original and self.original_flight_key:
                same_as_original = (
                    str(record.get("client_id"))
                    == str(self.original_flight_key["client_id"])
                    and str(record.get("airline_id"))
                    == str(self.original_flight_key["airline_id"])
                    and str(record.get("date"))
                    == str(self.original_flight_key["date"])
                    and str(record.get("start_city"))
                    == str(self.original_flight_key["start_city"])
                    and str(record.get("end_city"))
                    == str(self.original_flight_key["end_city"])
                )

                if same_as_original:
                    continue

            return True

        return False

    def on_add_flight(self):
        """Validate and create a new flight booking."""

        if not self.validate_flight_form():
            return

        try:
            flight = self.get_form_data()

            # Prevent the same client booking from being stored twice.
            if self.flight_exists(flight):
                messagebox.showerror(
                    "Duplicate Booking",
                    "An identical flight booking already exists.",
                )
                return

            self.rm.add_flight(
                flight["client_id"],
                flight["airline_id"],
                flight["date"],
                flight["start_city"],
                flight["end_city"],
            )

            self.refresh_table()
            self.clear_form()

            messagebox.showinfo(
                "Success",
                "Flight booked successfully.",
            )

        except (TypeError, ValueError) as error:
            messagebox.showerror(
                "Unable to Book Flight",
                str(error),
            )

    def on_update_flight(self):
        """Validate and update the flight currently loaded in the form."""

        if not self.original_flight_key:
            messagebox.showwarning(
                "No Flight Selected",
                "Double-click a flight to load it for editing.",
            )
            return

        if not self.validate_flight_form():
            return

        try:
            updated_data = self.get_form_data()

            if self.flight_exists(
                updated_data,
                exclude_original=True,
            ):
                messagebox.showerror(
                    "Duplicate Booking",
                    "Another identical flight booking already exists.",
                )
                return

            # Original composite values locate the existing record before
            # replacing them with the edited values.
            updated = self.rm.update_record(
                self.original_flight_key["client_id"],
                updated_data,
                record_type="Flight",
                old_airline_id=(
                    self.original_flight_key["airline_id"]
                ),
                old_date=self.original_flight_key["date"],
                old_start=(
                    self.original_flight_key["start_city"]
                ),
                old_end=self.original_flight_key["end_city"],
            )

            if not updated:
                messagebox.showwarning(
                    "Update Failed",
                    "The selected flight could not be found.",
                )
                return

            self.refresh_table()
            self.clear_form()

            messagebox.showinfo(
                "Success",
                "Flight updated successfully.",
            )

        except (TypeError, ValueError) as error:
            messagebox.showerror(
                "Unable to Update Flight",
                str(error),
            )

    def on_delete_flight(self):
        """Delete the flight selected in the Treeview."""
        selected_items = self.flight_tree.selection()

        if not selected_items:
            messagebox.showwarning(
                "No Flight Selected",
                "Select a flight to delete.",
            )
            return

        selected_item = selected_items[0]
        values = self.flight_tree.item(
            selected_item,
            "values",
        )

        client_id = values[0]
        airline_id = values[1]
        travel_date = values[2]
        start_city = values[3]
        end_city = values[4]

        confirmation_message = (
            f"Delete the flight from {start_city} to {end_city} "
            f"on {travel_date}?"
        )

        if not messagebox.askyesno(
            "Confirm Deletion",
            confirmation_message,
        ):
            return

        try:
            deleted = self.rm.delete_record(
                client_id,
                record_type="Flight",
                airline_id=airline_id,
                date=travel_date,
            )

            if not deleted:
                messagebox.showwarning(
                    "Delete Failed",
                    "The selected flight could not be found.",
                )
                return

            self.refresh_table()
            self.clear_form()

            messagebox.showinfo(
                "Success",
                "Flight booking removed successfully.",
            )

        except (TypeError, ValueError) as error:
            messagebox.showerror(
                "Unable to Delete Flight",
                str(error),
            )

    def load_to_form(self, _event=None):
        """Load the selected flight record into the form for editing."""
        selected_items = self.flight_tree.selection()

        if not selected_items:
            return

        selected_item = selected_items[0]
        values = self.flight_tree.item(
            selected_item,
            "values",
        )

        self.clear_form()

        # Preserve the original composite values because Flight records
        # currently have no standalone flight ID.
        self.original_flight_key = {
            "client_id": values[0],
            "airline_id": values[1],
            "date": values[2],
            "start_city": values[3],
            "end_city": values[4],
        }

        # Restore user-friendly dropdown values where matching records exist.
        self.flight_client_combo.set(
            self.find_dropdown_value(
                self.main.get_client_dropdown_items(),
                values[0],
            )
        )

        self.flight_airline_combo.set(
            self.find_dropdown_value(
                self.main.get_airline_dropdown_items(),
                values[1],
            )
        )

        self.flight_date_entry.set_date(values[2])
        self.flight_start_entry.set(values[3])
        self.flight_end_entry.set(values[4])

    @staticmethod
    def find_dropdown_value(dropdown_items, record_id):
        """Return the dropdown item matching the supplied record ID."""
        record_id = str(record_id)

        for item in dropdown_items:
            identifier = str(item).split(" - ", maxsplit=1)[0].strip()

            if identifier == record_id:
                return item

        # Fall back to the numeric ID when the related display record
        # is unavailable.
        return record_id

    def clear_form(self):
        """Clear flight fields and reset the editing state."""
        self.original_flight_key = None

        self.flight_client_combo.set("")
        self.flight_airline_combo.set("")
        self.flight_date_entry.delete(0, tk.END)
        self.flight_start_entry.set("")
        self.flight_end_entry.set("")

        self.flight_client_combo.focus_set()

    @staticmethod
    def flight_to_values(flight):
        """Convert a flight record into the Treeview column order."""
        return tuple(
            str(flight.get(field, ""))
            for field in FLIGHT_RECORD_FIELDS
        )

    def insert_flight_row(self, flight):
        """Insert one flight record into the Treeview."""
        self.flight_tree.insert(
            "",
            "end",
            values=self.flight_to_values(flight),
        )

    def clear_tree(self):
        """Remove all currently displayed rows from the flight Treeview."""
        for item in self.flight_tree.get_children():
            self.flight_tree.delete(item)

    def refresh_table(self):
        """Reload the flight table from current RecordManager data."""
        self.clear_tree()

        flights = self.rm.search_records(record_type="Flight")

        for flight in flights:
            self.insert_flight_row(flight)

    def filter_flight_table(self, *_args):
        """Filter flights by client, airline, date, origin, or destination."""
        query = self.flight_search_var.get().strip().lower()

        self.clear_tree()

        flights = self.rm.search_records(record_type="Flight")

        for flight in flights:
            values = self.flight_to_values(flight)

            if not query or any(
                query in value.lower()
                for value in values
            ):
                self.flight_tree.insert(
                    "",
                    "end",
                    values=values,
                )
