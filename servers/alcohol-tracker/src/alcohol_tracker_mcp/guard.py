"""The safety layer between an AI and the tracker database.

What an AI can do through this module, and nothing more:

* read records (read-only connections);
* log whole drink presets, after a two-step prepare -> user says yes -> confirm;
* undo doses it logged itself, recently, if nobody has touched them since.

It cannot edit or delete anything else. That is enforced three ways: there is simply no code path for it, the
write connection carries a SQLite authorizer that refuses every statement except the few this module needs, and every
write is preceded by a database backup.
"""

from __future__ import annotations

import json
import re
import secrets
import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta
from difflib import get_close_matches
from pathlib import Path
from typing import Callable

from alcohol_tracker_mcp import config
from alcohol_tracker_mcp.model import (
    DrinkPreset,
    Ingestion,
    estimate_bac,
    simulate_active_drinks,
)
from alcohol_tracker_mcp.model_settings import EstimateSettings

_LEDGER_SCHEMA = """
CREATE TABLE IF NOT EXISTS assistant_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ingestion_id INTEGER NOT NULL,
    proposal_id TEXT NOT NULL,
    preset_name TEXT NOT NULL,
    snapshot TEXT NOT NULL,
    created_at TEXT NOT NULL,
    undone_at TEXT
);
"""

_YES_START = {"yes", "yeah", "yep", "yup", "sure", "ok", "okay", "confirm", "correct", "affirmative", "go", "do", "please", "log", "undo", "that", "that's", "thats", "right"}
_YES_FILLER = _YES_START | {"it", "ahead", "is", "i", "do", "so", "thanks", "thank", "you"}
_NEGATE = {"no", "nope", "nah", "dont", "don't", "not", "cancel", "stop", "wait", "never", "negative", "hold", "but", "maybe"}


class DoseError(Exception):
    """A refusal that is safe to read back to the user."""


def user_said_yes(reply: str) -> bool:
    """A clear yes: starts with an affirmative, uses only affirmative filler, and contains no negation."""
    words = re.findall(r"[a-z']+", reply.lower().replace("’", "'"))
    if not words or any(w in _NEGATE for w in words):
        return False
    return words[0] in _YES_START and all(w in _YES_FILLER for w in words)


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z]+|\d+(?:\.\d+)?", text.lower())


def resolve_preset(query: str, presets: list[DrinkPreset]) -> DrinkPreset:
    """Match what the user said to exactly one saved preset, or raise DoseError listing the candidates."""
    if not presets:
        raise DoseError("There are no drink presets saved in the tracker.")
    q = query.strip().lower()
    for p in presets:
        if p.name.lower() == q:
            return p
    q_tokens = [t for t in _tokens(q) if t not in {"a", "an", "the", "of", "some", "my"}]
    if not q_tokens:
        raise DoseError("Which preset? " + _names(presets))
    q_nums = {t for t in q_tokens if t[0].isdigit()}
    q_words = {t for t in q_tokens if not t[0].isdigit()}
    scored: list[tuple[float, DrinkPreset]] = []
    for p in presets:
        toks = _tokens(p.name)
        nums = {t for t in toks if t[0].isdigit()}
        words = {t for t in toks if not t[0].isdigit() and t not in {"oz"}}
        if q_words and not q_words <= words:
            continue
        if not q_nums <= nums:
            continue
        scored.append((len(q_words) / max(len(words), 1) + (0.1 if q_nums else 0.0), p))
    if scored:
        best = max(s for s, _ in scored)
        top = [p for s, p in scored if s == best]
        if len(top) == 1:
            return top[0]
        raise DoseError(f"'{query}' matches more than one preset: {_names(top)}. Ask which one.")
    close = get_close_matches(q, [p.name.lower() for p in presets], n=2, cutoff=0.75)
    if len(close) == 1:
        return next(p for p in presets if p.name.lower() == close[0])
    raise DoseError(f"No preset matches '{query}'. Presets: {_names(presets)}.")


def _names(presets: list[DrinkPreset]) -> str:
    return "; ".join(p.name for p in presets)


@dataclass
class Proposal:
    id: str
    preset: DrinkPreset
    quantity: int
    occurred_at: datetime
    created: float
    warnings: list[str]
    standard_drinks: float
    projected_peak_bac: float

    def readback(self) -> str:
        p = self.preset
        when = "now" if abs((datetime.now() - self.occurred_at).total_seconds()) < 90 else f"at {self.occurred_at:%I:%M %p}".replace(" 0", " ")
        return f"{self.quantity} x {p.name} ({p.amount:g} {'shot' if p.unit == 'shots' else 'fl oz'}, {p.abv_percent:g}% ABV), {when}"


class Guard:
    def __init__(
        self,
        db_path: Path | None = None,
        *,
        now: Callable[[], datetime] = datetime.now,
        monotonic: Callable[[], float] = time.monotonic,
        backups: Path | None = None,
        settings: EstimateSettings | None = None,
        limits: config.WarningLimits | None = None,
    ) -> None:
        self.db_path = Path(db_path or config.default_db_path())
        self._now, self._mono = now, monotonic
        self.backups = backups or config.backup_dir()
        self._settings = settings
        self._limits = limits
        self._proposals: dict[str, Proposal] = {}
        self._allow_delete = False
        with closing(sqlite3.connect(self.db_path, timeout=10)) as c:
            c.executescript(_LEDGER_SCHEMA)

    # ---- connections ---------------------------------------------------------
    def reader(self) -> sqlite3.Connection:
        c = sqlite3.connect(f"file:{self.db_path.as_posix()}?mode=ro", uri=True, timeout=10)
        c.row_factory = sqlite3.Row
        return c

    def _writer(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.db_path, timeout=10)
        c.row_factory = sqlite3.Row
        c.set_authorizer(self._authorize)
        return c

    def _authorize(self, action, arg1, arg2, dbname, source):
        ok, deny = sqlite3.SQLITE_OK, sqlite3.SQLITE_DENY
        if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_TRANSACTION, sqlite3.SQLITE_SAVEPOINT):
            return ok
        if action == sqlite3.SQLITE_INSERT and arg1 in ("ingestions", "assistant_log"):
            return ok
        if action == sqlite3.SQLITE_UPDATE and arg1 in ("assistant_log", "sqlite_sequence"):
            return ok
        if action == sqlite3.SQLITE_DELETE and arg1 == "ingestions" and self._allow_delete:
            return ok
        return deny

    # ---- reads ---------------------------------------------------------------
    def presets(self) -> list[DrinkPreset]:
        with closing(self.reader()) as c:
            rows = c.execute("SELECT * FROM drink_presets ORDER BY name COLLATE NOCASE").fetchall()
        return [DrinkPreset(int(r["id"]), r["name"], float(r["amount"]), r["unit"], float(r["abv_percent"])) for r in rows]

    def ingestions(self, since: datetime | None = None, consumer: str | None = config.CONSUMER) -> list[Ingestion]:
        sql, args = "SELECT * FROM ingestions", []
        clauses = []
        if since is not None:
            clauses.append("occurred_at >= ?")
            args.append(since.isoformat(timespec="seconds"))
        if consumer:
            clauses.append("consumer = ?")
            args.append(consumer)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        with closing(self.reader()) as c:
            rows = c.execute(sql + " ORDER BY occurred_at, id", args).fetchall()
        return [_row_to_ingestion(r) for r in rows]

    def settings(self) -> EstimateSettings:
        return self._settings or config.load_estimate_settings()

    def limits(self) -> config.WarningLimits:
        return self._limits or config.load_limits()

    def ai_flags(self, ids: list[int]) -> set[int]:
        if not ids:
            return set()
        with closing(self.reader()) as c:
            marks = ",".join("?" * len(ids))
            rows = c.execute(f"SELECT ingestion_id FROM assistant_log WHERE undone_at IS NULL AND ingestion_id IN ({marks})", ids).fetchall()
        return {int(r[0]) for r in rows}

    # ---- step 1: prepare (writes nothing) ------------------------------------
    def prepare(self, drink: str, quantity: int = 1, minutes_ago: float = 0) -> Proposal:
        now = self._now()
        if isinstance(quantity, bool) or int(quantity) != quantity or not 1 <= int(quantity) <= config.MAX_QUANTITY_PER_DOSE:
            raise DoseError(f"Quantity must be a whole number from 1 to {config.MAX_QUANTITY_PER_DOSE}. For more, the user adds them in the app.")
        quantity = int(quantity)
        if not 0 <= float(minutes_ago) <= config.MAX_BACKDATE_MINUTES:
            raise DoseError("I can only log a drink from the last 24 hours, not the future. Older drinks go in the app.")
        self._check_rate(now, quantity)
        preset = resolve_preset(drink, self.presets())
        when = (now - timedelta(minutes=float(minutes_ago))).replace(microsecond=0)

        settings, limits = self.settings(), self.limits()
        dose = Ingestion(None, when, preset.amount, preset.unit, preset.abv_percent, preset.name, consumer=config.CONSUMER)
        std = dose.standard_drinks(settings) * quantity
        history = self.ingestions(since=now - timedelta(hours=48))
        projected = history + [dose] * quantity
        peak = self._peak_bac(projected, min(when, now), now, settings)

        warnings: list[str] = []
        day_total = sum(i.standard_drinks(settings) for i in history if i.occurred_at.date() == when.date()) + std
        if day_total >= limits.daily_standard_drinks:
            warnings.append(f"That brings {when:%A}'s total to about {day_total:.1f} standard drinks (your limit is {limits.daily_standard_drinks:g}).")
        if peak >= limits.peak_bac_percent:
            warnings.append(f"Estimated peak BAC would reach about {peak:.3f}% (your limit is {limits.peak_bac_percent:g}%). This is a rough estimate, not a measurement.")
        hour_ago = max(when, now) - timedelta(hours=1)
        pace = sum(i.standard_drinks(settings) for i in history if hour_ago <= i.occurred_at <= max(when, now)) + std
        if pace >= limits.drinks_per_hour:
            warnings.append(f"That is about {pace:.1f} standard drinks within an hour (your pace limit is {limits.drinks_per_hour:g}).")
        recent = self._recent_ai_same_preset(now, preset.name)
        if recent:
            warnings.append(f"The assistant already logged {preset.name} {recent} minute(s) ago; check this isn't a repeat.")

        self._expire(now)
        if len(self._proposals) >= 10:
            raise DoseError("Too many unconfirmed drinks pending. Ask the user what they want to log.")
        prop = Proposal(secrets.token_hex(3), preset, quantity, when, self._mono(), warnings, std, peak)
        self._proposals[prop.id] = prop
        return prop

    # ---- step 2: confirm (the only way an AI adds a record) -------------------
    def confirm(self, proposal_id: str, user_reply: str) -> dict:
        now = self._now()
        self._expire(now)
        prop = self._proposals.get(proposal_id.strip())
        if prop is None:
            raise DoseError("That drink was not prepared, or it expired. Prepare it again and ask the user to confirm.")
        if not user_said_yes(user_reply):
            raise DoseError("The user's reply was not a clear yes, so nothing was logged. Ask them again, or drop it.")
        if self._mono() - prop.created < config.MIN_CONFIRM_DELAY_SECONDS:
            raise DoseError("Read the drink back to the user and wait for their answer before confirming. Nothing was logged.")
        self._check_rate(now, prop.quantity)
        del self._proposals[prop.id]  # single use: a repeated confirm can never log twice

        self.backup("prewrite")
        p, stamp = prop.preset, now.isoformat(timespec="seconds")
        ids = []
        with closing(self._writer()) as c:
            with c:
                for _ in range(prop.quantity):
                    cur = c.execute(
                        "INSERT INTO ingestions (occurred_at, amount, unit, abv_percent, label, notes, duration_minutes, consumer, created_at, updated_at)"
                        " VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?)",
                        (prop.occurred_at.isoformat(timespec="seconds"), p.amount, p.unit, p.abv_percent, p.name, f"{config.AI_TAG} voice assistant", config.CONSUMER, stamp, stamp),
                    )
                    snap = json.dumps({"occurred_at": prop.occurred_at.isoformat(timespec="seconds"), "amount": p.amount, "unit": p.unit, "abv_percent": p.abv_percent, "label": p.name, "created_at": stamp})
                    c.execute("INSERT INTO assistant_log (ingestion_id, proposal_id, preset_name, snapshot, created_at) VALUES (?, ?, ?, ?, ?)", (cur.lastrowid, prop.id, p.name, snap, stamp))
                    ids.append(int(cur.lastrowid))
        return {"logged": prop.readback(), "entry_ids": ids, "standard_drinks": round(prop.standard_drinks, 2), "warnings": prop.warnings, "undo": f"The user can say 'undo' within {config.UNDO_WINDOW_MINUTES} minutes."}

    # ---- undo (own, recent, untouched entries only) ---------------------------
    def undo_last(self, user_reply: str) -> dict:
        if not user_said_yes(user_reply):
            raise DoseError("Ask the user to confirm the undo with a clear yes. Nothing was removed.")
        now = self._now()
        cutoff = (now - timedelta(minutes=config.UNDO_WINDOW_MINUTES)).isoformat(timespec="seconds")
        with closing(self.reader()) as c:
            last = c.execute("SELECT proposal_id FROM assistant_log WHERE undone_at IS NULL AND created_at >= ? ORDER BY id DESC LIMIT 1", (cutoff,)).fetchone()
            if last is None:
                raise DoseError(f"Nothing to undo: the assistant has no un-undone entry from the last {config.UNDO_WINDOW_MINUTES} minutes. Older entries are changed in the app.")
            batch = c.execute("SELECT * FROM assistant_log WHERE proposal_id = ? AND undone_at IS NULL AND created_at >= ?", (last[0], cutoff)).fetchall()
            live = {int(r["id"]): r for r in c.execute(f"SELECT * FROM ingestions WHERE id IN ({','.join('?' * len(batch))})", [b["ingestion_id"] for b in batch])}
        removable, skipped = [], []
        for b in batch:
            row, snap = live.get(int(b["ingestion_id"])), json.loads(b["snapshot"])
            if row is None:
                skipped.append(f"entry {b['ingestion_id']} is already gone")
            elif not _untouched(row, snap):
                skipped.append(f"entry {b['ingestion_id']} was edited in the app, so it was left alone")
            else:
                removable.append(b)
        if removable:
            self.backup("prewrite")
            self._allow_delete = True
            try:
                with closing(self._writer()) as c:
                    with c:
                        for b in removable:
                            c.execute("DELETE FROM ingestions WHERE id = ? AND id IN (SELECT ingestion_id FROM assistant_log WHERE undone_at IS NULL)", (b["ingestion_id"],))
                            c.execute("UPDATE assistant_log SET undone_at = ? WHERE id = ?", (now.isoformat(timespec="seconds"), b["id"]))
            finally:
                self._allow_delete = False
        return {"removed": len(removable), "drink": removable[0]["preset_name"] if removable else None, "left_alone": skipped}

    # ---- helpers ---------------------------------------------------------------
    def backup(self, kind: str = "daily", keep: int = 30) -> Path | None:
        """Copy the database. 'daily' once per calendar day; 'prewrite' at most once per 10 minutes."""
        now = self._now()
        self.backups.mkdir(parents=True, exist_ok=True)
        existing = sorted(self.backups.glob(f"{kind}-*.db"))
        if existing:
            last = datetime.strptime(existing[-1].stem.split("-", 1)[1], "%Y%m%d-%H%M%S")
            if (kind == "daily" and last.date() == now.date()) or (kind != "daily" and now - last < timedelta(minutes=10)):
                return None
        target = self.backups / f"{kind}-{now:%Y%m%d-%H%M%S}.db"
        with closing(self.reader()) as src, closing(sqlite3.connect(target)) as dst:
            src.backup(dst)
        for old in sorted(self.backups.glob(f"{kind}-*.db"))[:-keep]:
            old.unlink(missing_ok=True)
        return target

    def _check_rate(self, now: datetime, adding: int) -> None:
        since = (now - timedelta(hours=1)).isoformat(timespec="seconds")
        with closing(self.reader()) as c:
            n = c.execute("SELECT COUNT(*) FROM assistant_log WHERE created_at >= ?", (since,)).fetchone()[0]
        if n + adding > config.MAX_AI_LOGS_PER_HOUR:
            raise DoseError(f"The assistant can log at most {config.MAX_AI_LOGS_PER_HOUR} drinks an hour as a safety limit. Add more in the app.")

    def _recent_ai_same_preset(self, now: datetime, name: str) -> int | None:
        since = (now - timedelta(minutes=3)).isoformat(timespec="seconds")
        with closing(self.reader()) as c:
            r = c.execute("SELECT created_at FROM assistant_log WHERE undone_at IS NULL AND preset_name = ? AND created_at >= ? ORDER BY id DESC LIMIT 1", (name, since)).fetchone()
        return max(int((now - datetime.fromisoformat(r[0])).total_seconds() // 60), 0) if r else None

    def _expire(self, now: datetime) -> None:
        cutoff = self._mono() - config.PROPOSAL_TTL_SECONDS
        for k in [k for k, p in self._proposals.items() if p.created < cutoff]:
            del self._proposals[k]

    @staticmethod
    def _peak_bac(ingestions: list[Ingestion], start: datetime, now: datetime, settings: EstimateSettings) -> float:
        first = min(i.occurred_at for i in ingestions)
        series = simulate_active_drinks(ingestions, min(first, start), now + timedelta(hours=3), settings, step_minutes=5)
        return max((estimate_bac(v, settings) for _, v in series), default=0.0)


def _row_to_ingestion(r: sqlite3.Row) -> Ingestion:
    return Ingestion(
        id=int(r["id"]),
        occurred_at=datetime.fromisoformat(r["occurred_at"]),
        amount=float(r["amount"]),
        unit=str(r["unit"]),
        abv_percent=float(r["abv_percent"]),
        label=str(r["label"]),
        notes=str(r["notes"]),
        duration_minutes=float(r["duration_minutes"]),
        consumer=str(r["consumer"]),
    )


def _untouched(row: sqlite3.Row, snap: dict) -> bool:
    return (
        row["updated_at"] == snap["created_at"]
        and row["occurred_at"] == snap["occurred_at"]
        and float(row["amount"]) == snap["amount"]
        and row["unit"] == snap["unit"]
        and float(row["abv_percent"]) == snap["abv_percent"]
        and row["label"] == snap["label"]
    )
