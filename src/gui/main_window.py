import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk  # Requires Pillow (pip install Pillow)
import os


class MainApplicationWindow:
    def __init__(self, root, record_manager):
        self.root = root
        self.root.title("Specialist Travel Agent Record Management System — Group B")
        self.root.geometry("1150x680")
        self.rm = record_manager

        # Apply Custom Theme & Colour Palette
        self.setup_styles()

        # Load Logo Image (adjust path/filename as needed)
        self.logo_image = self.load_logo()

        # Main Notebook (Tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Initialize Tabs
        self.init_client_tab()
        self.init_airline_tab()
        self.init_flight_tab()

        # Status Bar at the Bottom
        total_records = len(self.rm.records) if hasattr(self.rm, 'records') else 0
        self.status_var = tk.StringVar(value=f"System Ready. Loaded {total_records} record(s) from storage.")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief="sunken", anchor="w",
                                    padding=(5, 2))
        self.status_bar.pack(side="bottom", fill="x")

        # Load initial data
        self.refresh_client_table()

    def setup_styles(self):
        """Configures a modern deep blue and slate travel agency colour scheme."""
        style = ttk.Style()
        style.theme_use("clam")

        # Palette colors
        primary_color = "#1B365D"  # Deep Navy
        accent_color = "#007A33"  # Travel Blue / Teal accent
        bg_color = "#F4F6F9"  # Soft off-white background

        self.root.configure(bg=bg_color)

        style.configure(".", background=bg_color, font=("Segoe UI", 10))
        style.configure("TNotebook", background=bg_color, borderwidth=0)
        style.configure("TNotebook.Tab", background="#D9E2EC", foreground="#102a43", padding=[15, 8],
                        font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", primary_color)], foreground=[("selected", "#FFFFFF")])

        style.configure("TLabelFrame", background=bg_color, foreground=primary_color, font=("Segoe UI", 11, "bold"))
        style.configure("TLabel", background=bg_color, foreground="#243b53")
        style.configure("TButton", background=primary_color, foreground="#FFFFFF", font=("Segoe UI", 10, "bold"),
                        padding=6)
        style.map("TButton", background=[("active", "#243b53")])

    def load_logo(self):
        """Safely loads and resizes the logo image for the bottom left corner."""
        try:
            # Look for logo in assets folder or current directory
            logo_path = "assets/logo.png"
            if not os.path.exists(logo_path):
                logo_path = "logo.png"  # Fallback to root dir

            if os.path.exists(logo_path):
                pil_img = Image.open(logo_path)
                pil_img = pil_img.resize((400, 300), Image.Resampling.LANCZOS)
                return ImageTk.PhotoImage(pil_img)
        except Exception as e:
            print(f"Could not load logo image: {e}")
        return None

    def add_logo_to_frame(self, parent_frame):
        """Helper to render the logo image at the bottom of a form frame using grid."""
        if self.logo_image:
            logo_label = ttk.Label(parent_frame, image=self.logo_image)
            logo_label.image = self.logo_image  # Keep reference
            # Place it below the buttons using grid instead of pack
            logo_label.grid(row=11, column=0, columnspan=2, pady=(15, 0), sticky="w")

    def init_client_tab(self):
        """Builds the Client Management View tab."""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=" 👥 Clients ")

        form_frame = ttk.LabelFrame(tab, text=" Client Details ", padding=15)
        form_frame.pack(side="left", fill="y", padx=10, pady=10)

        display_frame = ttk.LabelFrame(tab, text=" Search & Record List ", padding=15)
        display_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # Search Bar
        search_frame = ttk.Frame(display_frame)
        search_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(search_frame, text="Search Filter:").pack(side="left", padx=(0, 5))
        self.client_search_var = tk.StringVar()
        self.client_search_var.trace("w", self.filter_client_table)
        search_entry = ttk.Entry(search_frame, textvariable=self.client_search_var, width=30)
        search_entry.pack(side="left", padx=5)
        ttk.Button(search_frame, text="Clear Search", command=lambda: self.client_search_var.set("")).pack(side="left",
                                                                                                           padx=5)

        # Form Fields
        ttk.Label(form_frame, text="Client ID:").grid(row=0, column=0, sticky="w", pady=5)
        self.client_id_entry = ttk.Entry(form_frame, width=25)
        self.client_id_entry.grid(row=0, column=1, pady=5)

        ttk.Label(form_frame, text="Full Name:").grid(row=1, column=0, sticky="w", pady=5)
        self.client_name_entry = ttk.Entry(form_frame, width=25)
        self.client_name_entry.grid(row=1, column=1, pady=5)

        ttk.Label(form_frame, text="City:").grid(row=2, column=0, sticky="w", pady=5)
        self.client_city_entry = ttk.Entry(form_frame, width=25)
        self.client_city_entry.grid(row=2, column=1, pady=5)

        ttk.Label(form_frame, text="Phone Number:").grid(row=3, column=0, sticky="w", pady=5)
        self.client_phone_entry = ttk.Entry(form_frame, width=25)
        self.client_phone_entry.grid(row=3, column=1, pady=5)

        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=10, column=0, columnspan=2, pady=15)

        ttk.Button(btn_frame, text="Add", command=self.on_add_client).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Update", command=self.on_update_client).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Clear", command=self._clear_client_form).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Delete", command=self.on_delete_client).pack(side="left", padx=2)

        # Place Logo at the bottom left of the form frame
        self.add_logo_to_frame(form_frame)

        # Display Table (Treeview) with Type column added
        columns = ("ID", "Type", "Name", "City", "Phone")
        self.client_tree = ttk.Treeview(display_frame, columns=columns, show="headings")
        self.client_tree.heading("ID", text="Client ID")
        self.client_tree.heading("Type", text="Type")
        self.client_tree.heading("Name", text="Full Name")
        self.client_tree.heading("City", text="City")
        self.client_tree.heading("Phone", text="Phone Number")

        self.client_tree.column("ID", width=80, anchor="center")
        self.client_tree.column("Type", width=90, anchor="center")
        self.client_tree.column("Name", width=180)
        self.client_tree.column("City", width=150)
        self.client_tree.column("Phone", width=130)

        scrollbar = ttk.Scrollbar(display_frame, orient="vertical", command=self.client_tree.yview)
        self.client_tree.configure(yscrollcommand=scrollbar.set)

        self.client_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.client_tree.bind("<Double-1>", self.load_client_to_form)

    def init_airline_tab(self):
        """Builds the Airline Management View tab."""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=" ✈️ Airlines ")

        form_frame = ttk.LabelFrame(tab, text=" Airline Details ", padding=15)
        form_frame.pack(side="left", fill="y", padx=10, pady=10)

        display_frame = ttk.LabelFrame(tab, text=" Airline List ", padding=15)
        display_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        search_frame = ttk.Frame(display_frame)
        search_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(search_frame, text="Search Filter:").pack(side="left", padx=(0, 5))
        self.airline_search_var = tk.StringVar()
        self.airline_search_var.trace("w", self.filter_airline_table)
        search_entry = ttk.Entry(search_frame, textvariable=self.airline_search_var, width=30)
        search_entry.pack(side="left", padx=5)
        ttk.Button(search_frame, text="Clear", command=lambda: self.airline_search_var.set("")).pack(side="left",
                                                                                                     padx=5)

        ttk.Label(form_frame, text="Airline ID:").grid(row=0, column=0, sticky="w", pady=5)
        self.airline_id_entry = ttk.Entry(form_frame, width=25)
        self.airline_id_entry.grid(row=0, column=1, pady=5)

        ttk.Label(form_frame, text="Company Name:").grid(row=1, column=0, sticky="w", pady=5)
        self.airline_name_entry = ttk.Entry(form_frame, width=25)
        self.airline_name_entry.grid(row=1, column=1, pady=5)

        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=10, column=0, columnspan=2, pady=15)

        ttk.Button(btn_frame, text="Add", command=self.on_add_airline).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Update", command=self.on_update_airline).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Clear", command=self._clear_airline_form).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Delete", command=self.on_delete_airline).pack(side="left", padx=2)

        self.add_logo_to_frame(form_frame)

        self.airline_tree = ttk.Treeview(display_frame, columns=("ID", "Type", "CompanyName"), show="headings")
        self.airline_tree.heading("ID", text="Airline ID")
        self.airline_tree.heading("Type", text="Type")
        self.airline_tree.heading("CompanyName", text="Company Name")

        self.airline_tree.column("ID", width=90, anchor="center")
        self.airline_tree.column("Type", width=100, anchor="center")
        self.airline_tree.column("CompanyName", width=250)

        scrollbar = ttk.Scrollbar(display_frame, orient="vertical", command=self.airline_tree.yview)
        self.airline_tree.configure(yscrollcommand=scrollbar.set)

        self.airline_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.airline_tree.bind("<Double-1>", self.load_airline_to_form)
        self.refresh_airline_table()

    def init_flight_tab(self):
        """Builds the Flight Booking Management View tab."""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=" 🎫 Flights ")

        form_frame = ttk.LabelFrame(tab, text=" Flight Booking Details ", padding=15)
        form_frame.pack(side="left", fill="y", padx=10, pady=10)

        display_frame = ttk.LabelFrame(tab, text=" Flight Schedule List ", padding=15)
        display_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        search_frame = ttk.Frame(display_frame)
        search_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(search_frame, text="Search Filter:").pack(side="left", padx=(0, 5))
        self.flight_search_var = tk.StringVar()
        self.flight_search_var.trace("w", self.filter_flight_table)
        search_entry = ttk.Entry(search_frame, textvariable=self.flight_search_var, width=30)
        search_entry.pack(side="left", padx=5)
        ttk.Button(search_frame, text="Clear", command=lambda: self.flight_search_var.set("")).pack(side="left", padx=5)

        ttk.Label(form_frame, text="Client ID:").grid(row=0, column=0, sticky="w", pady=5)
        self.flight_client_id_entry = ttk.Entry(form_frame, width=25)
        self.flight_client_id_entry.grid(row=0, column=1, pady=5)

        ttk.Label(form_frame, text="Airline ID:").grid(row=1, column=0, sticky="w", pady=5)
        self.flight_airline_id_entry = ttk.Entry(form_frame, width=25)
        self.flight_airline_id_entry.grid(row=1, column=1, pady=5)

        ttk.Label(form_frame, text="Date (YYYY-MM-DD):").grid(row=2, column=0, sticky="w", pady=5)
        self.flight_date_entry = ttk.Entry(form_frame, width=25)
        self.flight_date_entry.grid(row=2, column=1, pady=5)

        ttk.Label(form_frame, text="Start City:").grid(row=3, column=0, sticky="w", pady=5)
        self.flight_start_entry = ttk.Entry(form_frame, width=25)
        self.flight_start_entry.grid(row=3, column=1, pady=5)

        ttk.Label(form_frame, text="End City:").grid(row=4, column=0, sticky="w", pady=5)
        self.flight_end_entry = ttk.Entry(form_frame, width=25)
        self.flight_end_entry.grid(row=4, column=1, pady=5)

        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=10, column=0, columnspan=2, pady=15)

        ttk.Button(btn_frame, text="Book", command=self.on_add_flight).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Update", command=self.on_update_flight).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Clear", command=self.clear_flight_form).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Delete", command=self.on_delete_flight).pack(side="left", padx=2)

        self.add_logo_to_frame(form_frame)

        self.flight_tree = ttk.Treeview(display_frame, columns=("Client", "Airline", "Date", "Start", "End"),
                                        show="headings")
        self.flight_tree.heading("Client", text="Client ID")
        self.flight_tree.heading("Airline", text="Airline ID")
        self.flight_tree.heading("Date", text="Date")
        self.flight_tree.heading("Start", text="Start City")
        self.flight_tree.heading("End", text="End City")

        # Explicit column widths so every column is fully visible
        self.flight_tree.column("Client", width=90, anchor="center")
        self.flight_tree.column("Airline", width=90, anchor="center")
        self.flight_tree.column("Date", width=110, anchor="center")
        self.flight_tree.column("Start", width=130)
        self.flight_tree.column("End", width=130)

        self.flight_tree.pack(side="left", fill="both", expand=True)
        # Bind double-click to load record into form
        self.flight_tree.bind("<Double-1>", self.load_flight_to_form)
        self.refresh_flight_table()

    # --- Filtering Methods ---
    def filter_client_table(self, *args):
        query = self.client_search_var.get().strip().lower()
        for item in self.client_tree.get_children():
            self.client_tree.delete(item)

        for c in self.rm.search_records(record_type="Client"):
            c_id = str(c.get("id", ""))
            name = str(c.get("name", ""))
            city = str(c.get("city", ""))
            phone = str(c.get("phone_number", ""))

            if query in c_id.lower() or query in name.lower() or query in city.lower() or query in phone.lower():
                self.client_tree.insert("", "end", values=(c_id, name, city, phone))

    def filter_airline_table(self, *args):
        query = self.airline_search_var.get().strip().lower()
        for item in self.airline_tree.get_children():
            self.airline_tree.delete(item)

        for a in self.rm.search_records(record_type="Airline"):
            a_id = str(a.get("id", ""))
            name = str(a.get("company_name", ""))
            if query in a_id.lower() or query in name.lower():
                self.airline_tree.insert("", "end", values=(a_id, name))

    def filter_flight_table(self, *args):
        query = self.flight_search_var.get().strip().lower()
        for item in self.flight_tree.get_children():
            self.flight_tree.delete(item)

        for f in self.rm.search_records(record_type="Flight"):
            c_id = str(f.get("client_id", ""))
            a_id = str(f.get("airline_id", ""))
            date = str(f.get("date", ""))
            start = str(f.get("start_city", ""))
            end = str(f.get("end_city", ""))

            if query in c_id.lower() or query in a_id.lower() or query in date.lower() or query in start.lower() or query in end.lower():
                self.flight_tree.insert("", "end", values=(c_id, a_id, date, start, end))

    # --- Load & Update Handlers ---
    def load_client_to_form(self, event):
        selected_item = self.client_tree.selection()
        if not selected_item:
            return
        row_values = self.client_tree.item(selected_item, "values")
        self._clear_client_form()
        self.client_id_entry.insert(0, row_values[0])  # ID
        self.client_id_entry.config(state="readonly")
        self.client_name_entry.insert(0, row_values[2])  # Name (shifted from 1 to 2)
        self.client_city_entry.insert(0, row_values[3])  # City (shifted from 2 to 3)
        self.client_phone_entry.insert(0, row_values[4])  # Phone (shifted from 3 to 4)

    def load_airline_to_form(self, event):
        selected_item = self.airline_tree.selection()
        if not selected_item:
            return
        row_values = self.airline_tree.item(selected_item, "values")
        self._clear_airline_form()
        self.airline_id_entry.insert(0, row_values[0])  # ID
        self.airline_id_entry.config(state="readonly")
        self.airline_name_entry.insert(0, row_values[2])  # Company Name (shifted to 2)

    def load_flight_to_form(self, event):
        """Loads selected flight row data into form entries for editing."""
        selected_item = self.flight_tree.selection()
        if not selected_item:
            return
        row_values = self.flight_tree.item(selected_item, "values")
        self.clear_flight_form()

        self.flight_client_id_entry.insert(0, row_values[0])
        self.flight_client_id_entry.config(state="readonly")  # Lock client/airline identifiers during update
        self.flight_airline_id_entry.insert(0, row_values[1])
        self.flight_airline_id_entry.config(state="readonly")

        self.flight_date_entry.insert(0, row_values[2])
        self.flight_start_entry.insert(0, row_values[3])
        self.flight_end_entry.insert(0, row_values[4])

    def on_update_flight(self):
        """Saves modifications made to an existing flight booking."""
        c_id = self.flight_client_id_entry.get().strip()
        a_id = self.flight_airline_id_entry.get().strip()
        date_str = self.flight_date_entry.get().strip()
        start = self.flight_start_entry.get().strip()
        end = self.flight_end_entry.get().strip()

        if not c_id or not a_id or not date_str or not start or not end:
            messagebox.showwarning("Validation Error", "All fields must be filled to update.")
            return

        updated_data = {
            "client_id": int(c_id) if c_id.isdigit() else c_id,
            "airline_id": int(a_id) if a_id.isdigit() else a_id,
            "date": date_str,
            "start_city": start,
            "end_city": end,
            "type": "Flight"
        }

        try:
            if hasattr(self.rm, 'update_record'):
                # Updates the record matching the client and airline pair
                self.rm.update_record(c_id, updated_data, record_type="Flight")

            self.clear_flight_form()
            self.refresh_flight_table()
            self.status_var.set("Successfully updated flight booking.")
            messagebox.showinfo("Success", "Flight booking updated successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Could not update flight: {e}")

    def clear_flight_form(self):
        """Clears the flight form and ensures ID entries are editable again."""
        self.flight_client_id_entry.config(state="normal")
        self.flight_airline_id_entry.config(state="normal")
        self.flight_client_id_entry.delete(0, tk.END)
        self.flight_airline_id_entry.delete(0, tk.END)
        self.flight_date_entry.delete(0, tk.END)
        self.flight_start_entry.delete(0, tk.END)
        self.flight_end_entry.delete(0, tk.END)

    def on_update_client(self):
        c_id = self.client_id_entry.get().strip()
        name = self.client_name_entry.get().strip()
        city = self.client_city_entry.get().strip()
        phone = self.client_phone_entry.get().strip()

        if not c_id or not name or not city or not phone:
            messagebox.showwarning("Validation Error", "All fields must be filled to update.")
            return

        updated_data = {
            "id": int(c_id) if c_id.isdigit() else c_id,
            "name": name,
            "city": city,
            "phone_number": phone
        }

        try:
            if hasattr(self.rm, 'update_record'):
                self.rm.update_record(c_id, updated_data, record_type="Client")

            self.client_id_entry.config(state="normal")
            self.refresh_client_table()
            self._clear_client_form()
            self.status_var.set(f"Successfully updated client ID: {c_id}")
            messagebox.showinfo("Success", "Client record updated successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Could not update client: {e}")

    def on_update_airline(self):
        a_id = self.airline_id_entry.get().strip()
        name = self.airline_name_entry.get().strip()

        if not a_id or not name:
            messagebox.showwarning("Validation Error", "All fields must be filled to update.")
            return

        updated_data = {
            "id": int(a_id) if a_id.isdigit() else a_id,
            "company_name": name
        }

        try:
            if hasattr(self.rm, 'update_record'):
                self.rm.update_record(a_id, updated_data, record_type="Airline")

            self.airline_id_entry.config(state="normal")
            self.refresh_airline_table()
            self._clear_airline_form()
            self.status_var.set(f"Successfully updated airline ID: {a_id}")
            messagebox.showinfo("Success", "Airline record updated successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Could not update airline: {e}")

    # --- Add Handlers ---
    def on_add_client(self):
        try:
            c_id = int(self.client_id_entry.get().strip())
            name = self.client_name_entry.get().strip()
            city = self.client_city_entry.get().strip()
            phone = self.client_phone_entry.get().strip()

            if not name or not city or not phone:
                messagebox.showerror("Validation Error", "All fields must be filled.")
                return

            existing_clients = self.rm.search_records(record_type="Client")
            for c in existing_clients:
                if int(c.get("id")) == c_id:
                    messagebox.showerror("Duplicate Record Error", f"A client with ID '{c_id}' already exists!")
                    return

            self.rm.add_client(c_id, name, "", "", "", city, "", "", "", phone)
            self.refresh_client_table()
            self.status_var.set(f"Successfully added client: {name}")
            messagebox.showinfo("Success", "Client added successfully!")
            self._clear_client_form()
        except ValueError:
            messagebox.showerror("Invalid Input", "Client ID must be a valid integer.")

    def on_add_airline(self):
        try:
            a_id = int(self.airline_id_entry.get().strip())
            name = self.airline_name_entry.get().strip()
            if not name:
                messagebox.showerror("Validation Error", "Company name cannot be empty.")
                return
            self.rm.add_airline(a_id, name)
            self.refresh_airline_table()
            self.status_var.set(f"Successfully added airline: {name}")
            messagebox.showinfo("Success", "Airline added successfully!")
            self._clear_airline_form()
        except ValueError:
            messagebox.showerror("Invalid Input", "Airline ID must be a valid integer.")

    def on_add_flight(self):
        try:
            c_id = int(self.flight_client_id_entry.get().strip())
            a_id = int(self.flight_airline_id_entry.get().strip())
            date_str = self.flight_date_entry.get().strip()
            start = self.flight_start_entry.get().strip()
            end = self.flight_end_entry.get().strip()

            if not start or not end or not date_str:
                messagebox.showerror("Validation Error", "All flight fields must be filled.")
                return

            self.rm.add_flight(c_id, a_id, date_str, start, end)
            self.refresh_flight_table()
            self.status_var.set(f"Successfully booked flight from {start} to {end}")
            messagebox.showinfo("Success", "Flight booking created successfully!")
            self.clear_flight_form()
        except ValueError:
            messagebox.showerror("Invalid Input", "Client ID and Airline ID must be valid integers.")

    # --- Delete Handlers ---
    def on_delete_client(self):
        selected_item = self.client_tree.selection()
        if not selected_item:
            messagebox.showwarning("Selection Error", "Please select a client to delete.")
            return

        row_values = self.client_tree.item(selected_item, "values")
        client_id = row_values[0]
        client_name = row_values[1]

        if messagebox.askyesno("Confirm Deletion", f"Delete client '{client_name}' (ID: {client_id})?"):
            try:
                self.rm.delete_record(client_id, record_type="Client")
                self.refresh_client_table()
                self.status_var.set(f"Successfully deleted client: {client_name}")
                messagebox.showinfo("Deleted", f"Client '{client_name}' has been removed.")
            except ValueError as e:
                messagebox.showerror("Integrity Constraint Violation", str(e))

    def on_delete_airline(self):
        selected_item = self.airline_tree.selection()
        if not selected_item:
            messagebox.showwarning("Selection Error", "Please select an airline to delete.")
            return

        row_values = self.airline_tree.item(selected_item, "values")
        airline_id = row_values[0]
        airline_name = row_values[1]

        if messagebox.askyesno("Confirm Deletion", f"Delete airline '{airline_name}' (ID: {airline_id})?"):
            try:
                self.rm.delete_record(airline_id, record_type="Airline")
                self.refresh_airline_table()
                self.status_var.set(f"Successfully deleted airline: {airline_name}")
                messagebox.showinfo("Deleted", f"Airline '{airline_name}' has been removed.")
            except ValueError as e:
                messagebox.showerror("Integrity Constraint Violation", str(e))

    def on_delete_flight(self):
        selected_item = self.flight_tree.selection()
        if not selected_item:
            messagebox.showwarning("Selection Error", "Please select a flight to delete.")
            return

        row_values = self.flight_tree.item(selected_item, "values")
        client_id = row_values[0]
        date = row_values[2]
        start = row_values[3]
        end = row_values[4]

        if messagebox.askyesno("Confirm Deletion", f"Delete flight from {start} to {end} on {date}?"):
            try:
                self.rm.delete_record(client_id, record_type="Flight")
                self.refresh_flight_table()
                self.status_var.set("Successfully deleted flight booking.")
                messagebox.showinfo("Deleted", "Flight booking has been removed.")
            except Exception as e:
                messagebox.showerror("Error", f"Could not delete flight: {e}")

    # --- Table Refresh Methods ---
    def refresh_client_table(self):
        for item in self.client_tree.get_children():
            self.client_tree.delete(item)
        for c in self.rm.search_records(record_type="Client"):
            self.client_tree.insert("", "end", values=(
                c.get("id"),
                c.get("type", "Client"),
                c.get("name"),
                c.get("city"),
                c.get("phone_number")
            ))

    def refresh_airline_table(self):
        for item in self.airline_tree.get_children():
            self.airline_tree.delete(item)
        for a in self.rm.search_records(record_type="Airline"):
            self.airline_tree.insert("", "end", values=(
                a.get("id"),
                a.get("type", "Airline"),
                a.get("company_name")
            ))

    def refresh_flight_table(self):
        for item in self.flight_tree.get_children():
            self.flight_tree.delete(item)
        for f in self.rm.search_records(record_type="Flight"):
            self.flight_tree.insert("", "end",
                                    values=(f.get("client_id"), f.get("airline_id"), f.get("date"), f.get("start_city"),
                                            f.get("end_city")))

    # --- Form Clear Utilities ---
    def _clear_client_form(self):
        self.client_id_entry.config(state="normal")
        self.client_id_entry.delete(0, tk.END)
        self.client_name_entry.delete(0, tk.END)
        self.client_city_entry.delete(0, tk.END)
        self.client_phone_entry.delete(0, tk.END)

    def _clear_airline_form(self):
        self.airline_id_entry.config(state="normal")
        self.airline_id_entry.delete(0, tk.END)
        self.airline_name_entry.delete(0, tk.END)

    def clear_flight_form(self):
        self.flight_client_id_entry.delete(0, tk.END)
        self.flight_airline_id_entry.delete(0, tk.END)
        self.flight_date_entry.delete(0, tk.END)
        self.flight_start_entry.delete(0, tk.END)
        self.flight_end_entry.delete(0, tk.END)