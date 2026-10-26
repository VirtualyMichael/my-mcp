"""Read-only parsing of Unity's text-serialised assets (.controller, .anim, .asset, .prefab, .unity)."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

_HEADER = re.compile(r"^--- !u!(\d+) &(-?\d+)(?: stripped)?\s*$")
MAX_BYTES = 60 * 1024 * 1024

CLASS_NAMES = {
    1: "GameObject", 4: "Transform", 74: "AnimationClip", 91: "AnimatorController", 114: "MonoBehaviour",
    1101: "AnimatorStateTransition", 1102: "AnimatorState", 1107: "AnimatorStateMachine", 206: "BlendTree",
}


class UnityYamlError(ValueError):
    pass


def load_documents(path: Path) -> dict[int, tuple[int, dict]]:
    """Return {fileID: (classID, body)} for every document in the file."""
    path = Path(path)
    if not path.is_file():
        raise UnityYamlError(f"File not found: {path}")
    if path.stat().st_size > MAX_BYTES:
        raise UnityYamlError(f"{path.name} is too large to analyse ({path.stat().st_size // 1_000_000} MB)")
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("%YAML"):
        raise UnityYamlError(f"{path.name} is not a text-serialised Unity asset (binary serialisation?). "
                             "Set Edit > Project Settings > Editor > Asset Serialization to Force Text.")
    docs: dict[int, tuple[int, dict]] = {}
    cls = fid = None
    buf: list[str] = []

    def flush() -> None:
        if fid is None:
            return
        try:
            body = yaml.load("\n".join(buf), Loader=yaml.CSafeLoader if hasattr(yaml, "CSafeLoader") else yaml.SafeLoader)
        except yaml.YAMLError:
            body = None
        if isinstance(body, dict):
            top = next(iter(body.values()), None)
            docs[fid] = (cls, top if isinstance(top, dict) else {})

    for line in text.splitlines():
        m = _HEADER.match(line)
        if m:
            flush()
            cls, fid, buf = int(m.group(1)), int(m.group(2)), []
        elif fid is not None:
            buf.append(line)
    flush()
    return docs


def find_project_root(path: Path) -> Path | None:
    for parent in [Path(path).resolve(), *Path(path).resolve().parents]:
        if (parent / "Assets").is_dir() and (parent / "ProjectSettings").is_dir():
            return parent
    return None


def guid_index(root: Path, suffixes=(".anim", ".controller", ".asset", ".mask", ".prefab")) -> dict[str, str]:
    """Map guid -> project-relative path by reading .meta files for the given asset types."""
    index: dict[str, str] = {}
    for meta in (root / "Assets").rglob("*.meta"):
        base = meta.name[:-5]
        if not base.lower().endswith(suffixes):
            continue
        try:
            for line in meta.read_text(encoding="utf-8", errors="replace").splitlines()[:6]:
                if line.startswith("guid:"):
                    index[line.split(":", 1)[1].strip()] = str(meta.with_suffix("").relative_to(root)).replace("\\", "/")
                    break
        except OSError:
            continue
    return index
