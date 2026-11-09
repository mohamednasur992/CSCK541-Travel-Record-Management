"""Client management tab for the Travel Record Management System."""

import tkinter as tk
from tkinter import messagebox, ttk

from gui.autocomplete import AutocompleteCombobox
from gui.constants import CITY_TO_NATIONALITY, WORLD_CITIES

# Explicit column labels provide clearer headings than automatically
# converting internal field names.
CLIENT_COLUMNS = {
    "client_id": "Client ID",
    "type": "Record Type",
    "full_name": "Full Name",
    "email": "Email",
    "phone_number": "Phone Number",
    "city": "City",
    "address": "Address",
    "passport_num": "Passport / ID",
    "nationality": "Nationality",
    "emergency_contact": "Emergency Contact",
}

# Field order used when displaying and filtering client records.
CLIENT_RECORD_FIELDS = (
    "id",
    "type",
    "name",
    "email",
    "phone_number",
    "city",
    "address",
    "passport_number",
    "nationality",
    "emergency_contact",
)


class ClientTab:
    """
    Manage client data entry, validation, searching, and CRUD operations.

    Client records are displayed and edited through this tab, while storage
    and record-integrity rules are delegated to the RecordManager.
    """

    def __init__(self, notebook, main_window):
        """Create the client tab and initialise its interface components."""
        self.notebook = notebook
        self.main = main_window
        self.rm = main_window.rm

        self.tab = ttk.Frame(self.notebook)
        self.notebook.add(self.tab, text=" 👥 Clients ")

        # The left-hand frame contains the client data-entry form.
        self.form_frame = ttk.LabelFrame(
            self.tab,
            text=" Client Details ",
            padding=15,
        )
        self.form_frame.pack(
            side="left",
            fill="y",
            padx=10,
            pady=10,
        )
        self.form_frame.columnconfigure(1, weight=1)

        # The right-hand frame contains search controls and the client table.
        self.display_frame = ttk.LabelFrame(
            self.tab,
            text=" Search & Record List ",
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
        """Create the client form, actions, search controls, and Treeview."""

        # Search controls filter the displayed records as the user types.
        search_frame = ttk.Frame(self.display_frame)
        search_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(
            search_frame,
            text="Search Filter:",
        ).pack(side="left", padx=(0, 5))

        self.client_search_var = tk.StringVar()
        self.client_search_var.trace_add(
            "write",
            self.filter_client_table,
        )

        search_entry = ttk.Entry(
            search_frame,
            textvariable=self.client_search_var,
            width=30,
        )
        search_entry.pack(side="left", padx=5)

        ttk.Button(
            search_frame,
            text="Clear Search",
            command=lambda: self.client_search_var.set(""),
        ).pack(side="left", padx=5)

        # Client details are captured in the left-hand form.
        ttk.Label(
            self.form_frame,
            text="Client ID:",
        ).grid(row=0, column=0, sticky="w", pady=3)

        self.client_id_entry = ttk.Entry(
            self.form_frame,
            state="readonly",
        )
        self.client_id_entry.grid(
            row=0,
            column=1,
            sticky="ew",
            pady=3,
        )

        ttk.Label(
            self.form_frame,
            text="Full Name:",
        ).grid(row=1, column=0, sticky="w", pady=3)

        self.client_name_entry = ttk.Entry(self.form_frame)
        self.client_name_entry.grid(
            row=1,
            column=1,
            sticky="ew",
            pady=3,
        )
        self.client_name_entry.bind(
            "<KeyRelease>",
            self.on_client_field_modified,
        )

        ttk.Label(
            self.form_frame,
            text="Email:",
        ).grid(row=2, column=0, sticky="w", pady=3)

        self.client_email_entry = ttk.Entry(self.form_frame)
        self.client_email_entry.grid(
            row=2,
            column=1,
            sticky="ew",
            pady=3,
        )

        ttk.Label(
            self.form_frame,
            text="Phone Number:",
        ).grid(row=3, column=0, sticky="w", pady=3)

        self.client_phone_entry = ttk.Entry(self.form_frame)
        self.client_phone_entry.grid(
            row=3,
            column=1,
            sticky="ew",
            pady=3,
        )

        ttk.Label(
            self.form_frame,
            text="City:",
        ).grid(row=4, column=0, sticky="w", pady=3)

        self.client_city_entry = AutocompleteCombobox(
            self.form_frame,
            list_of_items=WORLD_CITIES,
        )
        self.client_city_entry.grid(
            row=4,
            column=1,
            sticky="ew",
            pady=3,
        )
        self.client_city_entry.bind(
            "<<ComboboxSelected>>",
            self.on_city_selected,
        )

        ttk.Label(
            self.form_frame,
            text="Address:",
        ).grid(row=5, column=0, sticky="w", pady=3)

        self.client_address_entry = ttk.Entry(self.form_frame)
        self.client_address_entry.grid(
            row=5,
            column=1,
            sticky="ew",
            pady=3,
        )

        ttk.Label(
            self.form_frame,
            text="Passport / ID:",
        ).grid(row=6, column=0, sticky="w", pady=3)

        self.client_passport_entry = ttk.Entry(self.form_frame)
        self.client_passport_entry.grid(
            row=6,
            column=1,
            sticky="ew",
            pady=3,
        )

        ttk.Label(
            self.form_frame,
            text="Nationality:",
        ).grid(row=7, column=0, sticky="w", pady=3)

        self.client_nationality_entry = ttk.Entry(self.form_frame)
        self.client_nationality_entry.grid(
            row=7,
            column=1,
            sticky="ew",
            pady=3,
        )

        ttk.Label(
            self.form_frame,
            text="Emergency Contact:",
        ).grid(row=8, column=0, sticky="w", pady=3)

        self.client_emergency_entry = ttk.Entry(self.form_frame)
        self.client_emergency_entry.grid(
            row=8,
            column=1,
            sticky="ew",
            pady=3,
        )

        # CRUD actions operate on the current form values.
        button_frame = ttk.Frame(self.form_frame)
        button_frame.grid(
            row=10,
            column=0,
            columnspan=2,
            pady=10,
        )

        ttk.Button(
            button_frame,
            text="Add",
            command=self.on_add_client,
        ).pack(side="left", padx=2)

        ttk.Button(
            button_frame,
            text="Update",
            command=self.on_update_client,
        ).pack(side="left", padx=2)

        ttk.Button(
            button_frame,
            text="Clear",
            command=self.clear_form,
        ).pack(side="left", padx=2)

        ttk.Button(
            button_frame,
            text="Delete",
            command=self.on_delete_client,
        ).pack(side="left", padx=2)

        self.main.add_logo_to_frame(self.form_frame)

        # The Treeview provides a searchable and sortable client list.
        self.client_tree = ttk.Treeview(
            self.display_frame,
            columns=tuple(CLIENT_COLUMNS),
            show="headings",
        )

        for column, heading in CLIENT_COLUMNS.items():
            self.client_tree.heading(
                column,
                text=heading,
                command=lambda selected_column=column: (
                    self.main.sort_treeview_column(
                        self.client_tree,
                        selected_column,
                        False,
                    )
                ),
            )
            self.client_tree.column(
                column,
                width=120,
                anchor="w",
            )

        vertical_scrollbar = ttk.Scrollbar(
            self.display_frame,
            orient="vertical",
            command=self.client_tree.yview,
        )
        horizontal_scrollbar = ttk.Scrollbar(
            self.display_frame,
            orient="horizontal",
            command=self.client_tree.xview,
        )

        self.client_tree.configure(
            yscrollcommand=vertical_scrollbar.set,
            xscrollcommand=horizontal_scrollbar.set,
        )

        horizontal_scrollbar.pack(side="bottom", fill="x")
        vertical_scrollbar.pack(side="right", fill="y")
        self.client_tree.pack(
            side="left",
            fill="both",
            expand=True,
        )

        # Double-clicking a row loads that client into the editing form.
        self.client_tree.bind("<Double-1>", self.load_to_form)

        self.clear_form()

    def on_city_selected(self, _event=None):
        """Suggest a nationality based on the selected city."""
        selected_city = self.client_city_entry.get().strip()
        suggested_nationality = CITY_TO_NATIONALITY.get(selected_city)

        if not suggested_nationality:
            return

        self.client_nationality_entry.delete(0, tk.END)
        self.client_nationality_entry.insert(
            0,
            suggested_nationality,
        )

    def get_next_client_id(self):
        """Return the next available sequential client ID."""
        clients = self.rm.search_records(record_type="Client")

        # Use the highest valid numeric ID rather than relying on record order.
        valid_ids = [
            int(client["id"])
            for client in clients
            if str(client.get("id", "")).isdigit()
        ]

        return max(valid_ids, default=0) + 1

    def on_client_field_modified(self, _event=None):
        """Assign an ID when the user starts entering a new client."""

        if self.client_id_entry.get().strip():
            return

        # Keep generated IDs read-only to prevent accidental conflicts.
        self.set_client_id(self.get_next_client_id())

    def set_client_id(self, client_id):
        """Display a client ID while preserving the field's read-only state."""
        self.client_id_entry.configure(state="normal")
        self.client_id_entry.delete(0, tk.END)

        if client_id not in (None, ""):
            self.client_id_entry.insert(0, str(client_id))

        self.client_id_entry.configure(state="readonly")

    def validate_client_form(self):
        """Validate fields required to create or update a client."""

        if not self.client_name_entry.get().strip():
            messagebox.showerror(
                "Missing Information",
                "Full name is required.",
            )
            self.client_name_entry.focus_set()
            return False

        if not self.client_passport_entry.get().strip():
            messagebox.showerror(
                "Missing Information",
                "Passport or ID number is required.",
            )
            self.client_passport_entry.focus_set()
            return False

        email = self.client_email_entry.get().strip()

        # Apply a lightweight structure check without attempting to replace
        # full email-address verification.
        if email and ("@" not in email or "." not in email.rsplit("@", 1)[-1]):
            messagebox.showerror(
                "Invalid Email",
                "Enter a valid email address or leave the field blank.",
            )
            self.client_email_entry.focus_set()
            return False

        return True

    def get_form_data(self):
        """Return the current client-form values as a record dictionary."""
        client_id = self.client_id_entry.get().strip()

        if not client_id:
            raise ValueError("Client ID could not be generated.")

        return {
            "id": int(client_id),
            "type": "Client",
            "name": self.client_name_entry.get().strip(),
            "email": self.client_email_entry.get().strip(),
            "phone_number": self.client_phone_entry.get().strip(),
            "city": self.client_city_entry.get().strip(),
            "address": self.client_address_entry.get().strip(),
            "passport_number": self.client_passport_entry.get().strip(),
            "nationality": self.client_nationality_entry.get().strip(),
            "emergency_contact": self.client_emergency_entry.get().strip(),
        }

    def on_add_client(self):
        """Validate and add a new client record."""

        if not self.validate_client_form():
            return

        try:
            client = self.get_form_data()

            # Prevent accidental creation of a duplicate client identifier.
            existing_client = self.rm.get_record_by_id(
                client["id"],
                record_type="Client",
            )
            if existing_client:
                messagebox.showerror(
                    "Duplicate Client",
                    f"Client ID {client['id']} already exists.",
                )
                return

            self.rm.add_client(
                client["id"],
                client["name"],
                client["email"],
                client["phone_number"],
                client["city"],
                client["address"],
                client["passport_number"],
                client["nationality"],
                client["emergency_contact"],
            )

            self.refresh_table()
            self.clear_form()

            messagebox.showinfo(
                "Success",
                "Client added successfully.",
            )

        except (TypeError, ValueError) as error:
            messagebox.showerror(
                "Unable to Add Client",
                str(error),
            )

    def on_update_client(self):
        """Validate and update the client currently loaded in the form."""

        client_id = self.client_id_entry.get().strip()

        if not client_id:
            messagebox.showwarning(
                "No Client Selected",
                "Select a client to update.",
            )
            return

        if not self.validate_client_form():
            return

        try:
            updated_data = self.get_form_data()

            updated = self.rm.update_record(
                client_id,
                updated_data,
                record_type="Client",
            )

            if not updated:
                messagebox.showwarning(
                    "Update Failed",
                    "The selected client could not be found.",
                )
                return

            self.refresh_table()
            self.clear_form()

            messagebox.showinfo(
                "Success",
                "Client updated successfully.",
            )

        except (TypeError, ValueError) as error:
            messagebox.showerror(
                "Unable to Update Client",
                str(error),
            )

    def on_delete_client(self):
        """Delete the client selected in the Treeview."""
        selected_items = self.client_tree.selection()

        if not selected_items:
            messagebox.showwarning(
                "No Client Selected",
                "Select a client to delete.",
            )
            return

        selected_item = selected_items[0]
        values = self.client_tree.item(
            selected_item,
            "values",
        )
        client_id = values[0]

        if not messagebox.askyesno(
            "Confirm Deletion",
            f"Delete Client ID {client_id}?",
        ):
            return

        try:
            deleted = self.rm.delete_record(
                client_id,
                record_type="Client",
            )

            if not deleted:
                messagebox.showwarning(
                    "Delete Failed",
                    "The selected client could not be found.",
                )
                return

            self.refresh_table()
            self.clear_form()

            messagebox.showinfo(
                "Success",
                "Client deleted successfully.",
            )

        except ValueError as error:
            # RecordManager protects clients referenced by Flight records.
            messagebox.showerror(
                "Integrity Constraint",
                str(error),
            )

    def load_to_form(self, _event=None):
        """Load the selected client record into the form for editing."""
        selected_items = self.client_tree.selection()

        if not selected_items:
            return

        selected_item = selected_items[0]
        values = self.client_tree.item(
            selected_item,
            "values",
        )

        self.clear_form()

        # Temporarily unlock the generated ID field while loading the record.
        self.set_client_id(values[0])

        form_entries = (
            self.client_name_entry,
            self.client_email_entry,
            self.client_phone_entry,
            self.client_city_entry,
            self.client_address_entry,
            self.client_passport_entry,
            self.client_nationality_entry,
            self.client_emergency_entry,
        )

        # Values 0 and 1 contain the client ID and record type.
        for entry, value in zip(form_entries, values[2:]):
            entry.insert(0, value)

    def clear_form(self):
        """Clear all client fields and return the form to its initial state."""
        self.set_client_id("")

        form_entries = (
            self.client_name_entry,
            self.client_email_entry,
            self.client_phone_entry,
            self.client_city_entry,
            self.client_address_entry,
            self.client_passport_entry,
            self.client_nationality_entry,
            self.client_emergency_entry,
        )

        for entry in form_entries:
            entry.delete(0, tk.END)

        self.client_name_entry.focus_set()

    @staticmethod
    def client_to_values(client):
        """Convert a client record into the Treeview column order."""
        return tuple(
            str(client.get(field, ""))
            for field in CLIENT_RECORD_FIELDS
        )

    def insert_client_row(self, client):
        """Insert one client record into the Treeview."""
        self.client_tree.insert(
            "",
            "end",
            values=self.client_to_values(client),
        )

    def clear_tree(self):
        """Remove all currently displayed rows from the client Treeview."""
        for item in self.client_tree.get_children():
            self.client_tree.delete(item)

    def refresh_table(self):
        """Reload the client table from the current RecordManager data."""
        self.clear_tree()

        clients = self.rm.search_records(record_type="Client")
        for client in clients:
            self.insert_client_row(client)

        # Client changes affect the choices available when creating flights.
        self.main.refresh_flight_dropdowns()

    def filter_client_table(self, *_args):
        """Filter displayed clients against all searchable client fields."""
        query = self.client_search_var.get().strip().lower()

        self.clear_tree()

        clients = self.rm.search_records(record_type="Client")

        for client in clients:
            values = self.client_to_values(client)

            if not query or any(
                query in value.lower()
                for value in values
            ):
                self.client_tree.insert(
                    "",
                    "end",
                    values=values,
                )