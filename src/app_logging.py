"""Configure logging for the application.

Modules only call ``logging.getLogger(__name__)``; this function, called
once by ``main``, decides where the messages go:

* a rotating log file (``config.LOG_FILE``) with full detail and tracebacks;
* the console, for start-up and shutdown messages and any problem.

Personal data (names, addresses, phone numbers) is never logged;
records are identified by type and ID only.
"""

import logging
from logging.handlers import RotatingFileHandler

import config

_HANDLER_MARK = "_travel_records_handler"


def setup_logging(level=logging.INFO, log_file=config.LOG_FILE, console=True):
    """Attach the file and console handlers to the root logger (only once).

    Returns the log file path, or ``None`` when the file cannot be created
    (for example a read-only folder); logging then continues on the console.
    """
    root = logging.getLogger()
    root.setLevel(level)
    for handler in list(root.handlers):
        if getattr(handler, _HANDLER_MARK, False):     # called again: replace our handlers
            root.removeHandler(handler)
            handler.close()

    if console:
        stream = logging.StreamHandler()
        stream.setFormatter(logging.Formatter(config.LOG_CONSOLE_FORMAT))
        setattr(stream, _HANDLER_MARK, True)
        root.addHandler(stream)

    written_to = None
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(log_file, maxBytes=config.LOG_FILE_MAX_BYTES,
                                           backupCount=config.LOG_FILE_BACKUPS,
                                           encoding=config.FILE_ENCODING)
    except OSError as exc:
        logging.getLogger(__name__).warning(
            "Log file %s cannot be written (%s); logging to the console only.", log_file, exc)
    else:
        file_handler.setFormatter(logging.Formatter(config.LOG_FILE_FORMAT, config.LOG_DATE_FORMAT))
        setattr(file_handler, _HANDLER_MARK, True)
        root.addHandler(file_handler)
        written_to = log_file
    return written_to
