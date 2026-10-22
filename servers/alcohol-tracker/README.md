# alcohol-tracker MCP server

Lets an AI (the voice assistant, Bionic, Claude) log what you drank and report on your drinking, using the Alcohol Ingestion
Tracker's own database (`%LOCALAPPDATA%\AlcoholTracker\alcohol_tracker.db`; set `ALCOHOL_TRACKER_DB` to point elsewhere).
Install with `python install.py alcohol-tracker` from the repo root.

## Tools
| Tool | What it does |
|---|---|
| `prepare_dose(drink, quantity, minutes_ago)` | Matches a saved preset, returns a read-back and limit warnings. **Writes nothing.** |
| `confirm_dose(proposal_id, user_reply)` | Adds it. Needs a prepared proposal, a clear yes, and a pause since the read-back. Single use. |
| `undo_last_dose(user_reply)` | Removes the assistant's own entries from the last 10 minutes, only if you haven't edited them. |
| `current_status`, `recent_doses`, `list_drink_presets` | Read-only. |
| `drinking_report(period or start_date/end_date)` | Totals, averages, heaviest day, weekday and hour patterns, drink mix, sessions with estimated peak BAC, change from the previous period, and a sentence to read aloud. |
| `save_drinking_report(...)` | Same report as a markdown file in `%LOCALAPPDATA%\AlcoholTracker\reports`. |

## Safety
- No tool edits or deletes anything but the assistant's own recent, untouched entries. There is no SQL or file tool.
- The write connection has a SQLite authorizer: only INSERT on `ingestions`/`assistant_log`, and DELETE on `ingestions` only inside undo. `DROP`, `ALTER`, `UPDATE ingestions` and everything else are refused. Reads use a read-only connection.
- Hard caps in code: 6 drinks per log, 24 hours back, none in the future, 12 AI-logged drinks per hour, 10-minute undo window.
- Entries are tagged `[AI]` in the notes and recorded in an `assistant_log` table (with a snapshot), so they are always identifiable.
- Database backups: a daily copy and a pre-write copy (at most one per 10 minutes) in `%LOCALAPPDATA%\AlcoholTracker\backups`.
- Limit warnings (spoken, never blocking): defaults of 8 standard drinks a day, 0.08% estimated peak BAC, 3 standard drinks an hour. Change them in `%LOCALAPPDATA%\AlcoholTracker\assistant_limits.json` (`daily_standard_drinks`, `peak_bac_percent`, `drinks_per_hour`). The AI cannot change this file.

`src/alcohol_tracker_mcp/model.py` and `model_settings.py` are vendored copies of the tracker's estimate model so this server installs on its own; keep them in sync with the app. Your estimate settings (weight, height, and so on) are read from the app's saved settings (Windows registry).

Estimates are a journaling model, not a measurement. Never use them to decide whether it is safe to drive.

Tests: `python -m pytest` (needs `pytest` and `mcp`).
