"""Read-only scans of scenes/prefabs and project assets: object paths, VRCFury / Modular Avatar usage, texture bloat."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from vrchat_unity_mcp.unityyaml import MAX_BYTES, find_project_root, load_documents

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".tga", ".psd", ".exr", ".tif", ".tiff", ".bmp", ".hdr"}
MODEL_EXT = {".fbx", ".obj", ".blend"}


def list_scene_objects(file_path: str, name_contains: str = "", limit: int = 300) -> dict:
    """GameObject paths in a .prefab/.unity file, relative to the VRC Avatar Descriptor root when there is one.
    Objects that live inside an imported model (FBX) or a nested prefab are often NOT written into the file, so a missing
    path here is a hint, not proof; verify in the Unity Hierarchy."""
    docs = load_documents(Path(file_path))
    go_name, tf_of_go, father, go_of_tf = {}, {}, {}, {}
    for fid, (cls, body) in docs.items():
        if cls == 1:
            go_name[fid] = str(body.get("m_Name", ""))
        elif cls in (4, 224):
            go = int((body.get("m_GameObject") or {}).get("fileID", 0))
            go_of_tf[fid] = go
            tf_of_go[go] = fid
            father[fid] = int((body.get("m_Father") or {}).get("fileID", 0))

    def path_of(go: int) -> str:
        parts, seen = [], set()
        tf = tf_of_go.get(go)
        while tf and tf not in seen:
            seen.add(tf)
            parts.append(go_name.get(go_of_tf.get(tf, 0), "?"))
            tf = father.get(tf, 0)
        return "/".join(reversed(parts))

    root_go = next((int((b.get("m_GameObject") or {}).get("fileID", 0)) for c, b in docs.values() if c == 114 and "baseAnimationLayers" in b), None)
    root_path = path_of(root_go) if root_go else ""
    paths = []
    for go in go_name:
        p = path_of(go)
        if root_path:
            if p == root_path:
                continue
            if not p.startswith(root_path + "/"):
                continue
            p = p[len(root_path) + 1:]
        if p and (not name_contains or name_contains.lower() in p.lower()):
            paths.append(p)
    paths.sort()
    return {"file": file_path, "avatar_root": root_path or None, "count": len(paths), "paths": paths[:limit],
            "caveat": "Children inside imported models/nested prefab instances may be missing from this list." if paths or root_path else
                      "No objects found; the file may consist mostly of prefab instances."}


def scan_avatar_tools(file_path: str) -> dict:
    """Count VRCFury features and Modular Avatar components in a .prefab/.unity file (what the avatar does that its raw controller will not show)."""
    p = Path(file_path)
    if not p.is_file():
        raise ValueError(f"File not found: {file_path}")
    if p.stat().st_size > MAX_BYTES:
        raise ValueError("File too large to scan.")
    text = p.read_text(encoding="utf-8", errors="replace")
    features = Counter(re.findall(r"class: (\w+), ns: VF\.Model\.Feature", text)) + Counter(re.findall(r"type: VF\.Model\.Feature\.(\w+)", text))
    toggles = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.search(r"class: Toggle, ns: VF\.Model\.Feature|type: VF\.Model\.Feature\.Toggle", line):
            for nxt in lines[i + 1:i + 45]:
                m = re.match(r"\s+name: (.+)", nxt)
                if m:
                    toggles.append(m.group(1).strip())
                    break
                if "class:" in nxt and "VF.Model" in nxt:
                    break
    ma = {}
    root = find_project_root(p)
    if root:
        for meta in list((root / "Packages").glob("nadena.dev.modular-avatar*/**/*.cs.meta"))[:400]:
            if meta.name.startswith("ModularAvatar"):
                g = re.search(r"guid: (\w+)", meta.read_text(encoding="utf-8", errors="replace"))
                if g and text.count(g.group(1)):
                    ma[meta.name[:-8]] = text.count(g.group(1))
    return {"file": file_path, "vrcfury_features": dict(features) or None, "vrcfury_toggle_names": toggles or None,
            "modular_avatar_components": ma or None,
            "note": "These tools add animator layers, parameters and menu items at build time, so the avatar can do more than its raw FX controller shows."}


def bloat_scan(project: str, top: int = 15) -> dict:
    """Biggest textures/models in Assets with their import size and compression, to find what inflates download size and VRAM."""
    root = find_project_root(Path(project))
    if root is None:
        raise ValueError(f"{project} is not inside a Unity project.")
    images, models, total_img = [], [], 0
    for f in (root / "Assets").rglob("*"):
        ext = f.suffix.lower()
        if ext in IMAGE_EXT:
            size = f.stat().st_size
            total_img += size
            images.append((size, f))
        elif ext in MODEL_EXT:
            models.append((f.stat().st_size, f))
    images.sort(key=lambda x: -x[0])
    models.sort(key=lambda x: -x[0])
    out = []
    for size, f in images[:top]:
        meta = f.with_name(f.name + ".meta")
        info = {"path": str(f.relative_to(root)).replace("\\", "/"), "mb": round(size / 1e6, 1), "max_size": None, "crunched": None}
        if meta.is_file():
            t = meta.read_text(encoding="utf-8", errors="replace")
            m = re.search(r"buildTarget: DefaultTexturePlatform\s+maxTextureSize: (\d+).*?crunchedCompression: (\d)", t, re.S)
            if m:
                info["max_size"], info["crunched"] = int(m.group(1)), bool(int(m.group(2)))
        out.append(info)
    tips = []
    big = [o for o in out if o["max_size"] and o["max_size"] >= 4096]
    if big:
        tips.append(f"{len(big)} of the largest textures import at 4096+; 2048 or 1024 is plenty for most avatar textures.")
    uncrunched = [o for o in out if o["crunched"] is False and o["mb"] > 2]
    if uncrunched:
        tips.append(f"{len(uncrunched)} large textures are not crunch-compressed (Inspector > Compression > Use Crunch Compression).")
    tips.append("Only textures used by the avatar are uploaded; unused files here do not bloat the upload but do slow Unity.")
    return {"texture_files": len(images), "texture_total_mb_on_disk": round(total_img / 1e6, 1), "largest_textures": out,
            "largest_models": [{"path": str(f.relative_to(root)).replace("\\", "/"), "mb": round(s / 1e6, 1)} for s, f in models[:5]],
            "tips": tips}
