# My MCP

Small, individually installable [MCP](https://modelcontextprotocol.io) servers (and their skills) for my local AI apps: the
Voice Assistant (`Ai Live convo system`), Bionic / LM Studio, and Claude. Each server lives in `servers/<name>/` with a
`server.json` manifest, its own tests, and an optional `skill/` folder in the standard `SKILL.md` format.

```bash
python install.py list
python install.py alcohol-tracker --dry-run        # show what would change
python install.py alcohol-tracker                  # voice assistant + Bionic/LM Studio
python install.py alcohol-tracker --target claude-code
```

The installer gives each server its own virtual environment (`~/.my-mcp/venvs/<name>`), registers it in the chosen app's config
(backing the file up first), and copies the skill into the Bionic/LM Studio and Claude skill folders. Restart the app afterwards.

## Servers

| Server | What it does |
|---|---|
| [alcohol-tracker](servers/alcohol-tracker) | Log preset drinks by voice (read-back, yes/no, undo) and get detailed drinking reports from the Alcohol Ingestion Tracker app. Built so an AI cannot edit or delete your records. |

## Adding a server

Create `servers/<name>/` with a `pyproject.toml`, a `server.json` (`name`, `description`, `module`, optional `skill`, `autoApprove`, `env`),
tests, and a skill if it needs one. `install.py` picks it up automatically.

Run a server's tests: `cd servers/<name> && python -m pytest`.
