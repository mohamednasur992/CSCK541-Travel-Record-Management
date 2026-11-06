# Specialist Travel Agent Record Management System

The Specialist Travel Agent Record Management System is a GUI-based Python application developed by Group B as part of the CSCK541 module coursework.

The application enables a specialist travel agent to create, view and manage three primary record types:

* Client Records
* Flight Records
* Airline Company Records

The system is developed using Python and Tkinter, with Pillow (PIL) used to support application branding and image handling.

---

## Features

* **Graphical User Interface:** Desktop interface developed using Tkinter.
* **Client Record Management:** Create, view and maintain client information.
* **Flight Record Management:** Manage flight-related information.
* **Airline Company Records:** Maintain information relating to airline companies.
* **Record Storage:** Application records are stored in JSON Lines (.jsonl) format.
* **Visual Branding:** Pillow provides image support for the Group B logo and other interface assets.
* **Modular Architecture:** GUI, record-management logic and application start-up responsibilities are separated into dedicated modules.

---

## Project Structure

```text
CSCK541-Travel-Record-Management/

src/
    gui/
        __init__.py
        main_window.py       # Main application interface and layout
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

The structure separates the GUI in main_window.py from the record-management logic in record.py, while main.py acts as the application's entry point.

---

## Requirements

* **Python Version:** 3.8 or higher
* **Third-Party Libraries:**
  * `Pillow` (PIL) — Image processing for icons/logos

**Install the required third-party dependencies with:**
   ```bash
   pip install -r requirements.txt
   ```

**Pillow can be installed directly:**
   ```bash
   pip install Pillow
   ```

---

## System Setup

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/mohamednasur992/CSCK541-Travel-Record-Management.git
   cd CSCK541-Travel-Record-Management
   ```

2. **Create a Virtual Environment:**

   Creating a virtual environment is recommended to isolate the project's dependencies

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

3. **Configure PyCharm**

   When using PyCharm:
   * Locate the src directory in the Project panel.
   * Right-click the `src` folder in PyCharm's Project sidebar.
   * Select Mark Directory as → Sources Root.

---

## Running the Application

To launch the application, execute the `main.py` entry script from the root or `src` directory:

```bash
python src/main.py
```

The application will open the graphical interface for managing the travel agent's records.

**Client Records**

   Stores information required to identify and manage the travel agent's clients.

**Flight Records**

   Stores information relating to available or recorded flights.

**Airline Company Records**

   Stores information about the airlines associated with flight records.

The GUI provides users with a consistent interface through which these records can be created, viewed and managed.

---

## Authors and Acknowledgments

   Developed by Group B
   
   * Mohamed Nasur, 
   * Moegamat Sheraad Jacobs, 
   * Syed Raza, and 
   * Mzanempi Abednego Maduna
   
   as part of the CSCK541 Module Coursework.