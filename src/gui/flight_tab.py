"""Flight booking tab for the Travel Record Management System."""

import tkinter as tk
from tkinter import messagebox, ttk

from tkcalendar import DateEntry

# pylint: disable=import-error, too-many-branches, too-many-locals
# pylint: disable=line-too-long, attribute-defined-outside-init
from gui.autocomplete import AutocompleteCombobox
from gui.constants import WORLD_CITIES

# IDs remain in each row for safe update/delete operations, but only the
# user-friendly names and booking details are displayed in the Treeview.
FLIGHT_COLUMNS = (
    "client_id",
    "airline_id",
    "client_name",
    "airline_name",
    "date",
    "start_city",
    "end_city",
)
FLIGHT_DISPLAY_COLUMNS = (
    "client_name",
    "airline_name",
    "date",
    "start_city",
    "end_city",
)
FLIGHT_HEADINGS = {
    "client_name": "Client",
    "airline_name": "Airline",
    "date": "Travel Date",
    "start_city": "Start City",
    "end_city": "Destination",
}

# Subtle alternating row colours improve readability across wide flight records.
TABLE_ROW_EVEN = "#FFFFFF"
TABLE_ROW_ODD = "#F3F7FA"

class FlightTab:  # pylint: disable=too-many-instance-attributes
    """Manage flight booking, searching, display, and CRUD operations."""

    def __init__(self, notebook, main_window):
        self.notebook = notebook
        self.main = main_window
        self.rm = main_window.rm
        self.original_flight_key = None

        self.tab = ttk.Frame(self.notebook)
        self.notebook.add(self.tab, text=" 🎫 Flights ")

        self.form_frame = ttk.LabelFrame(
            self.tab,
            text=" Flight Booking Details ",
            padding=15,
        )
        self.form_frame.pack(side="left", fill="y", padx=10, pady=10)
        self.form_frame.columnconfigure(1, weight=1)

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

        # Widget references initialised for linter compliance
        self.flight_search_var = None
        self.flight_client_combo = None
        self.flight_airline_combo = None
        self.flight_date_entry = None
        self.flight_start_entry = None
        self.flight_end_entry = None
        self.flight_tree = None

        self.init_widgets()

    def init_widgets(self):
        """Create the booking form, actions, search controls, and table."""
        search_frame = ttk.Frame(self.display_frame)
        search_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(search_frame, text="Search Filter:").pack(
            side="left", padx=(0, 5)
        )

        self.flight_search_var = tk.StringVar()
        self.flight_search_var.trace_add("write", self.filter_flight_table)
        ttk.Entry(
            search_frame,
            textvariable=self.flight_search_var,
            width=30,
        ).pack(side="left", padx=5)
        ttk.Button(
            search_frame,
            text="Clear Search",
            command=lambda: self.flight_search_var.set(""),
        ).pack(side="left", padx=5)

        ttk.Label(self.form_frame, text="Client:").grid(
            row=0, column=0, sticky="w", pady=5
        )
        self.flight_client_combo = AutocompleteCombobox(
            self.form_frame,
            list_of_items=self.main.get_client_dropdown_items(),
        )
        self.flight_client_combo.grid(row=0, column=1, sticky="ew", pady=5)

        ttk.Label(self.form_frame, text="Airline:").grid(
            row=1, column=0, sticky="w", pady=5
        )
        self.flight_airline_combo = AutocompleteCombobox(
            self.form_frame,
            list_of_items=self.main.get_airline_dropdown_items(),
        )
        self.flight_airline_combo.grid(row=1, column=1, sticky="ew", pady=5)

        ttk.Label(self.form_frame, text="Travel Date:").grid(
            row=2, column=0, sticky="w", pady=5
        )
        self.flight_date_entry = DateEntry(
            self.form_frame,
            background="darkblue",
            foreground="white",
            date_pattern="yyyy-mm-dd",
        )
        self.flight_date_entry.grid(row=2, column=1, sticky="ew", pady=5)
        self.flight_date_entry.delete(0, tk.END)

        ttk.Label(self.form_frame, text="Start City:").grid(
            row=3, column=0, sticky="w", pady=5
        )
        self.flight_start_entry = AutocompleteCombobox(
            self.form_frame,
            list_of_items=WORLD_CITIES,
        )
        self.flight_start_entry.grid(row=3, column=1, sticky="ew", pady=5)

        ttk.Label(self.form_frame, text="Destination:").grid(
            row=4, column=0, sticky="w", pady=5
        )
        self.flight_end_entry = AutocompleteCombobox(
            self.form_frame,
            list_of_items=WORLD_CITIES,
        )
        self.flight_end_entry.grid(row=4, column=1, sticky="ew", pady=5)

        button_frame = ttk.Frame(self.form_frame)
        button_frame.grid(row=10, column=0, columnspan=2, pady=15)
        ttk.Button(
            button_frame, text="Book", command=self.on_add_flight
        ).pack(side="left", padx=2)
        ttk.Button(
            button_frame, text="Update", command=self.on_update_flight
        ).pack(side="left", padx=2)
        ttk.Button(
            button_frame, text="Clear", command=self.clear_form
        ).pack(side="left", padx=2)
        ttk.Button(
            button_frame,
            text="Delete",
            style="Danger.TButton",
            command=self.on_delete_flight,
        ).pack(side="left", padx=2)

        self.main.add_logo_to_frame(self.form_frame)

        self.flight_tree = ttk.Treeview(
            self.display_frame,
            columns=FLIGHT_COLUMNS,
            displaycolumns=FLIGHT_DISPLAY_COLUMNS,
            show="headings",
        )

        # Apply consistent zebra-striping to the flight schedule.
        self.flight_tree.tag_configure(
            "even_row",
            background=TABLE_ROW_EVEN,
        )

        self.flight_tree.tag_configure(
            "odd_row",
            background=TABLE_ROW_ODD,
        )
        widths = {
            "client_name": 160,
            "airline_name": 180,
            "date": 110,
            "start_city": 135,
            "end_city": 135,
        }
        for column in FLIGHT_DISPLAY_COLUMNS:
            self.flight_tree.heading(
                column,
                text=FLIGHT_HEADINGS[column],
                command=lambda selected_column=column: (
                    self.main.sort_treeview_column(
                        self.flight_tree, selected_column, False
                    )
                ),
            )
            self.flight_tree.column(
                column,
                width=widths[column],
                minwidth=90,
                anchor=(
                    "w"
                    if column in {
                        "client_name",
                        "airline_name",
                        "start_city",
                        "end_city",
                    }
                    else "center"
                ),
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
        horizontal_scrollbar.pack(side="bottom", fill="x")
        vertical_scrollbar.pack(side="right", fill="y")
        self.flight_tree.pack(side="left", fill="both", expand=True)
        self.flight_tree.bind("<Double-1>", self.load_to_form)

        self.refresh_table()
        self.clear_form(report_status=False)

    @staticmethod
    def extract_id_from_selection(selection_str):
        """Extract an integer ID from an ``ID - display name`` value."""
        if not selection_str:
            return None
        selection = str(selection_str).strip()
        if selection.isdigit():
            return int(selection)
        identifier = selection.split(" - ", maxsplit=1)[0].strip()
        return int(identifier) if identifier.isdigit() else None

    def refresh_dropdowns(self):
        """Refresh client and airline choices from current stored records."""
        client_items = sorted(self.main.get_client_dropdown_items())
        airline_items = sorted(self.main.get_airline_dropdown_items())
        self.flight_client_combo.all_items = client_items
        self.flight_client_combo["values"] = client_items
        self.flight_airline_combo.all_items = airline_items
        self.flight_airline_combo["values"] = airline_items

    def validate_flight_form(self):
        """Validate all values required to create or update a booking."""
        client_id = self.extract_id_from_selection(self.flight_client_combo.get())
        airline_id = self.extract_id_from_selection(self.flight_airline_combo.get())
        travel_date = self.flight_date_entry.get().strip()
        start_city = self.flight_start_entry.get().strip()
        end_city = self.flight_end_entry.get().strip()

        checks = (
            (client_id is None, "Invalid Client", "Select a valid client.", self.flight_client_combo),
            (airline_id is None, "Invalid Airline", "Select a valid airline.", self.flight_airline_combo),
            (not travel_date, "Missing Information", "Travel date is required.", self.flight_date_entry),
            (not start_city, "Missing Information", "Start city is required.", self.flight_start_entry),
            (not end_city, "Missing Information", "Destination is required.", self.flight_end_entry),
        )
        for failed, title, message, widget in checks:
            if failed:
                self.main.update_status(message)
                messagebox.showerror(title, message)
                widget.focus_set()
                return False

        if self.rm.get_record_by_id(client_id, record_type="Client") is None:
            message = "The selected client no longer exists."
            self.main.update_status(message)
            messagebox.showerror("Client Not Found", message)
            return False
        if self.rm.get_record_by_id(airline_id, record_type="Airline") is None:
            message = "The selected airline no longer exists."
            self.main.update_status(message)
            messagebox.showerror("Airline Not Found", message)
            return False
        if start_city.casefold() == end_city.casefold():
            message = "Start city and destination must be different."
            self.main.update_status(message)
            messagebox.showerror("Invalid Route", message)
            return False
        return True

    def get_form_data(self):
        """Return the current form values as a Flight record dictionary."""
        return {
            "type": "Flight",
            "client_id": self.extract_id_from_selection(self.flight_client_combo.get()),
            "airline_id": self.extract_id_from_selection(self.flight_airline_combo.get()),
            "date": self.flight_date_entry.get().strip(),
            "start_city": self.flight_start_entry.get().strip(),
            "end_city": self.flight_end_entry.get().strip(),
        }

    @staticmethod
    def _flight_identity(flight):
        """Return a normalised identity for one stored flight record."""
        return (
            str(flight.get("client_id", "")).strip(),
            str(flight.get("airline_id", "")).strip(),
            str(flight.get("date", "")).strip(),
            str(flight.get("start_city", "")).strip().casefold(),
            str(flight.get("end_city", "")).strip().casefold(),
        )

    @staticmethod
    def _same_client_and_date(flight, client_id, travel_date):
        """Return whether a flight belongs to one client's dated journey."""
        return (
            str(flight.get("client_id", "")).strip() == client_id
            and str(flight.get("date", "")).strip() == travel_date
        )

    @staticmethod
    def _validate_linear_journey(journey):
        """Return a conflict message when flights do not form one linear path."""
        seen_flights = set()
        used_start_cities = set()

        for index, flight in enumerate(journey):
            identity = FlightTab._flight_identity(flight)
            start_city = str(flight.get("start_city", "")).strip()
            normalized_start = start_city.casefold()

            if identity in seen_flights:
                return "An identical flight booking already exists."
            seen_flights.add(identity)

            if normalized_start in used_start_cities:
                return (
                    f"A flight already departs from {start_city} in this client's "
                    "journey on that date. Each reached city may be used as a "
                    "Start City only once."
                )

            if index:
                previous_destination = str(
                    journey[index - 1].get("end_city", "")
                ).strip()
                if normalized_start != previous_destination.casefold():
                    return (
                        f"The next flight must start from {previous_destination}, "
                        "the destination of the latest valid connection."
                    )

            used_start_cities.add(normalized_start)

        return None

    def booking_conflict_message(self, flight_data, exclude_original=False):
        """Return why a booking breaks the client's linear same-day journey.

        Stored record order defines the journey order because departure and
        arrival times are not captured. New bookings are appended as the latest
        leg. During an update, the candidate replaces the original leg in place.
        """
        candidate_client = str(flight_data.get("client_id", "")).strip()
        candidate_date = str(flight_data.get("date", "")).strip()
        original_identity = None
        if exclude_original and self.original_flight_key:
            original_identity = self._flight_identity(self.original_flight_key)

        records = self.rm.search_records(record_type="Flight")
        journey = []
        original_replaced = False
        candidate_inserted = False

        for record in records:
            is_original = (
                original_identity is not None
                and not original_replaced
                and self._flight_identity(record) == original_identity
            )
            if is_original:
                original_replaced = True
                if self._same_client_and_date(
                    record, candidate_client, candidate_date
                ):
                    journey.append(flight_data)
                    candidate_inserted = True
                continue

            if self._same_client_and_date(
                record, candidate_client, candidate_date
            ):
                journey.append(record)

        if not candidate_inserted:
            journey.append(flight_data)

        conflict = self._validate_linear_journey(journey)
        if conflict:
            return conflict

        # If an update moves a middle leg to another client/date, ensure that
        # removing it does not leave its original journey disconnected.
        if exclude_original and self.original_flight_key:
            original_client = str(
                self.original_flight_key.get("client_id", "")
            ).strip()
            original_date = str(
                self.original_flight_key.get("date", "")
            ).strip()
            moved_to_another_journey = (
                original_client != candidate_client
                or original_date != candidate_date
            )
            if moved_to_another_journey:
                remaining_journey = []
                original_removed = False
                for record in records:
                    if (
                        not original_removed
                        and self._flight_identity(record) == original_identity
                    ):
                        original_removed = True
                        continue
                    if self._same_client_and_date(
                        record, original_client, original_date
                    ):
                        remaining_journey.append(record)

                conflict = self._validate_linear_journey(remaining_journey)
                if conflict:
                    return (
                        "Updating this flight would break the remaining "
                        f"same-day journey. {conflict}"
                    )

        return None

    def has_booking_date_conflict(self, flight_data, exclude_original=False):
        """Return True when a booking breaks the linear same-day journey."""
        return self.booking_conflict_message(
            flight_data, exclude_original=exclude_original
        ) is not None

    def on_add_flight(self):
        """Validate and create a flight booking."""
        if not self.validate_flight_form():
            return
        try:
            flight = self.get_form_data()
            message = self.booking_conflict_message(flight)
            if message:
                self.main.update_status(message)
                messagebox.showerror("Travel Date Conflict", message)
                return
            self.rm.add_flight(
                flight["client_id"],
                flight["airline_id"],
                flight["date"],
                flight["start_city"],
                flight["end_city"],
            )
            self.refresh_table()
            start_city = flight["start_city"]
            end_city = flight["end_city"]
            travel_date = flight["date"]
            self.clear_form(report_status=False)
            self.main.update_status(
                f"Flight {start_city} → {end_city} booked for {travel_date}."
            )

        except (TypeError, ValueError) as error:
            self.main.update_status(f"Flight booking failed: {error}")
            messagebox.showerror("Unable to Book Flight", str(error))

    def on_update_flight(self):
        """Validate and update the flight loaded in the form."""
        if not self.original_flight_key:
            message = "Double-click a flight to load it for editing."
            self.main.update_status(message)
            messagebox.showwarning("No Flight Selected", message)
            return
        if not self.validate_flight_form():
            return
        try:
            updated_data = self.get_form_data()
            message = self.booking_conflict_message(
                updated_data, exclude_original=True
            )
            if message:
                self.main.update_status(message)
                messagebox.showerror("Travel Date Conflict", message)
                return
            original = self.original_flight_key
            updated = self.rm.update_record(
                original["client_id"],
                updated_data,
                record_type="Flight",
                old_airline_id=original["airline_id"],
                old_date=original["date"],
                old_start=original["start_city"],
                old_end=original["end_city"],
            )
            if not updated:
                message = "The selected flight could not be found."
                self.main.update_status(message)
                messagebox.showwarning("Update Failed", message)
                return
            self.refresh_table()
            self.clear_form(report_status=False)

            self.main.update_status(
                f"Flight {updated_data['start_city']} → "
                f"{updated_data['end_city']} updated successfully."
            )

        except (TypeError, ValueError) as error:
            self.main.update_status(f"Flight update failed: {error}")
            messagebox.showerror("Unable to Update Flight", str(error))

    def deletion_conflict_message(self, selected_flight):
        """Return a message if deleting a flight breaks its remaining journey."""
        client_id = str(selected_flight["client_id"]).strip()
        travel_date = str(selected_flight["date"]).strip()
        selected_identity = self._flight_identity(selected_flight)

        remaining_journey = []
        selected_removed = False

        for record in self.rm.search_records(record_type="Flight"):
            if (
                    not selected_removed
                    and self._flight_identity(record) == selected_identity
            ):
                selected_removed = True
                continue

            if self._same_client_and_date(
                    record,
                    client_id,
                    travel_date,
            ):
                remaining_journey.append(record)

        conflict = self._validate_linear_journey(remaining_journey)

        if conflict:
            return (
                "This flight cannot be deleted because doing so would break "
                f"the client's remaining same-day journey. {conflict}"
            )

        return None

    def on_delete_flight(self):
        """Delete the selected flight using its hidden stored identifiers."""
        selected_items = self.flight_tree.selection()
        if not selected_items:
            message = "Select a flight to delete."
            self.main.update_status(message)
            messagebox.showwarning("No Flight Selected", message)
            return

        values = self.flight_tree.item(selected_items[0], "values")
        client_id, airline_id = values[0], values[1]
        travel_date, start_city, end_city = values[4], values[5], values[6]
        if not messagebox.askyesno(
            "Confirm Deletion",
            f"Delete the flight from {start_city} to {end_city} on {travel_date}?",
        ):
            self.main.update_status("Flight deletion cancelled.")
            return
        try:
            deleted = self.rm.delete_record(
                client_id,
                record_type="Flight",
                airline_id=airline_id,
                date=travel_date,
                start_city=start_city,
                end_city=end_city,
            )
            if not deleted:
                message = "The selected flight could not be found."
                self.main.update_status(message)
                messagebox.showwarning("Delete Failed", message)
                return

            selected_flight = {
                "client_id": client_id,
                "airline_id": airline_id,
                "date": travel_date,
                "start_city": start_city,
                "end_city": end_city,
            }

            conflict_message = self.deletion_conflict_message(selected_flight)

            if conflict_message:
                self.main.update_status(
                    "Deletion blocked: the remaining journey would be disconnected."
                )
                messagebox.showerror(
                    "Journey Integrity",
                    conflict_message,
                )
                return

            self.refresh_table()
            self.clear_form(report_status=False)

            self.main.update_status(
                f"Flight {start_city} → {end_city} deleted successfully."
            )

        except (TypeError, ValueError) as error:
            self.main.update_status(f"Flight deletion failed: {error}")
            messagebox.showerror("Unable to Delete Flight", str(error))

    def load_to_form(self, _event=None):
        """Load the selected row while restoring ID-based dropdown values."""
        selected_items = self.flight_tree.selection()
        if not selected_items:
            return
        values = self.flight_tree.item(selected_items[0], "values")
        self.clear_form(report_status=False)
        self.original_flight_key = {
            "client_id": values[0],
            "airline_id": values[1],
            "date": values[4],
            "start_city": values[5],
            "end_city": values[6],
        }
        self.flight_client_combo.set(
            self.find_dropdown_value(self.main.get_client_dropdown_items(), values[0])
        )
        self.flight_airline_combo.set(
            self.find_dropdown_value(self.main.get_airline_dropdown_items(), values[1])
        )
        self.flight_date_entry.set_date(values[4])
        self.flight_start_entry.set(values[5])
        self.flight_end_entry.set(values[6])
        self.main.update_status(
            f"Loaded flight {values[5]} → {values[6]} for editing."
        )

    @staticmethod
    def find_dropdown_value(dropdown_items, record_id):
        """Return the dropdown item matching a record ID."""
        record_id = str(record_id)
        for item in dropdown_items:
            if str(item).split(" - ", maxsplit=1)[0].strip() == record_id:
                return item
        return record_id

    def clear_form(self, report_status=True):
        """Clear all booking fields and reset the editing state."""
        self.original_flight_key = None
        self.flight_client_combo.set("")
        self.flight_airline_combo.set("")
        self.flight_date_entry.delete(0, tk.END)
        self.flight_start_entry.set("")
        self.flight_end_entry.set("")
        self.flight_client_combo.focus_set()
        if report_status:
            self.main.update_status("Flight form cleared.")

    def _lookup_maps(self):
        """Build client and airline name maps used by the display table."""
        clients = {
            str(record.get("id")): str(record.get("name", ""))
            for record in self.rm.search_records(record_type="Client")
        }
        airlines = {
            str(record.get("id")): str(record.get("company_name", ""))
            for record in self.rm.search_records(record_type="Airline")
        }
        return clients, airlines

    @staticmethod
    def _flight_values(flight, clients, airlines):
        """Return hidden identifiers plus user-friendly display values."""
        client_id = str(flight.get("client_id", ""))
        airline_id = str(flight.get("airline_id", ""))
        client_name = clients.get(client_id) or f"Client ID {client_id}"
        airline_name = airlines.get(airline_id) or f"Airline ID {airline_id}"
        return (
            client_id,
            airline_id,
            client_name,
            airline_name,
            str(flight.get("date", "")),
            str(flight.get("start_city", "")),
            str(flight.get("end_city", "")),
        )

    def insert_flight_row(self, values, row_index=None):
        """Insert one flight row using alternating row colours."""
        if row_index is None:
            row_index = len(self.flight_tree.get_children())

        row_tag = (
            "even_row"
            if row_index % 2 == 0
            else "odd_row"
        )

        self.flight_tree.insert(
            "",
            "end",
            values=values,
            tags=(row_tag,),
        )

    def clear_tree(self):
        """Remove all currently displayed flight rows."""
        for item in self.flight_tree.get_children():
            self.flight_tree.delete(item)

    def refresh_table(self):
        """Reload the schedule with names resolved from stored IDs."""
        self.clear_tree()

        clients, airlines = self._lookup_maps()

        flights = self.rm.search_records(
            record_type="Flight"
        )

        for row_index, flight in enumerate(flights):
            values = self._flight_values(
                flight,
                clients,
                airlines,
            )

            self.insert_flight_row(
                values,
                row_index,
            )

    def filter_flight_table(self, *_args):
        """Filter flights by IDs, names, date, origin, or destination."""
        query = self.flight_search_var.get().strip().casefold()

        self.clear_tree()

        clients, airlines = self._lookup_maps()

        flights = self.rm.search_records(
            record_type="Flight"
        )

        matches = []

        for flight in flights:
            values = self._flight_values(
                flight,
                clients,
                airlines,
            )

            if not query or any(
                    query in str(value).casefold()
                    for value in values
            ):
                matches.append(values)

        # Recalculate the row colours for the filtered result set.
        for row_index, values in enumerate(matches):
            self.insert_flight_row(
                values,
                row_index,
            )

        if query:
            self.main.update_status(
                f"Flight search returned {len(matches)} booking(s)."
            )
        else:
            self.main.update_status(
                f"Showing {len(matches)} flight booking(s)."
            )
