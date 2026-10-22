---
name: alcohol-tracker
description: Log what the user drank (by preset, e.g. "I just had a beer") into their Alcohol Tracker app, undo a mistaken log, and give detailed drinking reports by time and amount (today, week, month, year, custom range). Use when the user says what they drank or asks how much, how often, when, or how they are doing.
---
# Alcohol Tracker

Tools come from the `alcohol-tracker` MCP server. It can only add preset drinks, undo the assistant's own recent entries, and read. It cannot edit or delete anything else. Estimates (BAC, clear time) are from a journaling model, not a measurement, and are never advice on whether it is safe to drive.

## Logging a drink
1. Call `prepare_dose` with the drink as the user said it (`quantity` for "two beers", `minutes_ago` for "an hour ago" = 60). If the preset is unclear it lists the matches: ask which one. If there is none, say so and offer `list_drink_presets`; do not invent or substitute a drink.
2. Read the `read_back_to_user` line to the user in your own words, say any `warnings_to_say_aloud` plainly and without lecturing, and ask **"Yes or no?"**
3. Only after the user clearly says yes, call `confirm_dose` with the proposal id and their exact reply. Never answer for them, never confirm in the same turn as prepare, never guess from silence. On "no", drop it.
4. After logging, say what was logged and that they can say "undo".

## Undo
Only when the user asks. Ask them to confirm, then call `undo_last_dose` with their reply. It works only on drinks the assistant added in the last 10 minutes that have not been edited in the app. Anything older or edited must be changed by the user in the app: tell them so. Never try other routes (files, SQL, shell) to change the tracker's data.

## Reports
- Quick questions ("how much today / this week"): `drinking_report` with a `period`, then read `spoken_summary`; offer detail after.
- "Right now" or "when will I be clear": `current_status`.
- Detailed or shareable: `save_drinking_report`, and give the file path.
- Custom ranges use `start_date` / `end_date` (YYYY-MM-DD). Periods: today, yesterday, last_7_days, last_30_days, this_week, this_month, last_month, this_year, all.
- Report on time and amount: totals and averages, heaviest day, weekday and hour patterns, drink mix, sessions with estimated peak BAC, change from the previous period. Quote numbers from the tool, state the period, and compare periods only with the tool's own comparison. Stay factual and kind. If the data shows very high peaks or a sharp rise, say it once, plainly, and mention that support lines exist if they want them; do not repeat it.

## Never
Log a drink the user did not say, more than 6 in one go, or a time in the future; write to the database any way except these tools.
