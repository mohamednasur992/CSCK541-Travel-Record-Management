"""Main entry point for the Specialist Travel Agent Record Management System."""
import sys
import os
import atexit
import tkinter as tk

# Standard package imports
from record.record import RecordManager  # pylint: disable=import-error
from gui.main_window import MainApplicationWindow  # pylint: disable=import-error

# Ensure 'src' is in Python's path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

def main():
    """Initialise the data manager and configure system exit hooks."""
    print("Initialising Specialist Travel Agent Record Management System...")

    # Check for and load existing records on startup
    db_path = os.path.join(str(os.path.dirname(__file__)), "record", "record.jsonl")
    manager = RecordManager(filepath=db_path)
    print(f"Startup check complete: Loaded {len(manager.records)} record(s) from storage.")

    # Register an exit handler to automatically save records when the app closes
    atexit.register(manager.save_to_file)

    # Launch GUI Application
    try:
        root = tk.Tk()  # Create the root window first
        # pylint: disable=unused-variable
        _app = MainApplicationWindow(root, manager)
        root.mainloop()  # Start the application loop

    except KeyboardInterrupt:
        print("\nShutdown signal received.")
    finally:
        # Ensure final save execution on exit
        manager.save_to_file()
        print("Records successfully saved to file system. Goodbye!")

if __name__ == "__main__":
    main()
