"""Main graphical user interface container window for the Travel Record Management System."""
import os
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

from gui.styles import setup_styles
from gui.client_tab import ClientTab
from gui.airline_tab import AirlineTab
from gui.flight_tab import FlightTab


# pylint: disable=too-many-instance-attributes, too-many-public-methods
class MainApplicationWindow:
    """Coordinates notebook tabs, shared logo handling, status bar, and global helpers."""
    def __init__(self, root, record_manager):
        self.root = root
        self.root.title("Specialist Travel Agent Record Management System — Group B")
        self.root.geometry("1250x720")
        self.rm = record_manager

        # Apply Styles
        setup_styles(self.root)

        # Load Logo
        self.logo_image = self.load_logo()

        # Notebook (Tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Initialize Individual Tabs
        self.client_tab = ClientTab(self.notebook, self)
        self.airline_tab = AirlineTab(self.notebook, self)
        self.flight_tab = FlightTab(self.notebook, self)

        # Shared Status Bar at the Bottom
        total_records = len(self.rm.records) if hasattr(self.rm, 'records') else 0
        self.status_var = tk.StringVar(value=f"System Ready. Loaded {total_records} record(s) from storage.")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief="sunken", anchor="w", padding=(5, 2))
        self.status_bar.pack(side="bottom", fill="x")

        # Initial Load
        self.client_tab.refresh_table()

    @staticmethod
    def load_logo():
        """Safely loads and resizes the logo image."""
        try:
            logo_path = "assets/logo.png"
            if not os.path.exists(logo_path):
                logo_path = "logo.png"
            if os.path.exists(logo_path):
                pil_img = Image.open(logo_path)
                pil_img = pil_img.resize((350, 250), Image.Resampling.LANCZOS)
                return ImageTk.PhotoImage(pil_img)
        except Exception as e:
            print(f"Could not load logo image: {e}")
        return None

    def add_logo_to_frame(self, parent_frame):
        """Renders the logo image centered at the bottom of form frames."""
        if self.logo_image:
            logo_label = ttk.Label(parent_frame, image=self.logo_image, anchor="center")
            logo_label.image = self.logo_image
            logo_label.grid(row=11, column=0, columnspan=2, pady=(15, 0))

    def get_client_dropdown_items(self):
        """Returns formatted strings for client dropdowns."""
        try:
            clients = self.rm.search_records(record_type="Client")
            return [f"{c.get('id')} - {c.get('name')}" for c in clients if c.get('id') is not None]
        except Exception:
            return []

    def get_airline_dropdown_items(self):
        """Returns formatted strings for airline dropdowns."""
        try:
            airlines = self.rm.search_records(record_type="Airline")
            return [f"{a.get('id')} - {a.get('company_name')}" for a in airlines if a.get('id') is not None]
        except Exception:
            return []

    def refresh_flight_dropdowns(self):
        """Synchronizes dropdown items across tabs."""
        if hasattr(self, 'flight_tab') and hasattr(self.flight_tab, 'flight_client_combo'):
            self.flight_tab.flight_client_combo.all_items = self.get_client_dropdown_items()
            self.flight_tab.flight_client_combo['values'] = self.flight_tab.flight_client_combo.all_items
        if hasattr(self, 'flight_tab') and hasattr(self.flight_tab, 'flight_airline_combo'):
            self.flight_tab.flight_airline_combo.all_items = self.get_airline_dropdown_items()
            self.flight_tab.flight_airline_combo['values'] = self.flight_tab.flight_airline_combo.all_items

    @staticmethod
    def sort_treeview_column(tree, col, reverse):
        """Sorts treeview columns alphabetically or numerically."""
        try:
            data_list = [(tree.set(child, col), child) for child in tree.get_children('')]
        except Exception:
            return

        try:
            data_list.sort(key=lambda x: float(x[0]) if x[0].strip() else 0, reverse=reverse)
        except ValueError:
            data_list.sort(key=lambda x: str(x[0]).lower(), reverse=reverse)

        for index, (_, child) in enumerate(data_list):
            tree.move(child, '', index)

        tree.heading(col, command=lambda: MainApplicationWindow.sort_treeview_column(tree, col, not reverse))