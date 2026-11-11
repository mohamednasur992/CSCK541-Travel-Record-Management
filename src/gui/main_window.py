"""Main window for the Specialist Travel Agent Record Management System."""

from pathlib import Path
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

# pylint: disable=import-error, too-many-instance-attributes
from gui.airline_tab import AirlineTab
from gui.client_tab import ClientTab
from gui.flight_tab import FlightTab
from gui.styles import setup_styles

class MainApplicationWindow:
    """Coordinate the application tabs, shared lookups, branding, and status."""

    def __init__(self, root, record_manager):
        self.root = root
        self.rm = record_manager
        self.root.title("Specialist Travel Agent Record Management System — Group B")
        self.root.geometry("1250x720")
        self.root.minsize(980, 620)

        setup_styles(self.root)
        self.status_var = tk.StringVar(value="Starting application…")
        self.logo_image = self.load_logo()

        # Create the status variable before the tabs. Tab constructors may refresh
        # data immediately and can therefore report status safely during startup.
        self.status_bar = ttk.Label(
            self.root,
            textvariable=self.status_var,
            style="Status.TLabel",
            relief="sunken",
            anchor="w",
            padding=(8, 3),
        )
        self.status_bar.pack(side="bottom", fill="x")

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.client_tab = ClientTab(self.notebook, self)
        self.airline_tab = AirlineTab(self.notebook, self)
        self.flight_tab = FlightTab(self.notebook, self)

        # Populate all views after every cross-tab dependency is available.
        self.client_tab.refresh_table()
        self.airline_tab.refresh_table()
        self.flight_tab.refresh_table()

        total_records = len(getattr(self.rm, "records", ()))
        self.update_status(
            f"System ready. Loaded {total_records} record(s) from storage."
        )

        self.status_var = tk.StringVar(
            value=f"Ready. Loaded {len(self.rm.records)} record(s) from storage."
        )

        self.status_bar = ttk.Label(
            self.root,
            textvariable=self.status_var,
            anchor="w",
            style="Status.TLabel",
        )

        self.status_bar.pack(
            side="bottom",
            fill="x",
            padx=8,
            pady=(0, 5),
        )


    def update_status(self, message):
        """Show concise feedback about the most recent user or system action."""
        self.status_var.set(str(message))
        self.root.update_idletasks()

    def load_logo(self):
        """Load the application logo at roughly 70% of its previous size."""
        source_root = Path(__file__).resolve().parents[1]
        candidates = (
            source_root / "assets" / "logo.png",
            Path.cwd() / "assets" / "logo.png",
            Path.cwd() / "logo.png",
        )

        for logo_path in candidates:
            if not logo_path.exists():
                continue

            try:
                with Image.open(logo_path) as image:
                    resized = image.convert("RGBA").resize(
                        (275, 205),
                        Image.Resampling.LANCZOS,
                    )
                    return ImageTk.PhotoImage(resized)
            except (OSError, ValueError) as error:
                self.update_status(f"Logo could not be loaded: {error}")
                return None

        return None

    def add_logo_to_frame(self, parent_frame):
        """Render the shared, compact logo below a tab's form controls."""
        if self.logo_image is None:
            return

        logo_label = ttk.Label(
            parent_frame,
            image=self.logo_image,
            anchor="center",
        )
        logo_label.image = self.logo_image # type: ignore[attr-defined]
        logo_label.grid(row=11, column=0, columnspan=2, pady=(10, 0))

    def get_client_dropdown_items(self):
        """Return user-friendly ``ID - name`` choices for current clients."""
        clients = self.rm.search_records(record_type="Client")
        return [
            f"{client.get('id')} - {client.get('name', '')}"
            for client in clients
            if client.get("id") is not None
        ]

    def get_airline_dropdown_items(self):
        """Return user-friendly ``ID - company`` choices for current airlines."""
        airlines = self.rm.search_records(record_type="Airline")
        return [
            f"{airline.get('id')} - {airline.get('company_name', '')}"
            for airline in airlines
            if airline.get("id") is not None
        ]

    def refresh_flight_dropdowns(self):
        """Refresh Flight choices after a client or airline change."""
        flight_tab = getattr(self, "flight_tab", None)
        if flight_tab is not None and hasattr(flight_tab, "refresh_dropdowns"):
            flight_tab.refresh_dropdowns()

    @staticmethod
    def sort_treeview_column(tree, column, reverse):
        """Sort a Treeview column while treating numeric values numerically."""
        rows = [(tree.set(item, column), item) for item in tree.get_children("")]

        def sort_key(row):
            value = str(row[0]).strip()
            try:
                return 0, float(value)
            except ValueError:
                return 1, value.casefold()

        rows.sort(key=sort_key, reverse=reverse)
        for index, (_, item) in enumerate(rows):
            tree.move(item, "", index)

        tree.heading(
            column,
            command=lambda: MainApplicationWindow.sort_treeview_column(
                tree,
                column,
                not reverse,
            ),
        )
