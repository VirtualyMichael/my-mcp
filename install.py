#!/usr/bin/env python
"""Install one server from this repo and register it where your AI apps look.

  python install.py list
  python install.py alcohol-tracker --target voice lmstudio claude-code [--dry-run]

Each server gets its own virtual environment under ~/.my-mcp/venvs/<name> (so nothing clashes), and its skill, if it has one, is
copied to the Bionic/LM Studio and Claude skill folders. Config files are backed up (<file>.bak-mcp) before they change.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HOME = Path.home()
TARGETS = {
    "voice": Path(os.environ.get("APPDATA", HOME)) / "VoiceAssistant" / "config.json",
    "lmstudio": HOME / ".lmstudio" / "mcp.json",
}
SKILL_DIRS = {"lmstudio": HOME / ".lmstudio" / "skills", "claude-code": HOME / ".claude" / "skills"}


def manifests() -> dict[str, dict]:
    return {p.parent.name: json.loads(p.read_text(encoding="utf-8")) for p in sorted(ROOT.glob("servers/*/server.json"))}


def venv_python(name: str) -> Path:
    base = HOME / ".my-mcp" / "venvs" / name
    return base / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def build_env(name: str, dry: bool) -> Path:
    py = venv_python(name)
    print(f"  environment: {py.parent.parent}")
    if dry:
        return py
    if not py.exists():
        venv.EnvBuilder(with_pip=True).create(py.parent.parent)
    subprocess.run([str(py), "-m", "pip", "install", "--quiet", "--upgrade", str(ROOT / "servers" / name)], check=True)
    return py


def edit_json(path: Path, mutate, dry: bool) -> None:
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    mutate(data)
    print(f"  {'would update' if dry else 'updated'} {path}")
    if dry:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        shutil.copy2(path, path.with_name(path.name + ".bak-mcp"))
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def register(target: str, name: str, m: dict, py: Path, dry: bool) -> None:
    entry = {"command": str(py), "args": ["-m", m["module"]]}
    if m.get("env"):
        entry["env"] = m["env"]
    if target == "voice":
        entry["auto_approve"] = bool(m.get("autoApprove"))
        edit_json(TARGETS["voice"], lambda d: d.setdefault("mcp_servers", {}).__setitem__(name, entry), dry)
    elif target == "lmstudio":
        edit_json(TARGETS["lmstudio"], lambda d: d.setdefault("mcpServers", {}).__setitem__(name, entry), dry)
    elif target == "claude-code":
        cmd = ["claude", "mcp", "add", "--scope", "user", name, "--", str(py), "-m", m["module"]]
        print(f"  {'would run' if dry else 'running'}: {' '.join(cmd)}")
        if not dry and shutil.which("claude"):
            subprocess.run(cmd, check=False)
        elif not dry:
            print("  the claude CLI was not found; run the command above yourself")
    if m.get("skill") and target in SKILL_DIRS:
        src = ROOT / "servers" / name / m["skill"]
        dest = SKILL_DIRS[target] / src.name
        print(f"  {'would copy' if dry else 'copying'} skill to {dest}")
        if not dry:
            shutil.copytree(src, dest, dirs_exist_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("server", help="server folder name under servers/, or 'list'")
    ap.add_argument("--target", nargs="+", choices=[*TARGETS, "claude-code"], default=["voice", "lmstudio"])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    found = manifests()
    if a.server == "list":
        for n, m in found.items():
            print(f"{n}: {m['description']}")
        return 0
    if a.server not in found:
        print(f"No server '{a.server}'. Available: {', '.join(found)}")
        return 1
    print(f"Installing {a.server}")
    py = build_env(a.server, a.dry_run)
    for t in a.target:
        print(f"- {t}")
        register(t, a.server, found[a.server], py, a.dry_run)
    print("Dry run: nothing changed." if a.dry_run else "Done. Restart the app(s) to load the server.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
