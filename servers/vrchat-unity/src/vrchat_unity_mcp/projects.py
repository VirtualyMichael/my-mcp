"""Find VRChat/Unity projects, inspect them, and analyse avatar assets. Read-only."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from vrchat_unity_mcp.unityyaml import UnityYamlError, find_project_root, guid_index, load_documents

PARAM_TYPE = {0: "Int", 1: "Float", 2: "Bool"}
PARAM_BITS = {"Int": 8, "Float": 8, "Bool": 1}
ANIM_PARAM_TYPE = {1: "Float", 3: "Int", 4: "Bool", 9: "Trigger"}
COND_MODE = {1: "==true", 2: "==false", 3: ">", 4: "<", 6: "==", 7: "!="}
CONTROL_TYPE = {101: "Button", 102: "Toggle", 103: "SubMenu", 201: "TwoAxisPuppet", 202: "FourAxisPuppet", 203: "RadialPuppet"}
MAX_SYNC_BITS = 256
BUILTIN_PARAMS = {
    "IsLocal", "Viseme", "Voice", "GestureLeft", "GestureRight", "GestureLeftWeight", "GestureRightWeight", "AngularY", "VelocityX",
    "VelocityY", "VelocityZ", "VelocityMagnitude", "Upright", "Grounded", "Seated", "AFK", "TrackingType", "VRMode", "MuteSelf",
    "InStation", "Earmuffs", "IsOnFriendsList", "AvatarVersion", "IsAnimatorEnabled", "ScaleModified", "ScaleFactor",
    "ScaleFactorInverse", "EyeHeightAsMeters", "EyeHeightAsPercent", "PreviewMode", "VisemeLevel", "MuteSelf", "VRCEmote", "VRCFaceBlendH", "VRCFaceBlendV",
}


def vcc_settings_path() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "VRChatCreatorCompanion" / "settings.json"


def find_projects() -> list[dict]:
    """Projects known to the VRChat Creator Companion, plus where it keeps them."""
    path = vcc_settings_path()
    out = []
    if path.is_file():
        try:
            settings = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            settings = {}
        for p in settings.get("userProjects", []):
            out.append(_brief(Path(p)))
    return out


def _brief(p: Path) -> dict:
    exists = (p / "Assets").is_dir()
    info = {"path": str(p), "name": p.name, "exists": exists}
    if exists:
        info["unity_version"] = unity_version(p)
        info["kind"] = project_kind(p)
        info["open_in_unity"] = is_open(p)
    return info


def unity_version(root: Path) -> str | None:
    f = root / "ProjectSettings" / "ProjectVersion.txt"
    if f.is_file():
        m = re.search(r"m_EditorVersion:\s*(\S+)", f.read_text(encoding="utf-8", errors="replace"))
        return m.group(1) if m else None
    return None


def vpm_packages(root: Path) -> dict[str, str]:
    f = root / "Packages" / "vpm-manifest.json"
    if not f.is_file():
        return {}
    try:
        deps = json.loads(f.read_text(encoding="utf-8")).get("dependencies", {})
    except (OSError, ValueError):
        return {}
    return {k: v.get("version", "?") if isinstance(v, dict) else str(v) for k, v in deps.items()}


def project_kind(root: Path) -> str:
    pk = vpm_packages(root)
    avatar, world = "com.vrchat.avatars" in pk, "com.vrchat.worlds" in pk
    return "avatar" if avatar and not world else "world" if world and not avatar else "unknown" if not (avatar or world) else "both"


def is_open(root: Path) -> bool:
    """True when a Unity editor is probably holding the project open (its lock file exists and cannot be removed/opened)."""
    lock = root / "Temp" / "UnityLockfile"
    if not lock.exists():
        return False
    try:
        with open(lock, "r+b"):
            pass
        return False
    except OSError:
        return True


def inspect_project(path: str) -> dict:
    root = find_project_root(Path(path))
    if root is None:
        raise ValueError(f"{path} is not inside a Unity project (needs Assets/ and ProjectSettings/).")
    pk = vpm_packages(root)
    assets = {"controllers": [], "expression_parameters": [], "expression_menus": [], "scenes": [], "udon_scripts": 0}
    for f in (root / "Assets").rglob("*"):
        if not f.is_file():
            continue
        rel = str(f.relative_to(root)).replace("\\", "/")
        if f.suffix == ".controller":
            assets["controllers"].append(rel)
        elif f.suffix == ".unity":
            assets["scenes"].append(rel)
        elif f.suffix == ".asset" and f.stat().st_size < 2_000_000:
            kind = _classify_asset(f)
            if kind:
                assets[kind].append(rel)
        elif f.suffix == ".cs" and "UdonSharpBehaviour" in _head(f):
            assets["udon_scripts"] += 1
    sdk = {k: v for k, v in pk.items() if k.startswith(("com.vrchat", "nadena", "com.vrcfury", "vrcfury", "com.anatawa12", "jp.lilxyzw", "com.poiyomi"))}
    return {"root": str(root), "kind": project_kind(root), "unity_version": unity_version(root), "open_in_unity": is_open(root),
            "relevant_packages": sdk, **{k: (v[:60] if isinstance(v, list) else v) for k, v in assets.items()},
            "truncated_lists_at": 60}


def _head(f: Path, n: int = 4000) -> str:
    try:
        with open(f, "r", encoding="utf-8", errors="replace") as h:
            return h.read(n)
    except OSError:
        return ""


def _classify_asset(f: Path) -> str | None:
    head = _head(f, 1200)
    if "\n  parameters:" in head:
        return "expression_parameters"
    if "\n  controls:" in head:
        return "expression_menus"
    return None


# ---------------------------------------------------------------- controller analysis

def analyze_controller(path: str) -> dict:
    p = Path(path)
    docs = load_documents(p)
    root = find_project_root(p)
    guids = guid_index(root) if root else {}
    ctrl = next((b for c, b in docs.values() if c == 91), None)
    if ctrl is None:
        raise ValueError(f"{p.name} contains no AnimatorController.")
    params = [{"name": q.get("m_Name"), "type": ANIM_PARAM_TYPE.get(q.get("m_Type"), str(q.get("m_Type"))),
               "default": q.get("m_DefaultBool") if q.get("m_Type") == 4 else q.get("m_DefaultInt") if q.get("m_Type") == 3 else q.get("m_DefaultFloat")}
              for q in ctrl.get("m_AnimatorParameters", [])]
    pnames = {q["name"] for q in params}
    layers, wd_on, wd_off, issues, used = [], 0, 0, [], set()

    def get(fid):
        return docs.get(fid, (None, {}))[1]

    for i, layer in enumerate(ctrl.get("m_AnimatorLayers", [])):
        sm = get(_fid(layer.get("m_StateMachine")))
        states, transitions = [], 0
        any_state = []
        for t in sm.get("m_AnyStateTransitions", []):
            td = get(_fid(t))
            conds = [f"{c.get('m_ConditionEvent')} {COND_MODE.get(c.get('m_ConditionMode'), '?')}"
                     + ("" if c.get("m_ConditionMode") in (1, 2) else f" {c.get('m_EventTreshold')}") for c in td.get("m_Conditions", [])]
            used.update(c.get("m_ConditionEvent") for c in td.get("m_Conditions", []))
            any_state.append({"to": get(_fid(td.get("m_DstState"))).get("m_Name", "(exit)"), "conditions": conds})
        for st in _iter_states(sm, get):
            state = get(st)
            wd = bool(state.get("m_WriteDefaultValues"))
            wd_on += wd
            wd_off += not wd
            motion = state.get("m_Motion") or {}
            mfid = _fid(motion)
            if mfid and mfid in docs and docs[mfid][0] == 206:
                mdesc = "blend tree: " + str(docs[mfid][1].get("m_Name", ""))
            else:
                mdesc = guids.get(str(motion.get("guid")), None) if motion.get("guid") else None
                mdesc = mdesc or ("none" if not mfid and not motion.get("guid") else "clip")
            tr = []
            for t in state.get("m_Transitions", []):
                td = get(_fid(t))
                conds = []
                for c in td.get("m_Conditions", []):
                    conds.append(f"{c.get('m_ConditionEvent')} {COND_MODE.get(c.get('m_ConditionMode'), '?')}"
                                 + ("" if c.get("m_ConditionMode") in (1, 2) else f" {c.get('m_EventTreshold')}"))
                    used.add(c.get("m_ConditionEvent"))
                dst = get(_fid(td.get("m_DstState")))
                tr.append({"to": dst.get("m_Name", "(exit)"), "conditions": conds, "exit_time": bool(td.get("m_HasExitTime")),
                           "duration": td.get("m_TransitionDuration")})
                transitions += 1
            states.append({"name": state.get("m_Name"), "write_defaults": wd, "motion": mdesc, "behaviours": len(state.get("m_Behaviours", [])),
                           "transitions": tr})
        if i > 0 and not layer.get("m_DefaultWeight"):
            issues.append(f"Layer '{layer.get('m_Name')}' has weight 0 and will do nothing unless a driver enables it.")
        layers.append({"index": i, "name": layer.get("m_Name"), "weight": layer.get("m_DefaultWeight"),
                       "any_state_transitions": any_state, "states": states})
    for u in sorted(x for x in used if x and x not in pnames):
        issues.append(f"Transition uses parameter '{u}' which is not declared in the controller's Parameters list.")
    if wd_on and wd_off:
        issues.append(f"Mixed Write Defaults: {wd_on} states ON, {wd_off} OFF. Pick one convention (see write-defaults guide).")
    return {"controller": str(p), "parameters": params, "layer_count": len(layers), "layers": layers,
            "write_defaults": "mixed" if wd_on and wd_off else "on" if wd_on else "off" if wd_off else "no states",
            "issues": issues}


def _fid(ref) -> int:
    return int(ref.get("fileID", 0)) if isinstance(ref, dict) else 0


def _iter_states(sm: dict, get):
    for cs in sm.get("m_ChildStates", []):
        yield _fid(cs.get("m_State"))
    for sub in sm.get("m_ChildStateMachines", []):
        yield from _iter_states(get(_fid(sub.get("m_StateMachine"))), get)


# ---------------------------------------------------------------- expression assets

def read_expression_parameters(path: str) -> dict:
    docs = load_documents(Path(path))
    body = next((b for c, b in docs.values() if c == 114 and "parameters" in b), None)
    if body is None:
        raise ValueError(f"{Path(path).name} is not a VRCExpressionParameters asset.")
    items, bits = [], 0
    for q in body.get("parameters", []):
        t = PARAM_TYPE.get(q.get("valueType"), "?")
        synced = bool(q.get("networkSynced", 1))
        if synced:
            bits += PARAM_BITS.get(t, 0)
        items.append({"name": q.get("name"), "type": t, "default": q.get("defaultValue"), "saved": bool(q.get("saved")), "synced": synced})
    return {"path": str(path), "parameters": items, "synced_bits_used": bits, "synced_bits_max": MAX_SYNC_BITS,
            "over_budget": bits > MAX_SYNC_BITS}


def read_expression_menu(path: str) -> dict:
    p = Path(path)
    docs = load_documents(p)
    body = next((b for c, b in docs.values() if c == 114 and "controls" in b), None)
    if body is None:
        raise ValueError(f"{p.name} is not a VRCExpressionsMenu asset.")
    controls = []
    for c in body.get("controls", []):
        param = (c.get("parameter") or {}).get("name") or ""
        subs = [s.get("name") for s in c.get("subParameters", []) or [] if s and s.get("name")]
        controls.append({"name": c.get("name"), "type": CONTROL_TYPE.get(c.get("type"), str(c.get("type"))), "parameter": param or None,
                         "sub_parameters": subs, "value": c.get("value"), "has_submenu": bool((c.get("subMenu") or {}).get("guid"))})
    return {"path": str(p), "control_count": len(controls), "full": len(controls) >= 8, "controls": controls}


def analyze_avatar_assets(controller: str, parameters: str, menu: str | None = None) -> dict:
    """Cross-check an avatar's FX controller against its expression parameters (and root menu)."""
    ctrl = analyze_controller(controller)
    par = read_expression_parameters(parameters)
    cparams = {q["name"]: q["type"] for q in ctrl["parameters"]}
    eparams = {q["name"]: q["type"] for q in par["parameters"]}
    issues = list(ctrl["issues"])
    if par["over_budget"]:
        issues.append(f"Synced parameters use {par['synced_bits_used']} bits; the limit is {MAX_SYNC_BITS}.")
    for n, t in eparams.items():
        if n not in cparams:
            issues.append(f"Expression parameter '{n}' is not in the controller, so nothing animates from it.")
        elif cparams[n] != t:
            issues.append(f"Type mismatch for '{n}': expression {t} vs controller {cparams[n]}.")
    if menu:
        m = read_expression_menu(menu)
        for c in m["controls"]:
            for pn in ([c["parameter"]] if c["parameter"] else []) + c["sub_parameters"]:
                if pn not in eparams and pn not in BUILTIN_PARAMS:
                    issues.append(f"Menu control '{c['name']}' uses parameter '{pn}' that is not in Expression Parameters.")
    return {"issues": issues or ["No problems found."], "controller_parameters": len(cparams), "expression_parameters": len(eparams),
            "synced_bits_used": par["synced_bits_used"], "write_defaults": ctrl["write_defaults"]}
