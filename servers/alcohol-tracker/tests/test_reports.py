from datetime import date, datetime, timedelta

import pytest

from alcohol_tracker_mcp import reports
from alcohol_tracker_mcp.model import Ingestion
from alcohol_tracker_mcp.model_settings import EstimateSettings

S = EstimateSettings()
NOW = datetime(2026, 10, 21, 20, 0)


def drink(day_offset, hour, n=1):
    t = NOW.replace(hour=hour, minute=0) - timedelta(days=day_offset)
    return [Ingestion(None, t + timedelta(minutes=10 * k), 1.0, "shots", 40.0, "Shot", consumer="Me") for k in range(n)]


def test_periods():
    assert reports.resolve_period("last_7_days", NOW) == (date(2026, 10, 15), date(2026, 10, 21))
    assert reports.resolve_period("last_month", NOW) == (date(2026, 9, 1), date(2026, 9, 30))
    assert reports.resolve_period("x", NOW, start="2026-01-02", end="2026-01-03") == (date(2026, 1, 2), date(2026, 1, 3))


@pytest.mark.parametrize("kw", [{"period": "nope"}, {"period": "today", "start": "bad"}, {"period": "today", "start": "2026-02-02", "end": "2026-01-01"}])
def test_bad_period(kw):
    with pytest.raises(ValueError):
        reports.resolve_period(now=NOW, **kw)


def test_report_numbers():
    items = drink(0, 19, 3) + drink(3, 22, 2) + drink(10, 21, 4)
    r = reports.build_report(items, date(2026, 10, 15), date(2026, 10, 21), S, NOW)
    assert r["totals"]["standard_drinks"] == 5.0 and r["totals"]["drinking_days"] == 2
    assert r["totals"]["heaviest_day"]["standard_drinks"] == 3.0
    assert len(r["sessions"]) == 2 and r["sessions"][0]["peak_bac_percent"] > 0
    assert r["compared_to_previous_period"]["standard_drinks"] == 4.0
    assert "right_now" in r and r["spoken_summary"]
    assert "## By weekday" in reports.to_markdown(r)


def test_empty_report():
    r = reports.build_report([], date(2026, 10, 15), date(2026, 10, 21), S, NOW)
    assert r["empty"] and "No drinks" in r["spoken_summary"] and "No drinks" in reports.to_markdown(r)
