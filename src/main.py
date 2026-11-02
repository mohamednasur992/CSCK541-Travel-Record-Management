import sys
import os
import atexit
import tkinter as tk

# Ensure 'src' is in Python's path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

# Standard package imports
from record.record import RecordManager
from gui.main_window import MainApplicationWindow

def main():
    print("Initializing Specialist Travel Agent Record Management System...")

    # Check for and load existing records on startup
    db_path = os.path.join(os.path.dirname(__file__), "record", "record.jsonl")
    manager = RecordManager(filepath=db_path)
    print(f"Startup check complete: Loaded {len(manager.records)} record(s) from storage.")

    # Register an exit handler to automatically save records when the app closes
    atexit.register(manager.save_to_file)

    # 3. Launch GUI Application
    try:
        # 2. Instantiate the main window, passing the record manager to it
        '''root = MainApplicationWindow(manager) (got broken after the uniqueness solution)'''
        root = tk.Tk()  # Create the root window first
        app = MainApplicationWindow(root, manager)
        root.mainloop()  # Start the application loop

        # 3. Start the Tkinter event loop (this replaces the temporary print/input lines)
        root.mainloop()

    except KeyboardInterrupt:
        print("\nShutdown signal received.")
    finally:
        # Ensure final save execution on exit
        manager.save_to_file()
        print("Records successfully saved to file system. Goodbye!")


if __name__ == "__main__":
    main()