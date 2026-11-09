"""Main entry point for the Specialist Travel Agent Record Management System."""
import sys
import os
import atexit
import tkinter as tk

# Import the application's record-management and GUI components.
from record.record import RecordManager  # pylint: disable=import-error
from gui.main_window import MainApplicationWindow  # pylint: disable=import-error

# Add the source directory to the module search path when the application
# is launched directly from main.py.
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

def main():
    """Initialise record storage, launch the GUI, and manage safe shutdown."""
    print("Initialising Specialist Travel Agent Record Management System...")

    # Build the path to the application's persistent .JSONL record store.
    db_path = os.path.join(str(os.path.dirname(__file__)), "record", "record.jsonl")

    # Initialise the record manager and load any previously saved records.
    manager = RecordManager(filepath=db_path)
    print(f"Startup check complete: Loaded "
          f"{len(manager.records)} record(s) from storage.")

    # Register a fallback save operation for normal interpreter shutdown.
    atexit.register(manager.save_to_file)

    try:
        # Create the Tkinter root window and connect the GUI to the record manager.
        root = tk.Tk()

        # Keep a reference to the main window for the lifetime of the application.
        # pylint: disable=unused-variable
        _app = MainApplicationWindow(root, manager)

        # Hand control to Tkinter until the application window is closed.
        root.mainloop()

    except KeyboardInterrupt:
        # Allow a clean shutdown when the program is interrupted from the terminal.
        print("\nShutdown signal received.")

    finally:
        # Perform a final explicit save before the application exits.
        manager.save_to_file()
        print("Records successfully saved to file system. Goodbye!")

if __name__ == "__main__":
    main()
