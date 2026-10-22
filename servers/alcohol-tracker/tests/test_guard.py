import sqlite3
from contextlib import closing

import pytest

from alcohol_tracker_mcp.guard import DoseError, resolve_preset, user_said_yes
from conftest import count


def test_yes_parsing():
    for ok in ("yes", "Yes please", "yeah", "yep, do it", "okay", "go ahead", "that's right"):
        assert user_said_yes(ok), ok
    for bad in ("", "no", "yes no wait", "don't", "maybe", "yes but cancel", "what", "sure not"):
        assert not user_said_yes(bad), bad


def test_preset_matching(guard):
    ps = guard.presets()
    assert resolve_preset("double shot", ps).name == "Double shot - 40%"
    assert resolve_preset("beer", ps).name == "Beer - 12 oz 5%"
    assert resolve_preset("50 shot", ps).name == "50% Shot"
    assert resolve_preset("4 loko", ps).name == "4 Loko"
    with pytest.raises(DoseError, match="more than one"):
        resolve_preset("shot", ps)
    with pytest.raises(DoseError, match="No preset"):
        resolve_preset("margarita", ps)


def test_prepare_writes_nothing(guard):
    p = guard.prepare("beer", 2)
    assert count(guard) == 0 and p.quantity == 2


def test_confirm_needs_wait_and_yes(guard, clock):
    p = guard.prepare("beer")
    with pytest.raises(DoseError, match="wait"):
        guard.confirm(p.id, "yes")
    clock.advance(5)
    with pytest.raises(DoseError, match="clear yes"):
        guard.confirm(p.id, "no")
    assert count(guard) == 0
    out = guard.confirm(p.id, "yes")
    assert count(guard) == 1 and out["entry_ids"]
    with pytest.raises(DoseError, match="not prepared"):
        guard.confirm(p.id, "yes")  # single use
    assert count(guard) == 1


def test_proposal_expires(guard, clock):
    p = guard.prepare("beer")
    clock.advance(400)
    with pytest.raises(DoseError, match="expired"):
        guard.confirm(p.id, "yes")


def test_bounds(guard):
    for q in (0, 7, 1.5, -1):
        with pytest.raises(DoseError):
            guard.prepare("beer", q)
    with pytest.raises(DoseError):
        guard.prepare("beer", 1, -5)
    with pytest.raises(DoseError):
        guard.prepare("beer", 1, 24 * 60 + 1)


def test_backdate_and_tag(guard, clock):
    p = guard.prepare("shot - 40", 1, 30)
    clock.advance(5)
    guard.confirm(p.id, "yes")
    with closing(guard.reader()) as c:
        r = c.execute("SELECT * FROM ingestions").fetchone()
    assert r["occurred_at"] == "2026-10-21T19:30:00" and "[AI]" in r["notes"] and r["consumer"] == "Me"


def test_rate_limit(guard, clock):
    for _ in range(2):
        p = guard.prepare("beer", 6)
        clock.advance(3)
        guard.confirm(p.id, "yes")
    with pytest.raises(DoseError, match="at most"):
        guard.prepare("beer")


def test_undo_own_recent_only(guard, clock):
    with closing(sqlite3.connect(guard.db_path)) as c:  # a user's own entry
        c.execute("INSERT INTO ingestions VALUES (NULL,'2026-10-21T19:00:00',1,'shots',40,'Shot','',0,'Me','x','x')")
        c.commit()
    p = guard.prepare("beer", 2)
    clock.advance(3)
    guard.confirm(p.id, "yes")
    assert count(guard) == 3
    with pytest.raises(DoseError):
        guard.undo_last("no")
    assert guard.undo_last("yes")["removed"] == 2
    assert count(guard) == 1  # the user's own entry survives
    with pytest.raises(DoseError, match="Nothing to undo"):
        guard.undo_last("yes")


def test_undo_window_and_edited(guard, clock):
    p = guard.prepare("beer")
    clock.advance(3)
    guard.confirm(p.id, "yes")
    with closing(sqlite3.connect(guard.db_path)) as c:  # user edits it in the app
        c.execute("UPDATE ingestions SET amount = 20, updated_at = 'later'")
        c.commit()
    out = guard.undo_last("yes")
    assert out["removed"] == 0 and "edited" in out["left_alone"][0] and count(guard) == 1
    p = guard.prepare("beer")
    clock.advance(3)
    guard.confirm(p.id, "yes")
    clock.advance(11 * 60)
    with pytest.raises(DoseError, match="Nothing to undo"):
        guard.undo_last("yes")


def test_write_connection_is_locked_down(guard, clock):
    p = guard.prepare("beer")
    clock.advance(3)
    guard.confirm(p.id, "yes")
    w = guard._writer()
    try:
        for sql in ("DELETE FROM ingestions", "UPDATE ingestions SET amount=0", "DROP TABLE ingestions", "DELETE FROM drink_presets",
                    "DROP TABLE drink_presets", "ALTER TABLE ingestions ADD COLUMN x", "DELETE FROM assistant_log", "UPDATE drink_presets SET abv_percent=0"):
            with pytest.raises(sqlite3.DatabaseError):
                w.execute(sql)
    finally:
        w.close()
    assert count(guard) == 1
    with closing(guard.reader()) as c, pytest.raises(sqlite3.OperationalError):
        c.execute("DELETE FROM ingestions")


def test_backups_made(guard, clock):
    assert guard.backup("daily")
    assert guard.backup("daily") is None  # once a day
    p = guard.prepare("beer")
    clock.advance(3)
    guard.confirm(p.id, "yes")
    assert list(guard.backups.glob("prewrite-*.db"))


def test_warnings(guard):
    assert any("limit" in w for w in guard.prepare("double shot", 6).warnings)
    assert guard.prepare("beer").warnings == []
