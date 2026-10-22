"""MCP server (stdio) for the Alcohol Tracker app.

Tools an AI gets:
  read-only   list_drink_presets, current_status, recent_doses, drinking_report, prepare_dose
  writes      confirm_dose (adds), undo_last_dose (removes only the assistant's own recent entries),
              save_drinking_report (writes one markdown file into the reports folder)
There is no tool that edits or deletes anything else. See guard.py for how that is enforced.
"""

from __future__ import annotations

import functools
import json
import re
from datetime import datetime

try:  # MCP SDK 2.x
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:  # MCP SDK 1.x
    from mcp.server.fastmcp import FastMCP as _Server
from mcp.types import ToolAnnotations

from alcohol_tracker_mcp import config, reports
from alcohol_tracker_mcp.guard import DoseError, Guard

INSTRUCTIONS = (
    "Logs and reports alcohol for the user's Alcohol Tracker app. To log a drink: call prepare_dose, READ THE RESULT BACK to the user "
    "(and any warnings) and ask 'yes or no?'. Only after they answer yes, call confirm_dose with their exact words. Never confirm on your own. "
    "Undo only when the user asks. Estimates are not medical or legal advice."
)

mcp = _Server("alcohol-tracker", instructions=INSTRUCTIONS)
RO = ToolAnnotations(readOnlyHint=True)
_guard: Guard | None = None


def guard() -> Guard:
    global _guard
    if _guard is None:
        _guard = Guard()
        try:
            _guard.backup("daily")
        except Exception:  # a failed daily backup must not stop reads
            pass
    return _guard


def _json(obj) -> str:
    return json.dumps(obj, indent=2, default=str)


def _safe(fn):
    @functools.wraps(fn)
    def wrapper(*a, **k):
        try:
            return fn(*a, **k)
        except (DoseError, ValueError) as e:
            return f"Not done: {e}"

    return wrapper


@mcp.tool(annotations=RO)
def list_drink_presets() -> str:
    """The drink presets saved in the tracker (the only drinks that can be logged by voice)."""
    return _json([{"name": p.name, "amount": p.amount, "unit": p.unit, "abv_percent": p.abv_percent} for p in guard().presets()])


@mcp.tool(annotations=RO)
@_safe
def prepare_dose(drink: str, quantity: int = 1, minutes_ago: float = 0) -> str:
    """Step 1 of logging. Matches `drink` to a saved preset and returns a read-back plus any limit warnings. Writes NOTHING.
    Read it to the user and ask yes or no; only then call confirm_dose. quantity is 1-6 whole drinks; minutes_ago back-dates up to 24 hours."""
    p = guard().prepare(drink, quantity, minutes_ago)
    return _json({
        "proposal_id": p.id,
        "read_back_to_user": f"Log {p.readback()}?",
        "standard_drinks": round(p.standard_drinks, 2),
        "estimated_peak_bac_percent": round(p.projected_peak_bac, 3),
        "warnings_to_say_aloud": p.warnings,
        "next": "Ask the user yes or no. Do not call confirm_dose until they answer yes.",
    })


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False))
@_safe
def confirm_dose(proposal_id: str, user_reply: str) -> str:
    """Step 2 of logging: adds the prepared drink. `user_reply` must be the user's actual spoken or typed answer (a clear yes)."""
    return _json(guard().confirm(proposal_id, user_reply))


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False))
@_safe
def undo_last_dose(user_reply: str) -> str:
    """Removes the drink(s) the assistant itself logged most recently, only within 10 minutes and only if untouched in the app.
    Ask the user first; `user_reply` is their actual yes. It can never remove anything else."""
    return _json(guard().undo_last(user_reply))


@mcp.tool(annotations=RO)
@_safe
def recent_doses(limit: int = 10) -> str:
    """The latest logged drinks, newest first, marking which ones the assistant added."""
    items = guard().ingestions(since=None)[-max(1, min(int(limit), 50)) :][::-1]
    ai = guard().ai_flags([i.id for i in items if i.id])
    s = guard().settings()
    return _json([{"when": i.occurred_at.isoformat(timespec="minutes"), "drink": i.label, "standard_drinks": round(i.standard_drinks(s), 2), "added_by_assistant": i.id in ai} for i in items])


@mcp.tool(annotations=RO)
@_safe
def current_status() -> str:
    """Right now: estimated BAC, standard drinks in the body, estimated clear time, today's total and the last hour's total."""
    g = guard()
    return _json(reports.status(g.ingestions(since=None), datetime.now(), g.settings()))


def _report(period: str, start_date: str, end_date: str) -> tuple[dict, str]:
    g, now = guard(), datetime.now()
    items = g.ingestions(since=None)
    first, last = reports.resolve_period(period, now, items[0].occurred_at.date() if items else None, start_date, end_date)
    return reports.build_report(items, first, last, g.settings(), now), period


@mcp.tool(annotations=RO)
@_safe
def drinking_report(period: str = "last_7_days", start_date: str = "", end_date: str = "") -> str:
    """Detailed report: totals, averages, heaviest day, by weekday and hour, by drink, sessions with estimated peak BAC, comparison with the
    previous period. period: today, yesterday, last_7_days, last_30_days, this_week, this_month, last_month, this_year, all.
    Or give start_date/end_date as YYYY-MM-DD. `spoken_summary` is ready to read aloud; offer the details after."""
    return _json(_report(period, start_date, end_date)[0])


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False))
@_safe
def save_drinking_report(period: str = "last_30_days", start_date: str = "", end_date: str = "") -> str:
    """Saves the same report as a markdown file in the tracker's reports folder (a new file each time; nothing is overwritten)."""
    report, label = _report(period, start_date, end_date)
    name = re.sub(r"[^a-z0-9_-]", "", (label or "custom").lower().replace(" ", "_")) or "custom"
    folder = config.reports_dir()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"drinking-report-{name}-{datetime.now():%Y%m%d-%H%M%S}.md"
    path.write_text(reports.to_markdown(report), encoding="utf-8")
    return _json({"saved_to": str(path), "spoken_summary": report["spoken_summary"]})


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
