"""Paths, hard safety caps, user-tunable warning limits and the stored estimate settings (read-only)."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, fields
from pathlib import Path

from alcohol_tracker_mcp.model_settings import EstimateSettings

# Hard caps. These are code, not configuration: the AI and the limits file cannot raise them.
MAX_QUANTITY_PER_DOSE = 6
MAX_BACKDATE_MINUTES = 24 * 60
MAX_AI_LOGS_PER_HOUR = 12
UNDO_WINDOW_MINUTES = 10
PROPOSAL_TTL_SECONDS = 300
MIN_CONFIRM_DELAY_SECONDS = 2.0
AI_TAG = "[AI]"
CONSUMER = "Me"


def default_db_path() -> Path:
    """Where the Alcohol Tracker app keeps its database (ALCOHOL_TRACKER_DB overrides it)."""
    if os.environ.get("ALCOHOL_TRACKER_DB"):
        return Path(os.environ["ALCOHOL_TRACKER_DB"])
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "AlcoholTracker" / "alcohol_tracker.db"


def data_dir() -> Path:
    return default_db_path().parent


def backup_dir() -> Path:
    return data_dir() / "backups"


def reports_dir() -> Path:
    return data_dir() / "reports"


def limits_path() -> Path:
    return data_dir() / "assistant_limits.json"


@dataclass(frozen=True)
class WarningLimits:
    """Spoken heads-ups only. They never block a log; edit assistant_limits.json to change them."""

    daily_standard_drinks: float = 8.0
    peak_bac_percent: float = 0.08
    drinks_per_hour: float = 3.0


def load_limits(path: Path | None = None) -> WarningLimits:
    path = path or limits_path()
    defaults = WarningLimits()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return defaults
    values = {}
    for f in fields(WarningLimits):
        try:
            v = float(raw[f.name])
            if v > 0:
                values[f.name] = v
        except (KeyError, TypeError, ValueError):
            pass
    return WarningLimits(**{**defaults.__dict__, **values})


def load_estimate_settings() -> EstimateSettings:
    """The app's saved estimate settings (Windows registry via QSettings); defaults elsewhere or if unreadable."""
    defaults = EstimateSettings()
    if sys.platform != "win32":
        return defaults
    try:
        import winreg

        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Local\Alcohol Tracker\estimate")
    except OSError:
        return defaults
    values = {}
    with key:
        for f in fields(EstimateSettings):
            try:
                raw, _ = winreg.QueryValueEx(key, f.name)
                default = getattr(defaults, f.name)
                values[f.name] = type(default)(raw) if not isinstance(default, str) else str(raw)
            except (OSError, ValueError):
                pass
    return EstimateSettings(**{**defaults.__dict__, **values})
