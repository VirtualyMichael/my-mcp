"""Queue avatar edit jobs for the Unity-side runner and (optionally) run Unity headless to apply them.

Nothing here edits a controller, parameter list or menu directly: the C# runner does that inside Unity, with backups,
validation and rollback. This module only installs the runner, writes job files, and launches Unity.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from importlib import resources
from pathlib import Path

from vrchat_unity_mcp.projects import is_open, unity_version, vcc_settings_path, vpm_packages
from vrchat_unity_mcp.unityyaml import find_project_root

RUNNER_REL = "Assets/Editor/ClaudeVRC/ClaudeVRCJobRunner.cs"
JOBS_REL = "Assets/ClaudeVRC/Jobs"
_NAME = re.compile(r"^[A-Za-z0-9_/-]+$")
_JOB = re.compile(r"^[A-Za-z0-9_-]{1,60}$")
OPS = {"toggle", "blendshape_slider", "outfit_selector", "material_swap"}


def _root(project: str) -> Path:
    root = find_project_root(Path(project))
    if root is None:
        raise ValueError(f"{project} is not inside a Unity project.")
    return root


def _runner_source() -> str:
    return resources.files("vrchat_unity_mcp").joinpath("editor/ClaudeVRCJobRunner.cs").read_text(encoding="utf-8")


def install_runner(project: str) -> dict:
    root = _root(project)
    if "com.vrchat.avatars" not in vpm_packages(root):
        raise ValueError("This project has no VRChat Avatars SDK (com.vrchat.avatars), so the avatar job runner would not compile. "
                         "Use a project created from the Avatar template in VCC.")
    target = root / RUNNER_REL
    src = _runner_source()
    status = "already up to date"
    if not target.exists() or target.read_text(encoding="utf-8") != src:
        target.parent.mkdir(parents=True, exist_ok=True)
        status = "updated" if target.exists() else "installed"
        target.write_text(src, encoding="utf-8", newline="\n")
    return {"runner": RUNNER_REL, "status": status}


def _asset_path(root: Path, rel: str, suffix: str) -> str:
    rel = rel.replace("\\", "/")
    p = (root / rel).resolve()
    if not rel.startswith("Assets/") or not str(p).startswith(str((root / "Assets").resolve())):
        raise ValueError(f"'{rel}' must be a project-relative path starting with Assets/.")
    if p.suffix != suffix or not p.is_file():
        raise ValueError(f"'{rel}' does not exist or is not a {suffix} file.")
    return rel


def queue_job(project: str, job_name: str, controller: str, parameters: str, menu: str, ops: list[dict]) -> dict:
    root = _root(project)
    if not _JOB.match(job_name):
        raise ValueError("job_name may only contain letters, digits, '-' and '_'.")
    clean = []
    for i, op in enumerate(ops):
        kind = op.get("op")
        if kind not in OPS:
            raise ValueError(f"ops[{i}].op must be one of {sorted(OPS)}.")
        name = str(op.get("name", "")).strip()
        if not name:
            raise ValueError(f"ops[{i}] needs a name (the menu label).")
        param = str(op.get("parameter") or name.replace(" ", ""))
        if not _NAME.match(param):
            raise ValueError(f"ops[{i}] parameter '{param}' may only contain letters, digits, '_', '/' and '-' (set 'parameter' explicitly).")
        entry = {"op": kind, "name": name, "parameter": param, "object_path": "", "renderer_path": "", "blendshape": "",
                 "min_value": float(op.get("min_value", 0)), "max_value": float(op.get("max_value", 100)),
                 "default_value": float(op.get("default_value", 0)), "default_on": bool(op.get("default_on", False)),
                 "saved": bool(op.get("saved", True)), "synced": bool(op.get("synced", True)),
                 "menu_path": str(op.get("menu_path", "")).strip("/"), "write_defaults": str(op.get("write_defaults", "auto"))}
        if entry["write_defaults"] not in ("auto", "on", "off"):
            raise ValueError("write_defaults must be auto, on or off.")
        if kind == "toggle":
            entry["object_path"] = str(op.get("object_path", "")).strip("/")
            if not entry["object_path"]:
                raise ValueError(f"ops[{i}] toggle needs object_path (path of the object below the avatar root, e.g. 'Body/Hat').")
        elif kind == "blendshape_slider":
            entry["renderer_path"] = str(op.get("renderer_path", "")).strip("/")
            entry["blendshape"] = str(op.get("blendshape", ""))
            if not entry["renderer_path"] or not entry["blendshape"]:
                raise ValueError(f"ops[{i}] blendshape_slider needs renderer_path and blendshape.")
            if not 0 <= entry["default_value"] <= 1:
                raise ValueError("default_value for a slider must be between 0 and 1.")
        else:
            options = op.get("options") or []
            if not 1 <= len(options) <= 8:
                raise ValueError(f"ops[{i}] {kind} needs 1-8 options (one menu control each; use a second op for more).")
            built = []
            for j, o in enumerate(options):
                label = str(o.get("label", "")).strip()
                if not label:
                    raise ValueError(f"ops[{i}].options[{j}] needs a label.")
                if kind == "outfit_selector":
                    paths = [str(x).strip("/") for x in (o.get("object_paths") or []) if str(x).strip("/")]
                    if not paths:
                        raise ValueError(f"ops[{i}].options[{j}] ('{label}') needs object_paths (objects shown for this outfit).")
                    built.append({"label": label, "object_paths": paths, "material": ""})
                else:
                    built.append({"label": label, "object_paths": [], "material": _asset_path(root, str(o.get("material", "")), ".mat")})
            entry["options"] = built
            entry["default_option"] = int(op.get("default_option", 0))
            if not 0 <= entry["default_option"] <= len(built):
                raise ValueError(f"ops[{i}] default_option must be 0 (none/default) to {len(built)}.")
            if kind == "material_swap":
                entry["renderer_path"] = str(op.get("renderer_path", "")).strip("/")
                if not entry["renderer_path"]:
                    raise ValueError(f"ops[{i}] material_swap needs renderer_path.")
                entry["material_index"] = int(op.get("material_index", 0))
                entry["is_skinned"] = bool(op.get("is_skinned", True))
        clean.append(entry)
    if not clean:
        raise ValueError("ops is empty.")
    payload = {"controller": _asset_path(root, controller, ".controller"), "parameters": _asset_path(root, parameters, ".asset"),
               "menu": _asset_path(root, menu, ".asset"), "ops": clean}
    runner = install_runner(project)
    job_file = root / JOBS_REL / f"{job_name}.json"
    if job_file.exists():
        raise ValueError(f"A pending job named '{job_name}' already exists; use another name.")
    job_file.parent.mkdir(parents=True, exist_ok=True)
    job_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {"queued": f"{JOBS_REL}/{job_name}.json", "runner": runner,
            "next": "Unity will compile the runner when it regains focus. Then choose Tools > Claude VRC > Run Pending Jobs, "
                    "or call run_unity_jobs if the project is NOT open in Unity.",
            "ops": [f"{o['op']}: {o['name']} -> parameter {o['parameter']}" for o in clean]}


def find_unity_exe(root: Path) -> Path:
    version = unity_version(root)
    candidates = []
    if os.environ.get("UNITY_EXE"):
        candidates.append(Path(os.environ["UNITY_EXE"]))
    if version:
        candidates.append(Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Unity" / "Hub" / "Editor" / version / "Editor" / "Unity.exe")
        candidates.append(Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Unity" / "Editor" / "Unity.exe")
    try:
        s = json.loads(vcc_settings_path().read_text(encoding="utf-8"))
        candidates += [Path(p) for k, p in (s.get("preferredUnityEditors") or {}).items() if version and version.startswith(k)]
    except (OSError, ValueError):
        pass
    for c in candidates:
        if c.is_file():
            return c
    raise ValueError(f"Could not find Unity {version}. Install that exact version via Unity Hub/VCC, or set the UNITY_EXE environment variable.")


def pending_jobs(project: str) -> list[str]:
    d = _root(project) / JOBS_REL
    return sorted(p.name for p in d.glob("*.json")) if d.is_dir() else []


def run_batch(project: str, timeout_s: int = 900) -> dict:
    root = _root(project)
    if is_open(root):
        raise ValueError("This project looks open in a Unity editor. Close it, or run Tools > Claude VRC > Run Pending Jobs inside Unity instead.")
    jobs = pending_jobs(project)
    if not jobs:
        raise ValueError("No pending jobs. Use queue_avatar_job first.")
    install_runner(project)
    exe = find_unity_exe(root)
    log = root / "Logs" / "ClaudeVRC-batch.log"
    log.parent.mkdir(exist_ok=True)
    cmd = [str(exe), "-batchmode", "-nographics", "-projectPath", str(root), "-executeMethod", "ClaudeVRC.JobRunner.RunBatch", "-logFile", str(log)]
    try:
        proc = subprocess.run(cmd, timeout=timeout_s, capture_output=True, text=True)
        code = proc.returncode
    except subprocess.TimeoutExpired:
        raise ValueError(f"Unity did not finish within {timeout_s}s (a first import of a big project can take longer). "
                         f"See {log}; no assets are changed until the job runs, and backups are made before edits.")
    text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
    interesting = [l for l in text.splitlines() if "[ClaudeVRC]" in l or "error CS" in l or "Exception" in l][-25:]
    results = {p.stem.replace(".result", ""): p.read_text(encoding="utf-8") for p in (root / JOBS_REL / "Done").glob("*.result.txt")} \
        if (root / JOBS_REL / "Done").is_dir() else {}
    return {"unity_exit_code": code, "jobs_found": jobs, "results": results, "log_highlights": interesting, "log_file": str(log)}
