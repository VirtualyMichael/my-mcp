# Install guide

## VRChat + Unity helper (vrchat-unity)

**Easiest:** double-click [`install-vrchat-unity.bat`](install-vrchat-unity.bat). It installs into Bionic / LM Studio, then restart the app.

Or from a terminal in this folder:

```bash
python install.py vrchat-unity --dry-run                    # preview, changes nothing
python install.py vrchat-unity                              # Voice Assistant + Bionic / LM Studio
python install.py vrchat-unity --target lmstudio            # Bionic / LM Studio only
python install.py vrchat-unity --target claude-code         # also register with Claude Code
```

What the installer does:
- creates an isolated environment at `~/.my-mcp/venvs/vrchat-unity` and installs the server into it
- adds `vrchat-unity` to `~/.lmstudio/mcp.json` (backup: `mcp.json.bak-mcp`)
- copies the skill to `~/.lmstudio/skills/vrchat-unity/`

Where things live in this repo:

| What | Path |
|---|---|
| Server code | `servers/vrchat-unity/src/vrchat_unity_mcp/` |
| Teaching guides (16) | `servers/vrchat-unity/src/vrchat_unity_mcp/guides/` |
| Unity-side editor script | `servers/vrchat-unity/src/vrchat_unity_mcp/editor/ClaudeVRCJobRunner.cs` |
| Skill | `servers/vrchat-unity/skill/vrchat-unity/SKILL.md` |
| Tests | `servers/vrchat-unity/tests/` (`python -m pytest` inside the server folder) |

After installing, ask Bionic things like "I'm new to VRChat avatars, where do I start?" or "check my Nami avatar's FX controller".
Avatar edits ask you to confirm, back up every asset first, and need the project's Unity version installed.

## Alcohol tracker

```bash
python install.py alcohol-tracker
```

See [servers/alcohol-tracker](servers/alcohol-tracker/README.md).
