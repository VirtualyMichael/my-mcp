import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

SCHEMA = """
CREATE TABLE ingestions (id INTEGER PRIMARY KEY AUTOINCREMENT, occurred_at TEXT NOT NULL, amount REAL NOT NULL,
 unit TEXT NOT NULL, abv_percent REAL NOT NULL, label TEXT NOT NULL, notes TEXT NOT NULL DEFAULT '',
 duration_minutes REAL NOT NULL DEFAULT 0, consumer TEXT NOT NULL DEFAULT 'Me', created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE drink_presets (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, amount REAL NOT NULL,
 unit TEXT NOT NULL, abv_percent REAL NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
"""
PRESETS = [("Shot - 40%", 1, "shots", 40), ("Double shot - 40%", 2, "shots", 40), ("Beer - 12 oz 5%", 12, "fl_oz", 5),
           ("Strong beer - 16 oz 8%", 16, "fl_oz", 8), ("50% Shot", 1, "fl_oz", 50), ("4 Loko", 23.5, "fl_oz", 14)]


class Clock:
    def __init__(self):
        self.t = datetime(2026, 10, 21, 20, 0, 0)
        self.m = 1000.0

    def now(self):
        return self.t

    def mono(self):
        return self.m

    def advance(self, seconds):
        self.t += timedelta(seconds=seconds)
        self.m += seconds


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def guard(tmp_path, clock):
    from alcohol_tracker_mcp.config import WarningLimits
    from alcohol_tracker_mcp.guard import Guard
    from alcohol_tracker_mcp.model_settings import EstimateSettings

    db = tmp_path / "t.db"
    c = sqlite3.connect(db)
    c.executescript(SCHEMA)
    for n, a, u, p in PRESETS:
        c.execute("INSERT INTO drink_presets VALUES (NULL,?,?,?,?,'x','x')", (n, a, u, p))
    c.commit()
    c.close()
    return Guard(db, now=clock.now, monotonic=clock.mono, backups=tmp_path / "bk", settings=EstimateSettings(), limits=WarningLimits())


def count(g):
    c = sqlite3.connect(g.db_path)
    try:
        return c.execute("SELECT COUNT(*) FROM ingestions").fetchone()[0]
    finally:
        c.close()
