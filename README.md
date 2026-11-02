# Specialist Travel Agent Record Management System

A GUI-based Python application designed for travel agents to create, view, manage, and process travel bookings and customer records efficiently. Built using Python, Tkinter, and Pillow (PIL).

---

## Features

* **Interactive GUI Interface:** Built with Tkinter for a clean desktop user experience.
* **Record Management:** Add, update, view, and organize customer travel bookings.
* **Logo & Visual Customization:** Image support for branding and custom UI styling using Pillow (`PIL`).
* **Modular Architecture:** Structured separation between the GUI, record handling logic, and entry scripts.

---

## Project Structure

```text
CSCK541-Travel-Record-Management/

src/
    gui/
        __init__.py
        main_window.py       # Main application interface & layout
    record/
        init__.py
        record.py            # RecordManager and data handling logic
        record.jsonl         # Record storage
    main.py                  # Entry point script to launch the application
    assets
        logo.png             # Logo for the application
.gitignore
README.md                    # Project documentation
requirements.txt             # Project dependencies
```

---

## Requirements

* **Python Version:** 3.8 or higher
* **Third-Party Libraries:**
  * `Pillow` (PIL) — Image processing for icons/logos

---

## Installation & Setup

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/mohamednasur992/CSCK541-Travel-Record-Management.git
   cd CSCK541-Travel-Record-Management
   ```

2. **Create and Activate a Virtual Environment (Optional but Recommended):**
   * **Windows:**
     ```bash
     python -m venv .venv
     .venv\Scripts\activate
     ```
   * **macOS/Linux:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   *(Alternatively, install Pillow directly: `pip install Pillow`)*

4. **Mark `src` as Sources Root in PyCharm:**
   * Right-click the `src` folder in PyCharm's Project sidebar.
   * Navigate to **Mark Directory as** -> **Sources Root**.

---

## Running the Application

To launch the application, execute the `main.py` entry script from the root or `src` directory:

```bash
python src/main.py
```

---

## Authors & Acknowledgments
Developed as part of the CSCK541 Module Coursework.