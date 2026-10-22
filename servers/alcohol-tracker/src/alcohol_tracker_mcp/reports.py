"""Drinking reports over a period: totals, timing, sessions, comparison. Pure functions over Ingestion lists."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta

from alcohol_tracker_mcp.model import (
    Ingestion,
    estimate_active_standard_drinks,
    estimate_bac,
    estimated_clear_time,
    group_into_sessions,
    simulate_active_drinks,
)
from alcohol_tracker_mcp.model_settings import EstimateSettings

PERIODS = ("today", "yesterday", "last_7_days", "last_30_days", "this_week", "this_month", "last_month", "this_year", "all")
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def resolve_period(period: str, now: datetime, first_record: date | None = None, start: str = "", end: str = "") -> tuple[date, date]:
    """Inclusive (first_day, last_day). Custom start/end (YYYY-MM-DD) win over `period`."""
    today = now.date()
    if start or end:
        try:
            s = date.fromisoformat(start) if start else (first_record or today)
            e = date.fromisoformat(end) if end else today
        except ValueError:
            raise ValueError("Dates must look like 2026-10-21.")
        if e < s:
            raise ValueError("The end date is before the start date.")
        return s, e
    p = period.strip().lower().replace(" ", "_")
    if p == "today":
        return today, today
    if p == "yesterday":
        return today - timedelta(days=1), today - timedelta(days=1)
    if p == "last_7_days":
        return today - timedelta(days=6), today
    if p == "last_30_days":
        return today - timedelta(days=29), today
    if p == "this_week":
        return today - timedelta(days=today.weekday()), today
    if p == "this_month":
        return today.replace(day=1), today
    if p == "last_month":
        end_prev = today.replace(day=1) - timedelta(days=1)
        return end_prev.replace(day=1), end_prev
    if p == "this_year":
        return today.replace(month=1, day=1), today
    if p == "all":
        return first_record or today, today
    raise ValueError(f"Unknown period '{period}'. Use one of: {', '.join(PERIODS)}, or start_date/end_date.")


def _in_range(items: list[Ingestion], first: date, last: date) -> list[Ingestion]:
    return [i for i in items if first <= i.occurred_at.date() <= last]


def _totals(items: list[Ingestion], settings: EstimateSettings) -> dict:
    std = sum(i.standard_drinks(settings) for i in items)
    days = {i.occurred_at.date() for i in items}
    return {
        "entries": len(items),
        "standard_drinks": round(std, 2),
        "pure_alcohol_grams": round(sum(i.pure_alcohol_grams(settings) for i in items), 1),
        "drinking_days": len(days),
    }


def build_report(all_items: list[Ingestion], first: date, last: date, settings: EstimateSettings, now: datetime) -> dict:
    items = sorted(_in_range(all_items, first, last), key=lambda i: i.occurred_at)
    n_days = (last - first).days + 1
    totals = _totals(items, settings)
    report: dict = {"period": {"start": first.isoformat(), "end": last.isoformat(), "days": n_days}, "totals": totals}
    if not items:
        report["spoken_summary"] = f"No drinks were logged from {first:%b %d} to {last:%b %d}."
        report["empty"] = True
        return report

    by_day: dict[date, float] = defaultdict(float)
    for i in items:
        by_day[i.occurred_at.date()] += i.standard_drinks(settings)
    heavy_day, heavy_val = max(by_day.items(), key=lambda kv: kv[1])
    totals.update(
        avg_per_day=round(totals["standard_drinks"] / n_days, 2),
        avg_per_drinking_day=round(totals["standard_drinks"] / totals["drinking_days"], 2),
        heaviest_day={"date": heavy_day.isoformat(), "standard_drinks": round(heavy_val, 2)},
    )

    # when: weekday and hour of day (hour is the time the drink was logged as taken)
    wd = [0.0] * 7
    hr = [0.0] * 24
    for i in items:
        s = i.standard_drinks(settings)
        wd[i.occurred_at.weekday()] += s
        hr[i.occurred_at.hour] += s
    report["by_weekday"] = {WEEKDAYS[k]: round(v, 2) for k, v in enumerate(wd)}
    report["by_hour"] = {f"{k:02d}:00": round(v, 2) for k, v in enumerate(hr) if v}
    late = sum(hr[0:5])
    report["late_night_share_percent"] = round(100 * late / sum(hr), 1) if sum(hr) else 0.0

    # what
    kinds: dict[str, list[float]] = defaultdict(lambda: [0, 0.0])
    for i in items:
        kinds[i.label][0] += 1
        kinds[i.label][1] += i.standard_drinks(settings)
    report["by_drink"] = [{"drink": k, "entries": int(v[0]), "standard_drinks": round(v[1], 2)} for k, v in sorted(kinds.items(), key=lambda kv: -kv[1][1])]

    # sessions and peak BAC (simulated from the logged times; an estimate, not a measurement)
    sessions = []
    for group in group_into_sessions(items, settings):
        begin, finish = group[0].occurred_at, group[-1].occurred_at
        series = simulate_active_drinks(group, begin, finish + timedelta(hours=10), settings, step_minutes=10)
        bac_series = [(t, estimate_bac(v, settings)) for t, v in series]
        peak_t, peak = max(bac_series, key=lambda p: p[1])
        clear = estimated_clear_time(bac_series, 0.005)
        sessions.append({
            "start": begin.isoformat(timespec="minutes"),
            "last_drink": finish.isoformat(timespec="minutes"),
            "duration_minutes": int((finish - begin).total_seconds() // 60),
            "standard_drinks": round(sum(i.standard_drinks(settings) for i in group), 2),
            "peak_bac_percent": round(peak, 3),
            "peak_at": peak_t.isoformat(timespec="minutes"),
            "estimated_clear": clear.isoformat(timespec="minutes") if clear else None,
        })
    report["sessions"] = sessions
    report["heaviest_sessions"] = sorted(sessions, key=lambda s: -s["standard_drinks"])[:3]
    totals["highest_peak_bac_percent"] = max(s["peak_bac_percent"] for s in sessions)

    # gaps
    days_sorted = sorted(by_day)
    gaps = [(b - a).days - 1 for a, b in zip(days_sorted, days_sorted[1:])]
    report["longest_dry_stretch_days"] = max(gaps + [(days_sorted[0] - first).days, (last - days_sorted[-1]).days])
    report["days_since_last_drink"] = (now.date() - max(i.occurred_at for i in all_items).date()).days

    # compare with the equal-length period before
    prev_last = first - timedelta(days=1)
    prev_first = prev_last - timedelta(days=n_days - 1)
    prev = _totals(_in_range(all_items, prev_first, prev_last), settings)
    delta = None if prev["standard_drinks"] == 0 else round(100 * (totals["standard_drinks"] - prev["standard_drinks"]) / prev["standard_drinks"])
    report["compared_to_previous_period"] = {"start": prev_first.isoformat(), "end": prev_last.isoformat(), **prev, "change_percent": delta}

    if first <= now.date() <= last:
        report["right_now"] = status(all_items, now, settings)

    report["spoken_summary"] = spoken_summary(report)
    return report


def status(all_items: list[Ingestion], now: datetime, settings: EstimateSettings) -> dict:
    recent = [i for i in all_items if i.occurred_at >= now - timedelta(hours=48) and i.occurred_at <= now]
    active = estimate_active_standard_drinks(recent, now, settings) if recent else 0.0
    bac = estimate_bac(active, settings)
    out: dict = {"estimated_bac_percent": round(bac, 3), "estimated_standard_drinks_in_body": round(active, 2)}
    if recent and active > 0:
        series = simulate_active_drinks(recent, now, now + timedelta(hours=14), settings, step_minutes=10)
        clear = next((t for t, v in series if estimate_bac(v, settings) <= 0.005), None)
        out["estimated_clear_time"] = clear.isoformat(timespec="minutes") if clear else None
    today = [i for i in all_items if i.occurred_at.date() == now.date()]
    out["standard_drinks_today"] = round(sum(i.standard_drinks(settings) for i in today), 2)
    last_hour = [i for i in today if i.occurred_at >= now - timedelta(hours=1)]
    out["standard_drinks_last_hour"] = round(sum(i.standard_drinks(settings) for i in last_hour), 2)
    out["note"] = "Estimates from a journaling model, not a breathalyzer. Never use them to decide whether it is safe to drive."
    return out


def spoken_summary(r: dict) -> str:
    t, p = r["totals"], r["period"]
    parts = [
        f"From {date.fromisoformat(p['start']):%b %d} to {date.fromisoformat(p['end']):%b %d} you logged {t['standard_drinks']:g} standard drinks "
        f"over {t['drinking_days']} of {p['days']} days, about {t['avg_per_drinking_day']:g} on a drinking day."
    ]
    busiest = max(r["by_weekday"].items(), key=lambda kv: kv[1])
    parts.append(f"{busiest[0]} is your heaviest day of the week.")
    parts.append(f"Your heaviest day was {date.fromisoformat(t['heaviest_day']['date']):%b %d} with {t['heaviest_day']['standard_drinks']:g}; highest estimated peak BAC was {t['highest_peak_bac_percent']:.3f}%.")
    cmp = r["compared_to_previous_period"]
    if cmp["change_percent"] is not None:
        parts.append(f"That is {'up' if cmp['change_percent'] > 0 else 'down'} {abs(cmp['change_percent'])}% from the period before." if cmp["change_percent"] else "That matches the period before.")
    return " ".join(parts)


def to_markdown(r: dict, title: str = "Drinking report") -> str:
    p, t = r["period"], r["totals"]
    lines = [f"# {title}", f"{p['start']} to {p['end']} ({p['days']} days)", ""]
    if r.get("empty"):
        return "\n".join(lines + ["No drinks were logged in this period."]) + "\n"
    lines += [
        "## Totals",
        f"- Standard drinks: **{t['standard_drinks']:g}** across {t['entries']} entries, {t['pure_alcohol_grams']:g} g pure alcohol",
        f"- Drinking days: {t['drinking_days']} of {p['days']}; average {t['avg_per_day']:g}/day overall, {t['avg_per_drinking_day']:g} per drinking day",
        f"- Heaviest day: {t['heaviest_day']['date']} ({t['heaviest_day']['standard_drinks']:g})",
        f"- Highest estimated peak BAC: {t['highest_peak_bac_percent']:.3f}%",
        f"- Longest dry stretch: {r['longest_dry_stretch_days']} days; days since last drink: {r['days_since_last_drink']}",
        f"- Late-night share (midnight to 5am): {r['late_night_share_percent']}%",
        "",
    ]
    c = r["compared_to_previous_period"]
    lines += ["## Compared with the previous period", f"{c['start']} to {c['end']}: {c['standard_drinks']:g} standard drinks on {c['drinking_days']} days" + (f" ({c['change_percent']:+d}%)" if c["change_percent"] is not None else ""), ""]
    mx = max(r["by_weekday"].values()) or 1
    lines += ["## By weekday (standard drinks)"] + [f"- {d:<9} {v:>6g} {'#' * round(20 * v / mx)}" for d, v in r["by_weekday"].items()] + [""]
    hx = max(r["by_hour"].values())
    lines += ["## By hour of day (standard drinks)"] + [f"- {h} {v:>6g} {'#' * round(20 * v / hx)}" for h, v in r["by_hour"].items()] + [""]
    lines += ["## By drink"] + [f"- {d['drink']}: {d['entries']} entries, {d['standard_drinks']:g} standard drinks" for d in r["by_drink"]] + [""]
    lines += ["## Drinking sessions", "| Start | Last drink | Std drinks | Peak BAC | Peak at | Est. clear |", "|---|---|---|---|---|---|"]
    lines += [f"| {s['start']} | {s['last_drink']} | {s['standard_drinks']:g} | {s['peak_bac_percent']:.3f}% | {s['peak_at']} | {s['estimated_clear'] or 'n/a'} |" for s in r["sessions"]]
    lines += ["", "_BAC and clear times are model estimates from the Alcohol Tracker settings, not measurements._", ""]
    return "\n".join(lines)
