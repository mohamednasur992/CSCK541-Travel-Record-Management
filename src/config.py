"""Application-wide settings: names, file locations, window and logging options.

Everything that might need changing in one place lives here, so no module
hard-codes a path, size or format of its own.
"""

from pathlib import Path

# ---------------------------------------------------------------- identity
APP_NAME = "Specialist Travel Agent Record Management System"
APP_TITLE = f"{APP_NAME} — Group B"

# ---------------------------------------------------------------- locations
SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent
DATA_FILE = SRC_DIR / "record" / "record.jsonl"     # JSON Lines, one record per line
SETTINGS_FILE_NAME = "settings.json"                # display preferences, next to DATA_FILE
STATIC_DIR = SRC_DIR / "gui" / "static"
INDEX_FILE = STATIC_DIR / "index.html"

# ---------------------------------------------------------------- storage
FILE_ENCODING = "utf-8"
CORRUPT_BACKUP_SUFFIX = ".corrupt-{timestamp}"      # damaged data files are kept under this name
BACKUP_TIMESTAMP_FORMAT = "%Y%m%d-%H%M%S"

# ---------------------------------------------------------------- window
WINDOW_SIZE = (1440, 900)
MIN_WINDOW_SIZE = (400, 560)                        # narrow windows switch to the compact layout
WINDOW_BACKGROUND = "#F8FAFC"

# ---------------------------------------------------------------- logging
LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "travel_records.log"
LOG_FILE_MAX_BYTES = 1_000_000                      # rotate at about 1 MB ...
LOG_FILE_BACKUPS = 3                                # ... keeping three old files
LOG_FILE_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
LOG_CONSOLE_FORMAT = "%(levelname)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
CLIENT_ERROR_MAX_LENGTH = 2000                      # longest page error message written to the log

# ---------------------------------------------------------------- exit codes
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_MISSING_DEPENDENCY = 2
