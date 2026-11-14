"""Main window for the Specialist Travel Agent Record Management System.

Layout (the same for Flights, Clients and Airlines):

    +------------------------------------------------------------------+
    | [logo] Travel Records [Flights|Clients|Airlines] ●Saved  ☾  +New |
    +------------------------------------------------------------------+
    | CLIENTS 4 | AIRLINES 3 | FLIGHTS 4 | NEXT DEPARTURE 2026-12-20   |
    +----------------------------------------+-------------------------+
    | search + sortable table                | create / edit form      |
    +----------------------------------------+-------------------------+
    | status bar                                                       |
    +------------------------------------------------------------------+

The window only coordinates the views; all record rules live in
``RecordManager`` and ``gui.flight_tab.FlightBookingRules``.
"""

from datetime import date
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from PIL import Image, ImageTk

# pylint: disable=import-error, too-many-instance-attributes
from gui import theme
from gui.record_tab import AIRLINE, CLIENT, FLIGHT, TITLES, RecordTab
from gui.widgets import KpiCard, Toast

APP_NAME = "Travel Records"
APP_TITLE = "Specialist Travel Agent Record Management System — Group B"
TAB_ORDER = (FLIGHT, CLIENT, AIRLINE)


class MainApplicationWindow:
    """Own the header, summary cards, record views, theme and saving."""

    def __init__(self, root, record_manager, theme_name=theme.LIGHT):
        self.root = root
        self.rm = record_manager
        self.today = date.today          # replaced in tests for determinism
        self.theme_name = theme_name
        self.fonts = theme.Fonts(root)
        self.palette = theme.apply_theme(root, theme_name, self.fonts)
        root.title(APP_TITLE)

        # Window sizes are in screen pixels: scale them with the display so
        # the layout keeps its proportions on high-DPI screens.
        scale = max(1.0, root.winfo_fpixels("1i") / 96)
        width = min(int(1360 * scale), max(root.winfo_screenwidth() - 60, 1000))
        height = min(int(860 * scale), max(root.winfo_screenheight() - 90, 640))
        root.geometry(f"{width}x{height}")
        root.minsize(min(int(1100 * scale), width), min(int(680 * scale), height))
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)

        self.status_var = tk.StringVar(value="Starting application…")
        self.toast = Toast(root)
        self.logo_image = self.load_logo()
        self._build_menu()
        self._build_header()
        self._build_kpis()

        body = ttk.Frame(root, style="App.TFrame")
        body.grid(row=2, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)
        self.tabs = {}
        for record_type in TAB_ORDER:
            tab = RecordTab(body, self, record_type)
            tab.grid(row=0, column=0, sticky="nsew")
            self.tabs[record_type] = tab
        self.current_type = FLIGHT
        self.select_tab(FLIGHT)
        for tab in self.tabs.values():
            tab.retheme(self.palette)

        self.status_bar = ttk.Label(root, textvariable=self.status_var,
                                    style="Status.TLabel", anchor="w",
                                    padding=(14, 4))
        self.status_bar.grid(row=3, column=0, sticky="ew")
        self._bind_keys()
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.update_dashboard()
        self.update_status(
            f"System ready. Loaded {len(self.rm.records)} record(s) from storage.")

    # ------------------------------------------------------------ build
    def load_logo(self):
        """Load the logo scaled to fit the header, or ``None`` if unavailable."""
        source_root = Path(__file__).resolve().parents[1]
        for name in ("Logo.png", "logo.png"):
            path = source_root / "assets" / name
            if not path.exists():
                continue
            try:
                with Image.open(path) as image:
                    image = image.convert("RGBA")
                    height = 40
                    width = max(1, round(image.width * height / image.height))
                    return ImageTk.PhotoImage(
                        image.resize((width, height), Image.Resampling.LANCZOS))
            except (OSError, ValueError):
                return None
        return None

    def _build_menu(self):
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="Save all records now",
                              accelerator="Ctrl+Shift+S", command=self.save_now)
        file_menu.add_separator()
        file_menu.add_command(label="Exit (saves records)", command=self.on_close)
        menubar.add_cascade(label="File", menu=file_menu)
        view_menu = tk.Menu(menubar, tearoff=False)
        for number, record_type in enumerate(TAB_ORDER, start=1):
            view_menu.add_command(
                label=TITLES[record_type], accelerator=f"Ctrl+{number}",
                command=lambda t=record_type: self.select_tab(t))
        view_menu.add_separator()
        view_menu.add_command(label="Toggle light / dark theme",
                              accelerator="Ctrl+Shift+L", command=self.toggle_theme)
        menubar.add_cascade(label="View", menu=view_menu)
        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="Keyboard shortcuts", accelerator="F1",
                              command=self.show_shortcuts)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        self.root.config(menu=menubar)

    def _build_header(self):
        header = ttk.Frame(self.root, style="Header.TFrame", padding=(20, 10))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)

        brand = ttk.Frame(header, style="Plain.TFrame")
        brand.grid(row=0, column=0, sticky="w")
        if self.logo_image is not None:
            logo = ttk.Label(brand, image=self.logo_image, style="Card.TLabel")
            logo.image = self.logo_image
        else:
            logo = ttk.Label(brand, text="✈", style="Logo.TLabel")
        logo.grid(row=0, column=0, rowspan=2, padx=(0, 10))
        ttk.Label(brand, text=APP_NAME, style="Brand.TLabel").grid(
            row=0, column=1, sticky="sw")
        ttk.Label(brand, text="Travel agent records", style="Muted.TLabel").grid(
            row=1, column=1, sticky="nw")

        nav = ttk.Frame(header, style="Seg.TFrame", padding=3)
        nav.grid(row=0, column=1)
        self.nav_buttons = {}
        for i, record_type in enumerate(TAB_ORDER):
            button = ttk.Button(nav, text=TITLES[record_type], style="Nav.TButton",
                                command=lambda t=record_type: self.select_tab(t))
            button.grid(row=0, column=i, padx=1)
            self.nav_buttons[record_type] = button

        right = ttk.Frame(header, style="Plain.TFrame")
        right.grid(row=0, column=2, sticky="e")
        self.save_pill = ttk.Label(right, style="success.Pill.TLabel")
        self.save_pill.grid(row=0, column=0, padx=(0, 10))
        self.theme_button = ttk.Button(right, style="Icon.TButton",
                                       command=self.toggle_theme)
        self.theme_button.grid(row=0, column=1, padx=(0, 10))
        self.new_button = ttk.Button(
            right, style="Primary.TButton",
            command=lambda: self.current_tab().new_record())
        self.new_button.grid(row=0, column=2)
        self._update_theme_button()

    def _build_kpis(self):
        row = ttk.Frame(self.root, style="App.TFrame", padding=(20, 16, 20, 16))
        row.grid(row=1, column=0, sticky="ew")
        self.kpis = {
            "clients": KpiCard(row, "Clients", "DIRECTORY"),
            "airlines": KpiCard(row, "Airlines", "CARRIERS"),
            "flights": KpiCard(row, "Flights", "MANIFEST"),
            "next": KpiCard(row, "Next departure", "LIVE"),
        }
        for i, card in enumerate(self.kpis.values()):
            row.columnconfigure(i, weight=1, uniform="kpi")
            card.grid(row=0, column=i, sticky="nsew",
                      padx=(0 if i == 0 else 8, 0 if i == 3 else 8))

    def _bind_keys(self):
        root = self.root
        root.bind("<Control-n>", lambda _e: self.current_tab().new_record())
        root.bind("<Control-s>", lambda _e: self.current_tab().save_record())
        root.bind("<Control-S>", lambda _e: self.save_now())
        root.bind("<Control-f>", lambda _e: self.focus_search())
        root.bind("<Control-L>", lambda _e: self.toggle_theme())
        root.bind("<slash>", self._slash)
        root.bind("<Escape>", lambda _e: self.current_tab().new_record())
        root.bind("<F1>", lambda _e: self.show_shortcuts())
        for number, record_type in enumerate(TAB_ORDER, start=1):
            root.bind(f"<Control-Key-{number}>",
                      lambda _e, t=record_type: self.select_tab(t))

    def _slash(self, event):
        """``/`` jumps to search, unless the user is typing in a field."""
        if isinstance(event.widget, (ttk.Entry, tk.Entry, ttk.Combobox)):
            return None
        self.focus_search()
        return "break"

    # ------------------------------------------------------------ actions
    def current_tab(self):
        """The view currently shown."""
        return self.tabs[self.current_type]

    def select_tab(self, record_type):
        """Show one of the Flights / Clients / Airlines views."""
        self.current_type = record_type
        tab = self.tabs[record_type]
        tab.tkraise()
        for kind, button in self.nav_buttons.items():
            button.configure(style="NavActive.TButton" if kind == record_type
                             else "Nav.TButton")
        self.new_button.configure(text=f"+ New {record_type}   Ctrl+N")
        tab.refresh()

    def focus_search(self):
        """Move the cursor to the current view's search box."""
        self.current_tab().search_entry.focus_set()

    def refresh_all(self):
        """Redraw every view and the summary cards after a data change."""
        for tab in self.tabs.values():
            tab.refresh()
        self.update_dashboard()

    def summary_text(self):
        """Record counts shown under each table."""
        counts = (len(self.rm.search_records(record_type=t))
                  for t in (CLIENT, AIRLINE, FLIGHT))
        return ", ".join(f"{n} {label}" for n, label in
                         zip(counts, ("clients", "airlines", "flights")))

    def update_dashboard(self):
        """Refresh the four summary cards and the saved/unsaved indicator."""
        clients = self.rm.search_records(record_type=CLIENT)
        airlines = self.rm.search_records(record_type=AIRLINE)
        flights = self.rm.search_records(record_type=FLIGHT)
        today = self.today().isoformat()
        upcoming = [f for f in flights if str(f.get("date", "")) >= today]
        booked = len({f.get("client_id") for f in flights})
        self.kpis["clients"].set(len(clients), f"{booked} with flights booked")
        self.kpis["airlines"].set(len(airlines), "partner carriers")
        self.kpis["flights"].set(
            len(flights),
            f"{len(upcoming)} upcoming · {len(flights) - len(upcoming)} past")
        if upcoming:
            nxt = min(upcoming, key=lambda f: str(f["date"]))
            client = self.rm.get_record_by_id(nxt["client_id"], record_type=CLIENT)
            self.kpis["next"].set(
                nxt["date"],
                f"{nxt['start_city']} → {nxt['end_city']} · "
                f"{client['name'] if client else '?'}")
        else:
            self.kpis["next"].set("—", "No upcoming flights")
        self.save_pill.configure(text="●  All changes saved",
                                 style="success.Pill.TLabel")

    def update_status(self, message):
        """Show concise feedback about the most recent action."""
        self.status_var.set(str(message))
        self.root.update_idletasks()

    def notify(self, kind, title, message="", toast=True):
        """Show a toast and remember the message in the status bar."""
        self.status_var.set(f"{title}. {message}".strip() if message else title)
        if toast:
            self.toast.show(kind, title, message)

    def save(self):
        """Write every record to the data file; report a failure."""
        try:
            self.rm.save_to_file()
        except OSError as error:
            self.notify("error", "Records could not be saved", str(error))
            self.save_pill.configure(text="●  Unsaved changes",
                                     style="warning.Pill.TLabel")
            return False
        self.update_dashboard()
        return True

    def save_now(self):
        """Menu command: save and confirm."""
        if self.save():
            self.notify("success", "All records saved", str(self.rm.filepath))

    def _update_theme_button(self):
        dark = self.theme_name == theme.DARK
        self.theme_button.configure(text="☀  Light" if dark else "☾  Dark")

    def toggle_theme(self):
        """Switch between the light and dark palettes."""
        self.theme_name = (theme.DARK if self.theme_name == theme.LIGHT
                           else theme.LIGHT)
        self.palette = theme.apply_theme(self.root, self.theme_name, self.fonts)
        for tab in self.tabs.values():
            tab.retheme(self.palette)
            tab.update_date_hint()
        self._update_theme_button()
        self.notify("info", "Theme switched",
                    f"{self.theme_name.title()} theme is active.")

    def on_close(self):
        """Save every record, then close. Never closes silently on failure."""
        if any(t.dirty for t in self.tabs.values()) and not messagebox.askyesno(
                "Unsaved form",
                "A form has changes that were not saved as a record.\n\n"
                "Close anyway? (Records already saved in the tables will be kept.)",
                icon="warning", default="no", parent=self.root):
            return
        if not self.save() and not messagebox.askyesno(
                "Save failed", "Records could not be saved.\n\nClose WITHOUT "
                "saving? Changes made in this session will be lost.",
                icon="error", default="no", parent=self.root):
            return
        self.toast.hide()
        self.root.destroy()

    def show_shortcuts(self):
        """List the keyboard shortcuts."""
        messagebox.showinfo("Keyboard shortcuts", "\n".join((
            "Ctrl+1 / Ctrl+2 / Ctrl+3   Flights / Clients / Airlines",
            "/ or Ctrl+F                Search box (results update as you type)",
            "Down (in search box)       Move into the results table",
            "Ctrl+N or Esc              New record (clear the form)",
            "Ctrl+S or Enter (in form)  Create / update record",
            "Delete (in table)          Delete selected record",
            "Ctrl+Shift+S               Save all records to file",
            "Ctrl+Shift+L               Light / dark theme",
            "Tab / Shift+Tab            Move between fields",
        )), parent=self.root)

    def show_about(self):
        """Show the About box."""
        messagebox.showinfo(
            "About", f"{APP_TITLE}\n\nRecords are stored in:\n{self.rm.filepath}\n\n"
                     "They are loaded when the program starts and saved after "
                     "every change and when it closes.", parent=self.root)

