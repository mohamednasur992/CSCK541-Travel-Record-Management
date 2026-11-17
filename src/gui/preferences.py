"""Display preferences chosen in the page (theme, contrast, effects, density, panel width).

They are kept in ``settings.json`` beside the records file. Only known names
and values are accepted; a missing or damaged file simply means the defaults.
"""

import json
import logging
import os
import tempfile
from pathlib import Path

import config

logger = logging.getLogger(__name__)

# Allowed values for each preference; the first value is the default.
PREFERENCE_CHOICES = {
    "theme": ("system", "light", "dark"),
    "contrast": ("system", "standard", "high"),
    "effects": ("system", "standard", "low"),
    "density": ("comfortable", "compact"),
}
PANEL_WIDTH = "panel_width"
PANEL_WIDTH_RANGE = (360, 720)
DEFAULT_PANEL_WIDTH = 440
DEFAULT_PREFERENCES = {**{name: values[0] for name, values in PREFERENCE_CHOICES.items()},
                       PANEL_WIDTH: DEFAULT_PANEL_WIDTH}


def is_valid(name, value):
    """True when ``value`` is allowed for preference ``name``."""
    if name == PANEL_WIDTH:
        low, high = PANEL_WIDTH_RANGE
        return isinstance(value, int) and not isinstance(value, bool) and low <= value <= high
    return name in PREFERENCE_CHOICES and value in PREFERENCE_CHOICES[name]


class PreferenceStore:  # pylint: disable=too-few-public-methods  # a small store: load + set
    """Load, validate and save the display preferences."""

    def __init__(self, path):
        self.path = Path(path)
        self.values = self._load()

    def _load(self):
        values = dict(DEFAULT_PREFERENCES)
        try:
            stored = json.loads(self.path.read_text(encoding=config.FILE_ENCODING))
        except FileNotFoundError:
            return values
        except (OSError, ValueError) as exc:
            logger.warning("Display settings in %s ignored (%s); using defaults.", self.path, exc)
            return values
        if not isinstance(stored, dict):
            logger.warning("Display settings in %s are not an object; using defaults.", self.path)
            return values
        values.update({name: value for name, value in stored.items() if is_valid(name, value)})
        return values

    def set(self, name, value):
        """Apply one preference and write the file.

        Raises ``ValueError`` for an unknown name or value, and ``OSError`` if
        the file cannot be written (the value still applies for this session).
        """
        if not is_valid(name, value):
            raise ValueError(f"Unknown preference {name!r} or value {value!r}.")
        self.values[name] = value
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle, temp_name = tempfile.mkstemp(dir=self.path.parent, prefix=".settings-", suffix=".tmp")
        try:
            with os.fdopen(handle, "w", encoding=config.FILE_ENCODING) as stream:
                json.dump(self.values, stream, indent=2)
            os.replace(temp_name, self.path)
        except BaseException:
            os.unlink(temp_name)
            raise
        logger.info("Display preference %s set to %r.", name, value)
