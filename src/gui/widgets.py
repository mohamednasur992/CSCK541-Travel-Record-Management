"""Small reusable widgets for the RMS Pro interface.

* ``KpiCard``  – a summary tile (caption, badge, big value, sub-line).
* ``SearchBox`` – an entry with a placeholder hint that never becomes data.
* ``Banner``   – an in-form message box coloured by kind (success, error…).
* ``Toast``    – a short-lived notification in the top-right corner.

They contain no business logic and are styled entirely through
``gui.theme``.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from gui.theme import FEEDBACK_KINDS

TOAST_MS = 3500
ICONS = {"success": "✔", "error": "✖", "warning": "⚠", "info": "ℹ"}


class KpiCard(ttk.Frame):
    """Summary tile: CAPTION [BADGE] / value / sub-line."""

    def __init__(self, master, caption: str, badge: str = ""):
        super().__init__(master, style="Card.TFrame", padding=(16, 12))
        self.columnconfigure(0, weight=1)
        self.value = tk.StringVar(value="–")
        self.sub = tk.StringVar()
        ttk.Label(self, text=caption.upper(), style="Caption.TLabel").grid(row=0, column=0, sticky="w")
        if badge:
            ttk.Label(self, text=badge, style="Badge.TLabel").grid(row=0, column=1, sticky="e")
        ttk.Label(self, textvariable=self.value, style="Kpi.TLabel").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Label(self, textvariable=self.sub, style="KpiSub.TLabel").grid(
            row=2, column=0, columnspan=2, sticky="w")

    def set(self, value, sub: str = "") -> None:
        self.value.set(str(value))
        self.sub.set(sub)


class SearchBox(ttk.Frame):
    """Entry with a grey placeholder shown only while the box is empty.

    The placeholder is a separate label laid over the entry, so it is never
    part of the entered text (a common bug with placeholder tricks).
    """

    def __init__(self, master, placeholder: str, width: int = 40):
        super().__init__(master, style="Plain.TFrame")
        self.columnconfigure(0, weight=1)
        self.var = tk.StringVar()
        self.entry = ttk.Entry(self, textvariable=self.var, width=width)
        self.entry.grid(row=0, column=0, sticky="ew")
        self.placeholder = ttk.Label(self, text=placeholder, style="Placeholder.TLabel")
        self.placeholder.bind("<Button-1>", lambda _e: self.entry.focus_set())
        self.var.trace_add("write", lambda *_: self._update())
        self.entry.bind("<FocusIn>", lambda _e: self._update(), add="+")
        self.entry.bind("<FocusOut>", lambda _e: self._update(), add="+")
        self._update()

    def placeholder_visible(self) -> bool:
        return self.placeholder.winfo_manager() == "place"

    def _update(self) -> None:
        if self.var.get():
            self.placeholder.place_forget()
        else:
            self.placeholder.place(x=11, rely=0.5, anchor="w")

    def get(self) -> str:
        return self.var.get()

    def set(self, text: str) -> None:
        self.var.set(text)


class ScrollFrame(ttk.Frame):
    """A vertically scrolling area; the scrollbar appears only when needed.

    Put child widgets in ``self.inner``. Used for the record form so that
    long forms (e.g. a client with error messages) never push the action
    buttons off a small screen.
    """

    def __init__(self, master, background: str):
        super().__init__(master, style="Plain.TFrame")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0, background=background)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.inner = ttk.Frame(self.canvas, style="Plain.TFrame")
        self._window = self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda _e: self._refresh())
        self.canvas.bind("<Configure>", self._on_resize)
        self.bind("<Enter>", lambda _e: self._bind_wheel(True))
        self.bind("<Leave>", lambda _e: self._bind_wheel(False))

    def set_background(self, colour: str) -> None:
        self.canvas.configure(background=colour)

    def needs_scrolling(self) -> bool:
        return self.inner.winfo_reqheight() > self.canvas.winfo_height() > 1

    def _on_resize(self, event) -> None:
        self.canvas.itemconfigure(self._window, width=event.width)
        self._refresh()

    def _refresh(self) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        if self.needs_scrolling():
            self.scrollbar.grid(row=0, column=1, sticky="ns", padx=(4, 0))
        else:
            self.scrollbar.grid_remove()
            self.canvas.yview_moveto(0)

    def _bind_wheel(self, on: bool) -> None:
        for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            if on:
                self.canvas.bind_all(sequence, self._on_wheel)
            else:
                self.canvas.unbind_all(sequence)

    def _on_wheel(self, event) -> None:
        if not self.needs_scrolling():
            return
        if getattr(event, "num", None) == 4:
            step = -1
        elif getattr(event, "num", None) == 5:
            step = 1
        else:
            step = -1 if event.delta > 0 else 1
        self.canvas.yview_scroll(step * 3, "units")

    def scroll_to(self, widget) -> None:
        """Scroll so that ``widget`` (inside ``inner``) is visible."""
        self.update_idletasks()
        total = max(self.inner.winfo_reqheight(), 1)
        y = widget.winfo_rooty() - self.inner.winfo_rooty()
        self.canvas.yview_moveto(max(0.0, (y - 20) / total))


class Banner(ttk.Frame):
    """Coloured message box: bold title plus detail text."""

    def __init__(self, master, wraplength: int = 360):
        super().__init__(master, style="info.Feedback.TFrame", padding=(12, 8))
        self.columnconfigure(1, weight=1)
        self.kind = "info"
        self.icon = ttk.Label(self, style="info.FeedbackTitle.TLabel")
        self.icon.grid(row=0, column=0, sticky="nw", padx=(0, 8))
        self.title = ttk.Label(self, style="info.FeedbackTitle.TLabel", wraplength=wraplength)
        self.title.grid(row=0, column=1, sticky="w")
        self.message = ttk.Label(self, style="info.Feedback.TLabel", wraplength=wraplength,
                                 justify="left")
        self.message.grid(row=1, column=1, sticky="w")

    def show(self, kind: str, title: str, message: str = "") -> None:
        if kind not in FEEDBACK_KINDS:
            raise ValueError(f"unknown feedback kind {kind!r}")
        self.kind = kind
        self.configure(style=f"{kind}.Feedback.TFrame")
        self.icon.configure(text=ICONS[kind], style=f"{kind}.FeedbackTitle.TLabel")
        self.title.configure(text=title, style=f"{kind}.FeedbackTitle.TLabel")
        self.message.configure(text=message, style=f"{kind}.Feedback.TLabel")
        if message:
            self.message.grid()
        else:
            self.message.grid_remove()

    def text(self) -> str:
        return f"{self.title.cget('text')}\n{self.message.cget('text')}".strip()


class Toast:
    """One notification at a time, top-right below the header; hides after a delay."""

    def __init__(self, root: tk.Misc, top_offset: int = 72):
        self.root = root
        self.top_offset = top_offset
        self.banner: Banner | None = None
        self._job = None
        # Cancel a pending hide if the window closes while a toast is showing.
        root.bind("<Destroy>", lambda e: self.hide() if e.widget is root else None, add="+")

    def show(self, kind: str, title: str, message: str = "", ms: int = TOAST_MS) -> Banner:
        self.hide()
        self.banner = Banner(self.root, wraplength=300)
        self.banner.show(kind, title, message)
        self.banner.place(relx=1.0, y=self.top_offset, x=-20, anchor="ne")
        self.banner.lift()
        self.banner.bind("<Button-1>", lambda _e: self.hide())
        self._job = self.root.after(ms, self.hide)
        return self.banner

    def hide(self) -> None:
        if self._job is not None:
            try:
                self.root.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None
        if self.banner is not None:
            try:
                self.banner.destroy()
            except tk.TclError:
                pass
            self.banner = None

    def visible_text(self) -> str:
        return self.banner.text() if self.banner is not None else ""
