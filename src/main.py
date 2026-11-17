"""Main entry point for the Specialist Travel Agent Record Management System."""
import sys
import os
import atexit

# Ensure 'src' is in Python's path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

# pylint: disable=wrong-import-position, import-error
from record.record import RecordManager
from gui.launcher import run, webview_available


def main():
    """Initialise the data manager, register the exit hook and open the UI."""
    print("Initialising Specialist Travel Agent Record Management System...")

    if not webview_available():
        print(
            "The HTML interface needs the 'pywebview' package.\n"
            "Install it with:  pip install -r requirements.txt",
            file=sys.stderr,
        )
        return 2

    # Check for and load existing records on startup
    db_path = os.path.join(CURRENT_DIR, "record", "record.jsonl")
    manager = RecordManager(filepath=db_path)
    print(f"Startup check complete: Loaded {len(manager.records)} record(s) from storage.")

    # Register an exit handler to automatically save records when the app closes
    atexit.register(manager.save_to_file)

    try:
        return run(manager)
    except KeyboardInterrupt:
        print("\nShutdown signal received.")
        return 0
    finally:
        # Ensure final save execution on exit
        manager.save_to_file()
        print("Records successfully saved to file system. Goodbye!")


if __name__ == "__main__":
    sys.exit(main())
