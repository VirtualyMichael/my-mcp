"""The built-in curriculum and error explainer."""

from __future__ import annotations

import re
from importlib import resources

LEVELS = {
    "beginner": ["getting-started", "unity-basics", "avatar-basics", "avatar-upload", "avatar-toggles", "troubleshooting"],
    "intermediate": ["avatar-parameters-and-menu", "fx-controller", "write-defaults", "animation-basics", "performance-ranks",
                     "tools-ecosystem", "world-basics"],
    "advanced": ["advanced-animation", "physbones-contacts", "udonsharp-basics"],
}


def _all() -> dict[str, str]:
    out = {}
    base = resources.files("vrchat_unity_mcp").joinpath("guides")
    for f in sorted(base.iterdir(), key=lambda p: p.name):
        if f.name.endswith(".md"):
            out[re.sub(r"^\d+-", "", f.name[:-3])] = f.read_text(encoding="utf-8")
    return out


def topics() -> list[dict]:
    docs = _all()
    level_of = {t: lv for lv, ts in LEVELS.items() for t in ts}
    return [{"topic": k, "level": level_of.get(k, "intermediate"), "title": v.splitlines()[0].lstrip("# ")} for k, v in docs.items()]


def get(topic: str) -> str:
    docs = _all()
    key = topic.strip().lower().replace(" ", "-").replace("_", "-")
    if key in docs:
        return docs[key]
    hits = [k for k in docs if key in k or k in key]
    if len(hits) == 1:
        return docs[hits[0]]
    words = set(re.findall(r"\w+", topic.lower()))
    scored = sorted(((sum(w in text.lower() for w in words), k) for k, text in docs.items()), reverse=True)
    best = [k for s, k in scored[:3] if s]
    raise ValueError(f"No guide called '{topic}'. " + (f"Closest: {', '.join(best)}. " if best else "") + f"All topics: {', '.join(docs)}.")


def path(level: str) -> list[str]:
    if level not in LEVELS:
        raise ValueError(f"level must be one of {', '.join(LEVELS)}")
    order = list(LEVELS)
    return [t for lv in order[: order.index(level) + 1] for t in LEVELS[lv]]


ERRORS = [
    (r"over.*(256|parameter memory)|too many parameters|parameter.*(exceeds|too much)",
     "Your synced Expression Parameters exceed 256 bits.",
     "Open the Expression Parameters asset. Untick Synced for parameters only you need, replace several Bools with one Int selector, delete unused entries. Bool=1 bit, Int/Float=8."),
    (r"missing script|the referenced script .* is missing|script.*is missing",
     "A component's script is gone (package removed or file deleted).",
     "Select the object, find the component marked '(Script)', and Remove Component. Reinstall the package if it should exist."),
    (r"the type or namespace name '?(UdonSharp|VRC)",
     "Scripts reference the VRChat/UdonSharp SDK but the project does not have it (or the wrong SDK type).",
     "Avatar projects have no UdonSharp. Worlds need the Worlds SDK. Add/repair via VCC > Manage Project, then let Unity recompile."),
    (r"the type or namespace name '?(TMPro|TextMeshPro)",
     "TextMeshPro is not imported.", "Window > TextMeshPro > Import TMP Essential Resources."),
    (r"error cs\d+",
     "A C# compile error. Any compile error blocks building/uploading.",
     "Read the first error in the Console (double-click to jump to the line). Fix or delete that script. Later errors are often side effects of the first."),
    (r"(pink|magenta) (material|avatar)|shader.*(not supported|unsupported|missing)|hidden/internalerror",
     "The material's shader is missing or not allowed in VRChat.",
     "Switch to a supported shader (lilToon, Poiyomi, or Standard) and re-apply the textures."),
    (r"unity (version|editor).*(mismatch|incompatible|not supported)|wrong unity version",
     "The project is being opened with a Unity version VRChat does not support.",
     "Open the project from VCC, which picks the right Unity version. Do not upgrade Unity manually."),
    (r"package resolution|failed to resolve packages|vpm.*(fail|error)",
     "VCC/Unity could not resolve a package.",
     "Close Unity, open VCC > Manage Project and reinstall/update the failing package, check the internet connection, then reopen."),
    (r"new user|trust rank|you must.*rank|upload.*not allowed",
     "Your VRChat account is not yet trusted enough to upload.", "Play VRChat for a while to reach New User rank; there is no workaround."),
    (r"nullreferenceexception",
     "Something the script/tool expected is not assigned.",
     "Check the stack trace for the first line in your own code or the tool; usually an empty Inspector field."),
    (r"could not (create|load) .*animator|animator controller.*missing|controller.*missing|playable layers",
     "A Playable Layer on the Avatar Descriptor points at a missing/invalid controller.",
     "Avatar Descriptor > Customize Playable Layers; reassign FX (and others) or tick Default for stock ones."),
    (r"lightmap|baked.*black|black.*(world|avatar)",
     "Lighting problem (unbaked lightmaps, missing light probes) or a bad normal map.",
     "Bake lighting (Window > Rendering > Lighting), add light probes/reflection probes, check shader settings."),
    (r"networking\.|not owner|ownership|synced.*not.*(work|update)",
     "UdonSharp networking: only the owner may change synced variables and must call RequestSerialization().",
     "Networking.SetOwner(Networking.LocalPlayer, gameObject); change the variable; RequestSerialization(); use Manual sync mode."),
    (r"is not exposed|not exposed to udon|udon.*not (allowed|exposed)",
     "That API is not whitelisted for Udon.", "Find an exposed alternative (see the Udon node browser / U# docs); do not use that .NET or Unity API."),
]


def explain(text: str) -> dict:
    low = text.lower()
    hits = [{"meaning": m, "fix": f} for pat, m, f in ERRORS if re.search(pat, low)]
    if not hits:
        return {"matched": False, "advice": "No known pattern. Share the first red error line from the Console and what you were doing; "
                "also try the troubleshooting guide (get_vrchat_guide 'troubleshooting')."}
    return {"matched": True, "possible_causes": hits}
