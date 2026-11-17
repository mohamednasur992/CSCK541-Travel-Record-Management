"""Main entry point for the Specialist Travel Agent Record Management System.

Run with ``python src/main.py``. Start-up checks for existing records,
opens the HTML interface, and saves every record again when the program
ends, however it ends (window closed, Ctrl+C or an unexpected error).
"""

import logging
import os
import sys

# Allow "python src/main.py" from the project root as well as from src/.
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

# pylint: disable=wrong-import-position, import-error
import config
from app_logging import setup_logging
from gui.launcher import run, webview_available
from record.errors import RecordStorageError
from record.record import RecordManager

logger = logging.getLogger("main")


def main(data_file=config.DATA_FILE, log_file=config.LOG_FILE):
    """Load the records, open the interface and save on exit; return an exit code."""
    log_path = setup_logging(log_file=log_file)
    logger.info("Starting %s.%s", config.APP_NAME, f" Log file: {log_path}" if log_path else "")

    if not webview_available():
        logger.error("The HTML interface needs the 'pywebview' package. "
                     "Install it with:  pip install -r requirements.txt")
        return config.EXIT_MISSING_DEPENDENCY

    manager = RecordManager(filepath=data_file)       # start-up check for existing records
    exit_code = config.EXIT_OK
    try:
        exit_code = run(manager, warnings=manager.load_warnings)
    except KeyboardInterrupt:
        logger.info("Shutdown requested from the keyboard.")
    except Exception:  # pylint: disable=broad-except
        logger.exception("The program stopped because of an unexpected error.")
        exit_code = config.EXIT_ERROR
    finally:
        # Final save, whatever happened above (the window also saves when it closes).
        try:
            manager.save_to_file()
        except RecordStorageError as exc:
            logger.error("Records could not be saved on exit: %s", exc)
            exit_code = config.EXIT_ERROR
    logger.info("Goodbye.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
