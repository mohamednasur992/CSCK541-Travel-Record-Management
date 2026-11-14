"""Generic record view (table + form) used for Clients, Airlines and Flights.

Every view has the same layout, so learning one teaches all three:

    +--------------------------------------+---------------------------+
    | [All fields v] [Search ...] [Show all]| Create New Client   NEW   |
    | table (sortable columns)             | (feedback banner)         |
    |                                      | form fields               |
    | Showing 4 of 4 clients               | [Cancel] [Create] [Delete]|
    +--------------------------------------+---------------------------+

The tab only collects input and shows results. Storage and referential
rules are delegated to ``RecordManager``; the same-day journey rule for
flights lives in ``gui.flight_tab.FlightBookingRules``.
"""

import tkinter as tk
from datetime import date, datetime
from tkinter import messagebox, ttk

# pylint: disable=import-error, too-many-instance-attributes
# pylint: disable=too-many-public-methods, too-many-lines
from gui import theme
from gui.autocomplete import AutocompleteCombobox
from gui.constants import CITY_TO_NATIONALITY, WORLD_AIRLINES, WORLD_CITIES
from gui.flight_tab import FlightBookingRules
from gui.widgets import Banner, ScrollFrame, SearchBox

CLIENT = "Client"
AIRLINE = "Airline"
FLIGHT = "Flight"

TITLES = {CLIENT: "Clients", AIRLINE: "Airlines", FLIGHT: "Flights"}
ALL_FIELDS = "All fields"
DATE_FORMAT = "%Y-%m-%d"
DATE_HINT = "YYYY-MM-DD"
QUICK_DATES = ("Today", "Tomorrow", "+3 Days", "+1 Week")

# Form fields: (record key, label, hint, widget kind). The kind is one of
# "id" (read-only, generated), "entry", "auto" (searchable drop-down that
# also accepts new text) or "link" (read-only drop-down of existing records).
REQUIRED = {
    CLIENT: ("name", "passport_number"),
    AIRLINE: ("company_name",),
    FLIGHT: ("client_id", "airline_id", "date", "start_city", "end_city"),
}
FIELDS = {
    CLIENT: {
        "id": ("Client ID", "generated", "id"),
        "name": ("Full Name", "", "entry"),
        "email": ("Email", "", "entry"),
        "phone_number": ("Phone Number", "", "entry"),
        "emergency_contact": ("Emergency Contact", "", "entry"),
        "city": ("City", "", "auto"),
        "nationality": ("Nationality", "suggested from city", "entry"),
        "address": ("Address", "", "entry"),
        "passport_number": ("Passport / ID", "", "entry"),
    },
    AIRLINE: {
        "id": ("Airline ID", "generated", "id"),
        "company_name": ("Company Name", "", "auto"),
    },
    FLIGHT: {
        "client_id": ("Client", "must already exist", "link"),
        "airline_id": ("Airline", "must already exist", "link"),
        "date": ("Travel Date", DATE_HINT, "entry"),
        "start_city": ("Start City", "", "auto"),
        "end_city": ("Destination", "", "auto"),
    },
}
# Form layout: rows of (field, relative width).
FORM_ROWS = {
    CLIENT: ((("id", 1), ("name", 3)), (("email", 1),),
             (("phone_number", 1), ("emergency_contact", 1)),
             (("city", 1), ("nationality", 1)), (("address", 1),),
             (("passport_number", 1),)),
    AIRLINE: ((("id", 1), ("company_name", 3)),),
    FLIGHT: ((("client_id", 1),), (("airline_id", 1),), (("date", 1),),
             (("start_city", 1), ("end_city", 1))),
}
LINKS = {"client_id": CLIENT, "airline_id": AIRLINE}

# Table columns: (heading, record key or None for computed columns).
TABLE_COLUMNS = {
    CLIENT: (("ID", "id"), ("Name", "name"), ("Email", "email"),
             ("Phone Number", "phone_number"), ("City", "city"),
             ("Nationality", "nationality")),
    AIRLINE: (("ID", "id"), ("Company Name", "company_name"), ("Flights", None)),
    FLIGHT: (("Travel Date", "date"), ("Client", None), ("Airline", None),
             ("Start City", "start_city"), ("Destination", "end_city")),
}
NARROW = {"ID": 70, "Flights": 90, "Travel Date": 120}
EXAMPLES = {FLIGHT: "Johannesburg, Maduna, 2026-11", CLIENT: "Maduna, Johannesburg, +27",
            AIRLINE: "Emirates, 2"}
SUBTITLES = {
    FLIGHT: "Book an existing client on an existing airline.",
    CLIENT: "Add a client's contact and passport details.",
    AIRLINE: "Add an airline company.",
}


def choice_label(record_id, name):
    """Drop-down text, e.g. ``"3 - Ada Lovelace"``."""
    return f"{record_id} - {name}"


def choice_id(label):
    """The numeric ID part of a drop-down entry, or ``None``."""
    text = str(label or "").split(" - ", maxsplit=1)[0].strip()
    return int(text) if text.isdigit() else None


def field_message(message):
    """Sentence-case error text shown under a field."""
    text = message[0].upper() + message[1:] if message else message
    return text if text.endswith(".") else text + "."


class RecordTab(ttk.Frame):
    """Search, list and edit records of one type."""

    def __init__(self, master, app, record_type):
        super().__init__(master, style="App.TFrame")
        self.app = app
        self.rm = app.rm
        self.record_type = record_type
        self.noun = record_type.lower()
        self.specs = FIELDS[record_type]
        self.rules = FlightBookingRules(self.rm) if record_type == FLIGHT else None
        self.current_key = None          # None = creating a new record
        self.current_record = None
        self.dirty = False               # form has unsaved edits
        self._loading = False            # suppress dirty tracking while filling
        self.row_records = {}
        self.vars = {}
        self.inputs = {}
        self.field_errors = {}
        self.sort_column = TABLE_COLUMNS[record_type][0][0]
        self.sort_desc = False

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, minsize=430)
        self.rowconfigure(0, weight=1)
        self._build_results()
        self._build_form()
        self.refresh()
        self.new_record(force=True)

    # ------------------------------------------------------------ build
    def _build_results(self):
        left = ttk.Frame(self, style="App.TFrame")
        left.grid(row=0, column=0, sticky="nsew", padx=(20, 16), pady=(0, 18))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)

        bar = ttk.Frame(left, style="App.TFrame")
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        bar.columnconfigure(1, weight=1)
        self.search_field = tk.StringVar(value=ALL_FIELDS)
        self.field_box = ttk.Combobox(
            bar, textvariable=self.search_field, state="readonly", width=16,
            values=[ALL_FIELDS] + [c for c, _k in TABLE_COLUMNS[self.record_type]])
        self.field_box.grid(row=0, column=0, padx=(0, 8), ipady=2)
        self.field_box.bind("<<ComboboxSelected>>", lambda _e: self.refresh())
        self.search_box = SearchBox(
            bar, f"Search {TITLES[self.record_type].lower()} "
                 f"(e.g. {EXAMPLES[self.record_type]}) — press /")
        self.search_box.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self.search_text = self.search_box.var
        self.search_entry = self.search_box.entry
        self.search_text.trace_add("write", lambda *_: self.refresh())
        self.search_entry.bind("<Return>", lambda _e: self.refresh())
        self.search_entry.bind("<Down>", lambda _e: self._focus_table())
        ttk.Button(bar, text="Show all", style="Secondary.TButton",
                   command=self.show_all).grid(row=0, column=2)

        card = ttk.Frame(left, style="Card.TFrame", padding=1)
        card.grid(row=1, column=0, sticky="nsew")
        card.columnconfigure(0, weight=1)
        card.rowconfigure(0, weight=1)
        columns = [c for c, _k in TABLE_COLUMNS[self.record_type]]
        self.tree = ttk.Treeview(card, columns=columns, show="headings",
                                 selectmode="browse")
        for column in columns:
            self.tree.heading(column, anchor="w",
                              command=lambda c=column: self.sort_by(c))
            narrow = NARROW.get(column)
            self.tree.column(column, width=narrow or 150, minwidth=60,
                             stretch=narrow is None, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0))
        scroll = ttk.Scrollbar(card, orient="vertical", command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Delete>", lambda _e: self.delete_record())
        self.empty_label = ttk.Label(card, style="Empty.TLabel")

        ttk.Separator(card).grid(row=1, column=0, columnspan=2, sticky="ew")
        footer = ttk.Frame(card, style="Plain.TFrame", padding=(16, 9))
        footer.grid(row=2, column=0, columnspan=2, sticky="ew")
        footer.columnconfigure(0, weight=1)
        self.result_count = tk.StringVar()
        self.system_text = tk.StringVar()
        ttk.Label(footer, textvariable=self.result_count,
                  style="Footer.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(footer, textvariable=self.system_text,
                  style="Muted.TLabel").grid(row=0, column=1, sticky="e")

    def _build_form(self):
        panel = ttk.Frame(self, style="Panel.TFrame", padding=(24, 18, 24, 18))
        panel.grid(row=0, column=1, sticky="nsew", pady=(0, 18), padx=(0, 20))
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(3, weight=1)

        head = ttk.Frame(panel, style="Plain.TFrame")
        head.grid(row=0, column=0, sticky="ew")
        head.columnconfigure(0, weight=1)
        self.form_title = tk.StringVar()
        self.form_subtitle = tk.StringVar()
        self.mode_text = tk.StringVar()
        ttk.Label(head, textvariable=self.form_title,
                  style="Title.TLabel").grid(row=0, column=0, sticky="w")
        self.mode_badge = ttk.Label(head, textvariable=self.mode_text,
                                    style="Badge.TLabel")
        self.mode_badge.grid(row=0, column=1, sticky="e")
        ttk.Label(head, textvariable=self.form_subtitle, style="Secondary.TLabel",
                  wraplength=370, justify="left").grid(
                      row=1, column=0, columnspan=2, sticky="w", pady=(2, 0))
        ttk.Separator(panel).grid(row=1, column=0, sticky="ew", pady=(12, 10))

        self.banner = Banner(panel, wraplength=340)
        self.banner.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self.banner.grid_remove()

        self.scroll = ScrollFrame(panel, self.app.palette["card"])
        self.scroll.grid(row=3, column=0, sticky="nsew")
        form = self.scroll.inner
        form.columnconfigure(0, weight=1)
        for row_index, row in enumerate(FORM_ROWS[self.record_type]):
            line = ttk.Frame(form, style="Plain.TFrame")
            line.grid(row=row_index, column=0, sticky="ew", pady=(0, 10), padx=(0, 4))
            for col, (name, weight) in enumerate(row):
                line.columnconfigure(col, weight=weight, uniform="cols")
                self._build_field(line, name, col, last=col == len(row) - 1)
            if self.record_type == FLIGHT and row[0][0] == "date":
                self._build_date_tools(line)

        buttons = ttk.Frame(panel, style="Plain.TFrame")
        buttons.grid(row=4, column=0, sticky="ew", pady=(14, 0))
        for i in range(3):
            buttons.columnconfigure(i, weight=1, uniform="buttons")
        self.cancel_button = ttk.Button(buttons, text="Cancel (Esc)",
                                        style="Secondary.TButton",
                                        command=self.new_record)
        self.save_button = ttk.Button(buttons, text="Create",
                                      style="Primary.TButton",
                                      command=self.save_record)
        self.delete_button = ttk.Button(buttons, text="Delete",
                                        style="Danger.TButton",
                                        command=self.delete_record)
        self.cancel_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.save_button.grid(row=0, column=1, sticky="ew", padx=6)
        self.delete_button.grid(row=0, column=2, sticky="ew", padx=(6, 0))

    def _build_field(self, parent, name, column, last):
        label_text, hint, kind = self.specs[name]
        cell = ttk.Frame(parent, style="Plain.TFrame")
        cell.grid(row=0, column=column, sticky="new", padx=(0, 0 if last else 12))
        cell.columnconfigure(1, weight=1)
        ttk.Label(cell, text=label_text, style="Field.TLabel").grid(
            row=0, column=0, sticky="w")
        required = name in REQUIRED[self.record_type]
        if required:
            ttk.Label(cell, text=" *", style="Required.TLabel").grid(
                row=0, column=1, sticky="w")
        hint = hint or ("" if required or kind == "id" else "optional")
        if hint:
            ttk.Label(cell, text=hint, style="Hint.TLabel").grid(
                row=0, column=2, sticky="e")

        var = tk.StringVar()
        var.trace_add("write", lambda *_a, n=name: self._on_edit(n))
        self.vars[name] = var
        if kind == "id":
            widget = ttk.Entry(cell, textvariable=var, width=1, state="readonly")
        elif kind == "link":
            widget = ttk.Combobox(cell, textvariable=var, state="readonly",
                                  height=12, width=1)
        elif kind == "auto":
            items = {"city": WORLD_CITIES, "start_city": WORLD_CITIES,
                     "end_city": WORLD_CITIES,
                     "company_name": WORLD_AIRLINES}[name]
            widget = AutocompleteCombobox(cell, items, textvariable=var, width=1)
            if name == "city":
                widget.bind("<<ComboboxSelected>>", self._on_city_selected, add="+")
        else:
            widget = ttk.Entry(cell, textvariable=var, width=1)
            widget.bind("<Return>", lambda _e: self.save_record())
        widget.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(4, 0))
        self.inputs[name] = widget
        error = ttk.Label(cell, style="FieldError.TLabel", wraplength=170,
                          justify="left")
        error.grid(row=2, column=0, columnspan=3, sticky="w", pady=(3, 0))
        error.grid_remove()
        self.field_errors[name] = error

    def _build_date_tools(self, line):
        chips = ttk.Frame(line, style="Plain.TFrame")
        chips.grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.quick_buttons = {}
        for i, option in enumerate(QUICK_DATES):
            button = ttk.Button(chips, text=option, style="Chip.TButton",
                                command=lambda o=option: self.apply_quick_date(o))
            button.grid(row=0, column=i, padx=(0, 6))
            self.quick_buttons[option] = button
        self.date_hint = ttk.Label(line, style="AccentBadge.TLabel")
        self.date_hint.grid(row=2, column=0, sticky="w", pady=(6, 0))

    # ------------------------------------------------------------ helpers
    def _on_edit(self, name):
        if self._loading:
            return
        self.dirty = True
        self._clear_field_error(name)
        if name == "date":
            self.update_date_hint()

    def _on_city_selected(self, _event=None):
        """Suggest a nationality for the selected city (client form only)."""
        suggestion = CITY_TO_NATIONALITY.get(self.vars["city"].get().strip())
        if suggestion and not self.vars["nationality"].get().strip():
            self.vars["nationality"].set(suggestion)

    def _focus_table(self):
        children = self.tree.get_children()
        if children:
            self.tree.focus_set()
            self.tree.focus(children[0])

    def apply_quick_date(self, option):
        """Fill the travel date from a quick button."""
        days = {"Today": 0, "Tomorrow": 1, "+3 Days": 3, "+1 Week": 7}[option]
        target = date.fromordinal(self.app.today().toordinal() + days)
        self.vars["date"].set(target.strftime(DATE_FORMAT))

    def update_date_hint(self):
        """Describe the typed travel date (how far away, or invalid)."""
        if self.record_type != FLIGHT:
            return
        text = self.vars["date"].get().strip()
        if not text:
            kind, message = "muted", f"Format {DATE_HINT}"
        else:
            try:
                when = datetime.strptime(text, DATE_FORMAT).date()
            except ValueError:
                kind, message = "error", f"Not a valid date – use {DATE_HINT}"
            else:
                days = (when - self.app.today()).days
                label = when.strftime("%a %d %b %Y")
                if days == 0:
                    kind, message = "info", f"Departs today ({label})"
                elif days > 0:
                    kind = "info"
                    message = (f"Departs in {days} day{'s' * (days != 1)} ({label})")
                else:
                    kind = "warning"
                    message = (f"Departed {-days} day{'s' * (days != -1)} ago "
                               "– this is a past flight")
        style = {"info": "AccentBadge.TLabel", "warning": "warning.Pill.TLabel",
                 "error": "FieldError.TLabel", "muted": "Hint.TLabel"}[kind]
        self.date_hint.grid()
        self.date_hint.configure(text=message, style=style)

    def _set_form(self, record):
        self._loading = True
        try:
            for name in self.specs:
                value = "" if record is None else record.get(name, "")
                if name in LINKS and record is not None:
                    value = choice_label(value, self.name_of(LINKS[name], value))
                self.vars[name].set(str(value))
        finally:
            self._loading = False
        self.dirty = False
        self._clear_errors()
        self.update_date_hint()

    def _form_data(self):
        data = {"type": self.record_type}
        for name in self.specs:
            value = self.vars[name].get().strip()
            if name in LINKS:
                value = choice_id(value)
            elif name == "id":
                value = int(value) if value.isdigit() else None
            data[name] = value
        return data

    def _input_style(self, name, invalid):
        kind = self.specs[name][2]
        base = "TCombobox" if kind in ("link", "auto") else "TEntry"
        return f"Invalid.{base}" if invalid else base

    def _clear_field_error(self, name):
        if name in self.field_errors and self.field_errors[name].cget("text"):
            self.field_errors[name].configure(text="")
            self.field_errors[name].grid_remove()
            self.inputs[name].configure(style=self._input_style(name, False))

    def _clear_errors(self):
        for name in self.field_errors:
            self.field_errors[name].configure(text="")
            self.field_errors[name].grid_remove()
            self.inputs[name].configure(style=self._input_style(name, False))
        self.hide_banner()

    def _show_errors(self, errors):
        """Mark invalid fields; ``errors`` maps field name (or ``""``) to text."""
        self._clear_errors()
        general = []
        for name, message in errors.items():
            if name in self.field_errors:
                self.field_errors[name].configure(text=field_message(message))
                self.field_errors[name].grid()
                self.inputs[name].configure(style=self._input_style(name, True))
            else:
                general.append(message)
        count = len(errors)
        shown = [n for n in errors if n in self.field_errors]
        detail = "\n".join(general) or (
            "Fix the fields marked in red below, then try again." if shown else "")
        title = ("Booking not allowed" if general and not shown
                 else f"{count} field{'s' * (count != 1)} need"
                      f"{'s' * (count == 1)} attention")
        self.show_banner("error", title, detail)
        first = next((n for n in self.specs if n in errors), None)
        if first:
            self.inputs[first].focus_set()
            self.scroll.scroll_to(self.inputs[first])

    def show_banner(self, kind, title, message=""):
        """Show a coloured message above the form."""
        self.banner.show(kind, title, message)
        self.banner.grid()

    def hide_banner(self):
        """Hide the message above the form."""
        self.banner.grid_remove()

    def _confirm_discard(self):
        if not self.dirty:
            return True
        return messagebox.askyesno(
            "Discard changes?",
            "The form has changes that have not been saved.\n\nDiscard them?",
            icon="warning", default="no", parent=self)

    # ----------------------------------------------------- data helpers
    def name_of(self, record_type, record_id):
        """Client name or airline company name for an ID ("" if unknown)."""
        record = self.rm.get_record_by_id(record_id, record_type=record_type)
        if not record:
            return ""
        return record.get("name" if record_type == CLIENT else "company_name", "")

    def flights_for(self, link_field, record_id):
        """Flights that refer to the given client or airline ID."""
        return [r for r in self.rm.search_records(record_type=FLIGHT)
                if str(r.get(link_field)) == str(record_id)]

    def _row_values(self, record):
        if self.record_type == FLIGHT:
            return (record.get("date", ""),
                    f"{self.name_of(CLIENT, record['client_id'])}  #{record['client_id']}",
                    f"{self.name_of(AIRLINE, record['airline_id'])}  #{record['airline_id']}",
                    record.get("start_city", ""), record.get("end_city", ""))
        if self.record_type == AIRLINE:
            return (record["id"], record.get("company_name", ""),
                    len(self.flights_for("airline_id", record["id"])))
        return tuple(record.get(key, "") for _c, key in TABLE_COLUMNS[CLIENT])

    @staticmethod
    def _key_of(record):
        if record["type"] == FLIGHT:
            return (str(record["client_id"]), str(record["airline_id"]),
                    str(record["date"]), str(record["start_city"]).casefold(),
                    str(record["end_city"]).casefold())
        return record["id"]

    def _sort_key(self, item):
        values = item[1]
        index = [c for c, _k in TABLE_COLUMNS[self.record_type]].index(self.sort_column)
        value = values[index]
        if isinstance(value, int):
            return (0, value, "")
        return (1, 0, str(value).casefold())

    def _matches(self, record, values, query, field):
        if not query:
            return True
        if field != ALL_FIELDS:
            columns = [c for c, _k in TABLE_COLUMNS[self.record_type]]
            return query in str(values[columns.index(field)]).casefold()
        haystack = [str(v) for v in values] + [str(v) for v in record.values()]
        return any(query in text.casefold() for text in haystack)

    def _update_headings(self):
        for column, _key in TABLE_COLUMNS[self.record_type]:
            arrow = (" ▼" if self.sort_desc else " ▲") if column == self.sort_column else ""
            self.tree.heading(column, text=column.upper() + arrow)

    # ------------------------------------------------------------ actions
    def sort_by(self, column):
        """Sort by a column; clicking the same heading again reverses it."""
        if column == self.sort_column:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_column, self.sort_desc = column, False
        self.refresh()

    def refresh(self):
        """Re-run the current search and redraw the table and drop-downs."""
        query = self.search_text.get().strip().casefold()
        field = self.search_field.get()
        records = self.rm.search_records(record_type=self.record_type)
        rows = [(r, self._row_values(r)) for r in records]
        rows = [row for row in rows if self._matches(row[0], row[1], query, field)]
        rows.sort(key=self._sort_key, reverse=self.sort_desc)
        self._update_headings()

        self.tree.delete(*self.tree.get_children())
        self.row_records.clear()
        selected_iid = None
        for index, (record, values) in enumerate(rows):
            iid = f"row{index}"
            self.row_records[iid] = dict(record)
            self.tree.insert("", "end", iid=iid, values=values,
                             tags=("alt",) if index % 2 else ())
            if self.current_key is not None and self._key_of(record) == self.current_key:
                selected_iid = iid
        if selected_iid:
            self.tree.selection_set(selected_iid)
            self.tree.see(selected_iid)

        total = len(records)
        noun = TITLES[self.record_type].lower()
        self.result_count.set(f"Showing {len(rows)} of {total} {noun}")
        self.system_text.set(self.app.summary_text())
        if rows:
            self.empty_label.place_forget()
        else:
            shown = self.search_text.get().strip()
            message = (f"No {noun} match “{shown}”.\nPress Show all to clear the search."
                       if shown else
                       f"No {noun} yet.\nUse the form on the right to create the first one.")
            self.empty_label.configure(text=message)
            self.empty_label.place(relx=0.5, rely=0.45, anchor="center")
        self.refresh_dropdowns()

    def refresh_dropdowns(self):
        """Refresh the client/airline choices of the flight form."""
        if self.record_type != FLIGHT:
            return
        for field, record_type in LINKS.items():
            records = sorted(self.rm.search_records(record_type=record_type),
                             key=lambda r: r["id"])
            self.inputs[field].configure(values=[
                choice_label(r["id"], self.name_of(record_type, r["id"]))
                for r in records])

    def show_all(self):
        """Clear the search."""
        self.search_field.set(ALL_FIELDS)
        self.search_text.set("")
        self.refresh()

    def _on_select(self, _event=None):
        selection = self.tree.selection()
        if not selection:
            return
        record = self.row_records.get(selection[0])
        if record is None:
            return
        if self.current_key is not None and self._key_of(record) == self.current_key:
            return
        if not self._confirm_discard():
            self.refresh()  # restore the previous selection
            return
        self.edit_record(record)

    def edit_record(self, record):
        """Load a record into the form for editing."""
        self.current_key = self._key_of(record)
        self.current_record = dict(record)
        if self.rules:
            self.rules.original_flight_key = dict(record)
        self._set_form(record)
        if self.record_type == FLIGHT:
            self.form_title.set(f"Edit Flight · {self.name_of(CLIENT, record['client_id'])}")
            self.form_subtitle.set(
                f"{record['start_city']} → {record['end_city']} with "
                f"{self.name_of(AIRLINE, record['airline_id'])}, {record['date']}")
        else:
            shown = record.get("name") or record.get("company_name", "")
            self.form_title.set(f"Edit {self.record_type} #{record['id']}")
            self.form_subtitle.set(f"{shown} · the ID cannot be changed")
        self.mode_text.set("EDITING")
        self.mode_badge.configure(style="AccentBadge.TLabel")
        self.save_button.configure(text=f"Update {self.record_type}")
        self.delete_button.state(["!disabled"])

    def next_id(self):
        """The next free ID (one more than the highest in use)."""
        ids = [int(r["id"]) for r in self.rm.search_records(record_type=self.record_type)
               if str(r.get("id", "")).isdigit()]
        return max(ids, default=0) + 1

    def new_record(self, force=False):
        """Clear the form ready for a new record (with a generated ID)."""
        if not force and not self._confirm_discard():
            return
        self.current_key = None
        self.current_record = None
        if self.rules:
            self.rules.original_flight_key = None
        self.tree.selection_remove(self.tree.selection())
        self._set_form(None)
        if "id" in self.vars:
            self._loading = True
            self.vars["id"].set(str(self.next_id()))
            self._loading = False
        self.form_title.set(f"Create New {self.record_type}")
        self.form_subtitle.set(SUBTITLES[self.record_type]
                               + " Fields marked * are required.")
        self.mode_text.set("NEW")
        self.mode_badge.configure(style="Badge.TLabel")
        self.save_button.configure(text=f"Create {self.record_type}")
        self.delete_button.state(["disabled"])
        self.show_guidance()
        first = {CLIENT: "name", AIRLINE: "company_name", FLIGHT: "client_id"}[
            self.record_type]
        self.inputs[first].focus_set()

    def show_guidance(self):
        """Explain up front when a flight cannot be created yet."""
        if self.record_type != FLIGHT:
            return
        missing = [phrase for record_type, phrase in
                   ((CLIENT, "a client"), (AIRLINE, "an airline"))
                   if not self.rm.search_records(record_type=record_type)]
        if missing:
            self.show_banner(
                "info", "Before you book a flight",
                "A flight must refer to an existing client and airline. "
                f"Create {' and '.join(missing)} first in the Clients / Airlines views.")

    # --------------------------------------------------------- validation
    def validate(self, data):
        """Return ``{field: message}`` for every problem in ``data``."""
        errors = {}
        for name in REQUIRED[self.record_type]:
            if data.get(name) in (None, ""):
                errors[name] = ("select an existing record" if name in LINKS
                                else "is required")
        if self.record_type == CLIENT:
            email = data["email"]
            if email and ("@" not in email or "." not in email.rsplit("@", 1)[-1]):
                errors["email"] = "enter a valid email address or leave it blank"
        elif self.record_type == AIRLINE:
            wanted = str(data["company_name"]).casefold()
            if wanted and any(
                    str(r.get("id")) != str(data["id"])
                    and str(r.get("company_name", "")).strip().casefold() == wanted
                    for r in self.rm.search_records(record_type=AIRLINE)):
                errors["company_name"] = "another airline already uses this name"
        else:
            errors.update(self._validate_flight(data, errors))
        return errors

    def _validate_flight(self, data, errors):
        found = {}
        for name, record_type in LINKS.items():
            if name not in errors and self.rm.get_record_by_id(
                    data[name], record_type=record_type) is None:
                found[name] = f"that {record_type.lower()} no longer exists"
        if "date" not in errors:
            try:
                datetime.strptime(data["date"], DATE_FORMAT)
            except ValueError:
                found["date"] = f"use the format {DATE_HINT}"
        if ("start_city" not in errors and "end_city" not in errors
                and data["start_city"].casefold() == data["end_city"].casefold()):
            found["end_city"] = "must differ from the start city"
        if not errors and not found:
            message = self.rules.booking_conflict_message(
                data, exclude_original=self.current_key is not None)
            if message:
                found["booking"] = message
        return found

    # ------------------------------------------------------------- saving
    def save_record(self):
        """Create or update from the form. Returns True on success."""
        data = self._form_data()
        errors = self.validate(data)
        if errors:
            self._show_errors(errors)
            self.app.notify("error", f"{self.record_type} not saved",
                            "Correct the highlighted fields and try again.",
                            toast=False)
            return False
        creating = self.current_key is None
        try:
            if creating:
                self._create(data)
            elif not self._update(data):
                self.app.notify("error", "Update failed",
                                f"The selected {self.noun} could not be found.")
                return False
        except (TypeError, ValueError) as error:
            self.app.notify("error", f"{self.record_type} not saved", str(error))
            return False
        self.app.save()
        self.dirty = False
        self.app.refresh_all()
        verb = "created" if creating else "updated"
        self.new_record(force=True)
        self.show_banner("success", f"{self.record_type} {verb}",
                         "The record was saved to the data file.")
        self.app.notify("success", f"{self.record_type} {verb} successfully")
        return True

    def _create(self, data):
        if self.record_type == CLIENT:
            if self.rm.get_record_by_id(data["id"], record_type=CLIENT):
                raise ValueError(f"Client ID {data['id']} already exists.")
            self.rm.add_client(
                data["id"], data["name"], data["email"], data["phone_number"],
                data["city"], data["address"], data["passport_number"],
                data["nationality"], data["emergency_contact"])
        elif self.record_type == AIRLINE:
            if self.rm.get_record_by_id(data["id"], record_type=AIRLINE):
                raise ValueError(f"Airline ID {data['id']} already exists.")
            self.rm.add_airline(data["id"], data["company_name"])
        else:
            self.rm.add_flight(data["client_id"], data["airline_id"], data["date"],
                               data["start_city"], data["end_city"])

    def _update(self, data):
        if self.record_type == FLIGHT:
            old = self.current_record
            return self.rm.update_record(
                old["client_id"], data, record_type=FLIGHT,
                old_airline_id=old["airline_id"], old_date=old["date"],
                old_start=old["start_city"], old_end=old["end_city"])
        return self.rm.update_record(data["id"], data, record_type=self.record_type)

    def delete_record(self):
        """Delete the record in the form after confirmation."""
        if self.current_key is None:
            self.app.notify("info", "Nothing selected",
                            "Select a record in the table to delete it.")
            return False
        record = self.current_record
        if self.record_type == FLIGHT:
            description = (f"the flight on {record['date']} from "
                           f"{record['start_city']} to {record['end_city']}")
            conflict = self.rules.deletion_conflict_message(record)
            if conflict:
                messagebox.showerror("Journey integrity", conflict, parent=self)
                self.show_banner("warning", "Delete blocked", conflict)
                self.app.notify("warning", "Flight not deleted",
                                "It would break the same-day journey.")
                return False
        else:
            name = record.get("name") or record.get("company_name", "")
            description = f"{self.noun} {record['id']} ({name})"
            link = "client_id" if self.record_type == CLIENT else "airline_id"
            count = len(self.flights_for(link, record["id"]))
            if count:
                messagebox.showwarning(
                    "Cannot delete",
                    f"{description[0].upper() + description[1:]} has {count} "
                    "flight(s).\n\nDelete or change those flights first, so no "
                    f"flight is left without a {self.noun}.", parent=self)
                self.show_banner("warning", "Delete blocked",
                                 f"{count} flight(s) still refer to this {self.noun}.")
                self.app.notify("warning", f"{self.record_type} not deleted",
                                "It still has flights.")
                return False
        if not messagebox.askyesno("Confirm delete", f"Permanently delete {description}?",
                                   icon="warning", default="no", parent=self):
            self.app.notify("info", "Delete cancelled")
            return False
        try:
            if self.record_type == FLIGHT:
                deleted = self.rm.delete_record(
                    record["client_id"], record_type=FLIGHT,
                    airline_id=record["airline_id"], date=record["date"],
                    start_city=record["start_city"], end_city=record["end_city"])
            else:
                deleted = self.rm.delete_record(record["id"],
                                                record_type=self.record_type)
        except ValueError as error:
            messagebox.showerror("Cannot delete", str(error), parent=self)
            return False
        if not deleted:
            self.app.notify("error", "Delete failed",
                            f"The selected {self.noun} could not be found.")
            return False
        self.app.save()
        self.dirty = False
        self.new_record(force=True)
        self.app.refresh_all()
        self.app.notify("success", f"{self.record_type} deleted")
        return True

    def retheme(self, palette):
        """Recolour widgets that ttk styles cannot reach after a theme change."""
        self.tree.tag_configure("alt", background=palette["row_alt"])
        self.scroll.set_background(palette["card"])
        boxes = [self.field_box] + [
            w for w in self.inputs.values() if isinstance(w, ttk.Combobox)]
        for box in boxes:
            theme.style_combobox_popdown(box, palette)
