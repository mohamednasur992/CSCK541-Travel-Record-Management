"""Centralised visual styles for the Travel Record Management System."""

from tkinter import ttk


def setup_styles(root):
    """Apply the application's shared colour palette and ttk widget styles."""

    style = ttk.Style()

    # Use the Clam theme because it supports consistent custom styling
    # across the application's ttk widgets.
    style.theme_use("clam")

    # Shared application palette keeps colours consistent across all GUI tabs.
    primary_color = "#1B365D"   # Deep navy
    background_color = "#F4F6F9"  # Soft off-white
    text_color = "#243B53"      # Dark slate
    tab_color = "#D9E2EC"       # Light slate
    white = "#FFFFFF"

    # Match the Tk root window with the ttk application background.
    root.configure(bg=background_color)

    # Establish shared defaults before applying component-specific styles.
    style.configure(
        ".",
        background=background_color,
        font=("Segoe UI", 10),
    )

    # Notebook styling visually separates the Client, Flight,
    # and Airline Company record-management views.
    style.configure(
        "TNotebook",
        background=background_color,
        borderwidth=0,
    )

    style.configure(
        "TNotebook.Tab",
        background=tab_color,
        foreground="#102A43",
        padding=[15, 8],
        font=("Segoe UI", 10, "bold"),
    )

    # Highlight the active record-management view using the primary brand colour.
    style.map(
        "TNotebook.Tab",
        background=[("selected", primary_color)],
        foreground=[("selected", white)],
    )

    # Use consistent section headings for grouped form controls.
    style.configure(
        "TLabelFrame",
        background=background_color,
        foreground=primary_color,
        font=("Segoe UI", 11, "bold"),
    )

    style.configure(
        "TLabel",
        background=background_color,
        foreground=text_color,
    )

    # Use the primary colour for application actions while retaining
    # a visible active state for user feedback.
    style.configure(
        "TButton",
        background=primary_color,
        foreground=white,
        font=("Segoe UI", 10, "bold"),
        padding=6,
    )

    style.map(
        "TButton",
        background=[("active", text_color)],
    )


    # Destructive actions must be visually distinct from ordinary actions.
    style.configure(
        "Danger.TButton",
        background="#B42318",
        foreground=white,
        font=("Segoe UI", 10, "bold"),
        padding=6,
    )
    style.map(
        "Danger.TButton",
        background=[
            ("pressed", "#7A1A14"),
            ("active", "#912018"),
            ("disabled", "#C8A5A1"),
        ],
        foreground=[("disabled", "#F7E8E6")],
    )

    style.configure(
        "Status.TLabel",
        background="#E8EDF3",
        foreground=text_color,
        font=("Segoe UI", 9),
    )
