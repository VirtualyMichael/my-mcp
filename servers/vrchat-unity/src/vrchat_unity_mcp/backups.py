"""List and restore the backups the Unity-side runner makes before every job."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from vrchat_unity_mcp.projects import is_open
from vrchat_unity_mcp.unityyaml import find_project_root

_JOB = re.compile(r"^[A-Za-z0-9_-]{1,60}$")


def _root(project: str) -> Path:
    root = find_project_root(Path(project))
    if root is None:
        raise ValueError(f"{project} is not inside a Unity project.")
    return root


def list_backups(project: str) -> list[dict]:
    d = _root(project) / "Assets" / "ClaudeVRC" / "Backups"
    out = []
    if d.is_dir():
        for m in sorted(d.glob("*/manifest.json")):
            try:
                files = json.loads(m.read_text(encoding="utf-8")).get("files", [])
            except (OSError, ValueError):
                continue
            out.append({"job": m.parent.name, "assets": [f["original"] for f in files]})
    return out


def restore_backup(project: str, job_name: str) -> dict:
    """Put back the controller, expression parameters and menu exactly as they were before the job ran.
    Clips and sub menus the job generated stay in Assets/ClaudeVRC/Generated but become unused."""
    root = _root(project)
    if is_open(root):
        raise ValueError("The project looks open in Unity. Close it first (or copy the files back yourself from "
                         f"Assets/ClaudeVRC/Backups/{job_name}) so Unity does not overwrite the restore.")
    if not _JOB.match(job_name):
        raise ValueError("Invalid job name.")
    manifest = root / "Assets" / "ClaudeVRC" / "Backups" / job_name / "manifest.json"
    if not manifest.is_file():
        names = [b["job"] for b in list_backups(project)]
        raise ValueError(f"No backup manifest for job '{job_name}'. Available: {names or 'none'}")
    assets = (root / "Assets").resolve()
    plan = []
    for f in json.loads(manifest.read_text(encoding="utf-8")).get("files", []):
        src, dst = (root / f["backup"]).resolve(), (root / f["original"]).resolve()
        if not (str(src).startswith(str(assets)) and str(dst).startswith(str(assets))) or not src.is_file():
            raise ValueError(f"Backup entry looks wrong, nothing was restored: {f}")
        plan.append((src, dst, f["original"]))
    for src, dst, _ in plan:
        shutil.copy2(src, dst)
    return {"restored": [p[2] for p in plan],
            "note": "Reopen Unity to reimport. Clips and menus the job generated remain in Assets/ClaudeVRC/Generated but are unused."}
