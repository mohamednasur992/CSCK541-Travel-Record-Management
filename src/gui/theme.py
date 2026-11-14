"""Colours, fonts and ttk styles for the application's "RMS Pro" look.

A calm 60/30/10 colour split (white content surfaces, slate background,
blue accent for actions), slate text, and colour-coded feedback (green
success, amber warning, red error, blue information). Light and dark
palettes share the same keys, so every widget is styled once and switching
theme only reconfigures the styles.

Accessibility: ``contrast_ratio`` implements the WCAG 2.x formula; body text
meets 4.5:1 and secondary text 3:1 on every surface in both themes.
"""

from __future__ import annotations

try:  # palettes and contrast maths work without Tk; styling needs it
    import tkinter as tk
    from tkinter import font as tkfont
    from tkinter import ttk
except ImportError:  # pragma: no cover - Python built without Tk
    tk = tkfont = ttk = None

LIGHT = "light"
DARK = "dark"

PALETTES: dict[str, dict[str, str]] = {
    LIGHT: {
        "bg": "#F1F5F9",          # 30 %: app background behind cards
        "card": "#FFFFFF",        # 60 %: cards, tables, form panel
        "input": "#FFFFFF",
        "input_disabled": "#F1F5F9",
        "border": "#E2E8F0",
        "border_strong": "#CBD5E1",
        "text": "#0F172A",
        "text2": "#475569",
        "muted": "#64748B",
        "accent": "#2563EB",      # 10 %: primary actions and selection
        "accent_hover": "#1D4ED8",
        "accent_text": "#FFFFFF",
        "accent_soft": "#EFF6FF",
        "select": "#DBEAFE",
        "row_alt": "#F8FAFC",
        "success_bg": "#F0FDF4", "success_fg": "#166534", "success_border": "#86EFAC",
        "warning_bg": "#FFFBEB", "warning_fg": "#92400E", "warning_border": "#FCD34D",
        "error_bg": "#FEF2F2", "error_fg": "#B91C1C", "error_border": "#FCA5A5",
        "info_bg": "#EFF6FF", "info_fg": "#1E40AF", "info_border": "#BFDBFE",
    },
    DARK: {
        "bg": "#0B1220",
        "card": "#111A2E",
        "input": "#0F172A",
        "input_disabled": "#1E293B",
        "border": "#1E293B",
        "border_strong": "#334155",
        "text": "#E2E8F0",
        "text2": "#CBD5E1",
        "muted": "#94A3B8",
        "accent": "#2563EB",
        "accent_hover": "#3B82F6",
        "accent_text": "#FFFFFF",
        "accent_soft": "#172554",
        "select": "#1E3A8A",
        "row_alt": "#0F1A30",
        "success_bg": "#052E16", "success_fg": "#86EFAC", "success_border": "#166534",
        "warning_bg": "#2B1D05", "warning_fg": "#FCD34D", "warning_border": "#92400E",
        "error_bg": "#2A0E12", "error_fg": "#FCA5A5", "error_border": "#991B1B",
        "info_bg": "#0F1E3D", "info_fg": "#93C5FD", "info_border": "#1E40AF",
    },
}

FEEDBACK_KINDS = ("success", "warning", "error", "info")

_SANS = ("Segoe UI", "SF Pro Text", "Helvetica Neue", "Inter", "Ubuntu",
         "Noto Sans", "DejaVu Sans", "Arial")
_MONO = ("Cascadia Mono", "Consolas", "SF Mono", "Menlo", "JetBrains Mono",
         "DejaVu Sans Mono", "Courier New")


# ------------------------------------------------------------ colour maths
def _channel(value: int) -> float:
    c = value / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_colour: str) -> float:
    """WCAG relative luminance of a ``#RRGGBB`` colour."""
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast_ratio(foreground: str, background: str) -> float:
    """WCAG contrast ratio between two colours (1.0 to 21.0)."""
    l1, l2 = sorted((relative_luminance(foreground),
                     relative_luminance(background)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


# ------------------------------------------------------------------ fonts
def pick_family(root: tk.Misc, candidates: tuple[str, ...]) -> str:
    """First installed font family from ``candidates`` (Tk default if none)."""
    available = {f.lower() for f in tkfont.families(root)}
    for family in candidates:
        if family.lower() in available:
            return family
    return tkfont.nametofont("TkDefaultFont", root).actual("family")


class Fonts:
    """Named fonts used across the interface."""

    def __init__(self, root: tk.Misc):
        sans = pick_family(root, _SANS)
        mono = pick_family(root, _MONO)
        self.body = tkfont.Font(root, family=sans, size=10)
        self.bold = tkfont.Font(root, family=sans, size=10, weight="bold")
        self.small = tkfont.Font(root, family=sans, size=9)
        self.small_bold = tkfont.Font(root, family=sans, size=9, weight="bold")
        self.micro = tkfont.Font(root, family=sans, size=8, weight="bold")
        self.title = tkfont.Font(root, family=sans, size=14, weight="bold")
        self.brand = tkfont.Font(root, family=sans, size=13, weight="bold")
        self.kpi = tkfont.Font(root, family=mono, size=19, weight="bold")
        self.mono = tkfont.Font(root, family=mono, size=10)
        self.mono_small = tkfont.Font(root, family=mono, size=8, weight="bold")
        tkfont.nametofont("TkDefaultFont", root).configure(family=sans, size=10)
        tkfont.nametofont("TkTextFont", root).configure(family=sans, size=10)


# ----------------------------------------------------------------- styles
def apply_theme(root: tk.Misc, name: str, fonts: Fonts) -> dict[str, str]:
    """Configure every ttk style for palette ``name`` and return the palette."""
    p = PALETTES[name]
    style = ttk.Style(root)
    style.theme_use("clam")
    root.configure(background=p["bg"])

    def frame(style_name, bg, border=None):
        style.configure(style_name, background=bg, borderwidth=1 if border else 0,
                        relief="solid" if border else "flat",
                        bordercolor=border or bg, lightcolor=border or bg,
                        darkcolor=border or bg)

    frame("TFrame", p["bg"])
    frame("App.TFrame", p["bg"])
    frame("Header.TFrame", p["card"], p["border"])
    frame("Card.TFrame", p["card"], p["border"])
    frame("Plain.TFrame", p["card"])
    frame("Panel.TFrame", p["card"], p["border"])
    frame("Seg.TFrame", p["bg"], p["border"])
    for kind in FEEDBACK_KINDS:
        frame(f"{kind}.Feedback.TFrame", p[f"{kind}_bg"], p[f"{kind}_border"])

    def label(style_name, bg, fg, font, **extra):
        style.configure(style_name, background=bg, foreground=fg, font=font, **extra)

    label("TLabel", p["bg"], p["text"], fonts.body)
    label("Card.TLabel", p["card"], p["text"], fonts.body)
    label("CardBold.TLabel", p["card"], p["text"], fonts.bold)
    label("Muted.TLabel", p["card"], p["muted"], fonts.small)
    label("Secondary.TLabel", p["card"], p["text2"], fonts.small)
    label("Brand.TLabel", p["card"], p["text"], fonts.brand)
    label("Logo.TLabel", p["accent"], p["accent_text"], fonts.brand, anchor="center",
          padding=(7, 1))
    label("Title.TLabel", p["card"], p["text"], fonts.title)
    label("Caption.TLabel", p["card"], p["muted"], fonts.micro)
    label("Kpi.TLabel", p["card"], p["text"], fonts.kpi)
    label("KpiSub.TLabel", p["card"], p["text2"], fonts.small)
    label("Badge.TLabel", p["card"], p["text"], fonts.mono_small, padding=(6, 2),
          borderwidth=1, relief="solid", bordercolor=p["border_strong"])
    label("AccentBadge.TLabel", p["accent_soft"], p["accent"] if name == LIGHT else p["info_fg"],
          fonts.mono_small, padding=(6, 2))
    label("Field.TLabel", p["card"], p["text"], fonts.small_bold)
    label("Required.TLabel", p["card"], p["error_fg"], fonts.small_bold)
    label("Hint.TLabel", p["card"], p["muted"], fonts.small)
    label("FieldError.TLabel", p["card"], p["error_fg"], fonts.small)
    label("Status.TLabel", p["card"], p["text2"], fonts.small)
    label("Footer.TLabel", p["card"], p["muted"], fonts.mono)
    label("Empty.TLabel", p["card"], p["muted"], fonts.body, anchor="center", justify="center")
    label("Placeholder.TLabel", p["input"], p["muted"], fonts.body)
    for kind in FEEDBACK_KINDS:
        label(f"{kind}.Feedback.TLabel", p[f"{kind}_bg"], p[f"{kind}_fg"], fonts.small)
        label(f"{kind}.FeedbackTitle.TLabel", p[f"{kind}_bg"], p[f"{kind}_fg"], fonts.small_bold)
        label(f"{kind}.Pill.TLabel", p[f"{kind}_bg"], p[f"{kind}_fg"], fonts.mono_small,
              padding=(8, 3), borderwidth=1, relief="solid", bordercolor=p[f"{kind}_border"])

    # Buttons ---------------------------------------------------------
    def button(style_name, bg, fg, border, hover, font=fonts.bold, padding=(14, 7),
               pressed=None, disabled_fg=None):
        style.configure(style_name, background=bg, foreground=fg, font=font,
                        padding=padding, borderwidth=1, relief="solid",
                        bordercolor=border, lightcolor=border, darkcolor=border,
                        focuscolor=fg, focusthickness=1, anchor="center", width=-4)
        style.map(style_name,
                  background=[("disabled", p["input_disabled"]), ("pressed", pressed or hover),
                              ("active", hover)],
                  foreground=[("disabled", disabled_fg or p["muted"])],
                  bordercolor=[("focus", p["accent"])],
                  lightcolor=[("focus", p["accent"])], darkcolor=[("focus", p["accent"])])

    button("TButton", p["card"], p["text"], p["border_strong"], p["row_alt"])
    button("Primary.TButton", p["accent"], p["accent_text"], p["accent"], p["accent_hover"])
    button("Secondary.TButton", p["card"], p["text"], p["border_strong"], p["row_alt"])
    button("Danger.TButton", p["error_bg"], p["error_fg"], p["error_border"],
           p["error_border"] if name == LIGHT else p["error_border"])
    button("Chip.TButton", p["card"], p["text2"], p["border"], p["row_alt"],
           font=fonts.small, padding=(8, 2))
    button("Icon.TButton", p["card"], p["text2"], p["border"], p["row_alt"],
           font=fonts.bold, padding=(9, 4))
    button("Nav.TButton", p["bg"], p["text2"], p["bg"], p["border"],
           font=fonts.bold, padding=(16, 5))
    button("NavActive.TButton", p["card"], p["accent"] if name == LIGHT else p["info_fg"],
           p["border"], p["card"], font=fonts.bold, padding=(16, 5))

    # Inputs ----------------------------------------------------------
    for style_name, border in (("TEntry", p["border_strong"]), ("Invalid.TEntry", p["error_fg"])):
        style.configure(style_name, fieldbackground=p["input"], foreground=p["text"],
                        insertcolor=p["text"], bordercolor=border, lightcolor=border,
                        darkcolor=border, padding=(9, 6), selectbackground=p["select"],
                        selectforeground=p["text"])
        style.map(style_name,
                  fieldbackground=[("disabled", p["input_disabled"]), ("readonly", p["input_disabled"])],
                  foreground=[("disabled", p["muted"])],
                  bordercolor=[("focus", p["accent"] if border == p["border_strong"] else border)],
                  lightcolor=[("focus", p["accent"] if border == p["border_strong"] else border)])
    for style_name, border in (("TCombobox", p["border_strong"]), ("Invalid.TCombobox", p["error_fg"])):
        style.configure(style_name, fieldbackground=p["input"], background=p["card"],
                        foreground=p["text"], arrowcolor=p["text2"], bordercolor=border,
                        lightcolor=border, darkcolor=border, padding=(9, 5),
                        selectbackground=p["input"], selectforeground=p["text"])
        style.map(style_name,
                  fieldbackground=[("readonly", p["input"])],
                  foreground=[("readonly", p["text"])],
                  selectbackground=[("readonly", p["input"])],
                  selectforeground=[("readonly", p["text"])],
                  bordercolor=[("focus", p["accent"] if border == p["border_strong"] else border)],
                  background=[("active", p["row_alt"])])
    # Drop-down lists of comboboxes created from now on.
    root.option_add("*TCombobox*Listbox.background", p["card"])
    root.option_add("*TCombobox*Listbox.foreground", p["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", p["select"])
    root.option_add("*TCombobox*Listbox.selectForeground", p["text"])
    root.option_add("*TCombobox*Listbox.font", fonts.body)

    # Table -----------------------------------------------------------
    style.configure("Treeview", background=p["card"], fieldbackground=p["card"],
                    foreground=p["text"], rowheight=38, borderwidth=0, relief="flat",
                    font=fonts.body, bordercolor=p["card"], lightcolor=p["card"],
                    darkcolor=p["card"])
    style.map("Treeview", background=[("selected", p["select"])],
              foreground=[("selected", p["text"])])
    style.configure("Treeview.Heading", background=p["card"], foreground=p["muted"],
                    font=fonts.micro, relief="flat", borderwidth=1, padding=(10, 9),
                    bordercolor=p["border"], lightcolor=p["card"], darkcolor=p["border"])
    style.map("Treeview.Heading", background=[("active", p["row_alt"])],
              foreground=[("active", p["text"])])
    style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    style.configure("TScrollbar", background=p["border_strong"], troughcolor=p["card"],
                    bordercolor=p["card"], arrowcolor=p["muted"])
    style.configure("Vertical.TScrollbar", background=p["border_strong"], troughcolor=p["card"],
                    bordercolor=p["card"], lightcolor=p["border_strong"],
                    darkcolor=p["border_strong"], arrowcolor=p["muted"], gripcount=0, width=10)
    style.map("Vertical.TScrollbar", background=[("active", p["muted"])])
    style.configure("TSeparator", background=p["border"])
    return p


def style_combobox_popdown(combobox: ttk.Combobox, palette: dict[str, str]) -> None:
    """Recolour the drop-down list of an existing combobox (after a theme change)."""
    try:
        popdown = combobox.tk.call("ttk::combobox::PopdownWindow", combobox)
        combobox.tk.call(f"{popdown}.f.l", "configure",
                         "-background", palette["card"], "-foreground", palette["text"],
                         "-selectbackground", palette["select"],
                         "-selectforeground", palette["text"])
    except tk.TclError:
        pass  # popdown not created yet: option_add covers it
