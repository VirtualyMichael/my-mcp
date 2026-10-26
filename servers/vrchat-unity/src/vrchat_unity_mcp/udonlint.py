"""A quick, regex-based lint for UdonSharp scripts: catches the mistakes that otherwise only show up after a slow Unity compile."""

from __future__ import annotations

import re
from pathlib import Path

# (pattern, severity, message)
RULES = [
    (r"\basync\b|\bawait\b", "error", "async/await is not supported by UdonSharp. Use SendCustomEventDelayedSeconds for delays."),
    (r"\byield\s+(return|break)", "error", "Coroutines/iterators are not supported. Use SendCustomEventDelayedSeconds or an Update timer."),
    (r"\btry\s*\{|\bcatch\b|\bfinally\b", "error", "try/catch/finally is not supported in UdonSharp. Validate with if checks instead."),
    (r"using\s+System\.Linq", "error", "LINQ is not available in Udon. Use loops over arrays."),
    (r"using\s+System\.Collections\.Generic|\b(List|Dictionary|HashSet|Queue|Stack)\s*<", "error",
     "System.Collections.Generic types are not available. Use arrays, or VRC DataList / DataDictionary (VRC.SDK3.Data)."),
    (r"using\s+System\.(Threading|Net|IO)\b", "error", "That System namespace is not exposed to Udon."),
    (r"^\s*(public\s+|private\s+|internal\s+)?(interface|struct|enum)\s+\w+", "error",
     "Custom interfaces, structs and enums are not supported in UdonSharp. Use ints/constants."),
    (r"^\s*(public\s+|private\s+|protected\s+|internal\s+)?static\s+(?!readonly)[\w<>\[\]]+\s+\w+\s*(=|;)", "error",
     "Static fields are not supported. Use instance fields (or a shared UdonBehaviour reference)."),
    (r"\bdelegate\b|=>\s*\{", "warning", "Lambdas and delegates are not supported (expression-bodied properties like 'get => x' are fine)."),
    (r"\bnew\s+(Thread|Timer|WaitForSeconds)\b", "error", "Not supported in Udon. Use SendCustomEventDelayedSeconds."),
    (r"\bGameObject\.Find\(|\bFindObjectOfType|\bFindObjectsOfType", "warning", "Find calls are slow and fragile; assign the object in the Inspector instead."),
    (r"\bvoid\s+Update\s*\(", "warning", "Update runs every frame for every client. Prefer events when you can."),
    (r"\$\"", "warning", "String interpolation may not be supported by your UdonSharp version; use string concatenation."),
    (r"\bConvert\.To|\bstring\.Format\(", "warning", "These .NET helpers may not be exposed; use simple casts or concatenation."),
]


def lint(path: str) -> dict:
    p = Path(path)
    if not p.is_file() or p.suffix != ".cs":
        raise ValueError(f"{path} is not a .cs file.")
    text = p.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    findings: list[dict] = []

    def add(sev, msg, line=None):
        findings.append({"severity": sev, "line": line, "message": msg})

    for i, line in enumerate(lines, 1):
        code = line.split("//")[0]
        for pat, sev, msg in RULES:
            if re.search(pat, code):
                add(sev, msg, i)

    cls = re.search(r"class\s+(\w+)\s*:\s*(\w+)", text)
    if not cls:
        add("error", "No class found. A script needs 'public class Name : UdonSharpBehaviour'.")
    else:
        name, base = cls.groups()
        if name != p.stem:
            add("error", f"Class name '{name}' must equal the file name '{p.stem}', or Unity cannot attach it.")
        if base != "UdonSharpBehaviour":
            add("error", f"'{name}' derives from '{base}'; it must derive from UdonSharpBehaviour.")
    if "using UdonSharp;" not in text:
        add("error", "Missing 'using UdonSharp;'.")

    mode = re.search(r"BehaviourSyncMode\.(\w+)", text)
    synced = "[UdonSynced" in text
    if synced and not mode:
        add("warning", "Has [UdonSynced] fields but no [UdonBehaviourSyncMode(...)]; add Manual (state) or Continuous (movement).")
    if synced and mode and mode.group(1) in ("None", "NoVariableSync"):
        add("error", f"[UdonSynced] fields with BehaviourSyncMode.{mode.group(1)} will never sync.")
    if synced and mode and mode.group(1) == "Manual" and "RequestSerialization" not in text:
        add("error", "Manual sync mode but RequestSerialization() is never called, so changes never reach other players.")
    if synced and "SetOwner" not in text and "IsOwner" not in text:
        add("warning", "Synced fields only propagate from the owner; call Networking.SetOwner(Networking.LocalPlayer, gameObject) before writing.")

    for m in re.finditer(r"SendCustomNetworkEvent\s*\([^,]+,\s*nameof\((\w+)\)", text):
        meth = m.group(1)
        if re.search(rf"private\s+void\s+{meth}\b", text):
            add("error", f"Network event '{meth}' must be public; private methods cannot be called remotely.")
        if re.search(rf"void\s+{meth}\s*\(\s*[^)\s]", text):
            add("error", f"Network event '{meth}' cannot take parameters.")

    if re.search(r"Networking\.LocalPlayer\.\w+", text) and "IsValid" not in text and "!= null" not in text:
        add("warning", "Networking.LocalPlayer can be null in the editor; check Utilities.IsValid before using it.")
    for m in re.finditer(r"void\s+(OnPlayer\w+|OnPickup\w*|OnDrop|OnDeserialization|OnPostSerialization|OnOwnershipTransferred|Interact)\s*\(", text):
        if "override" not in text[max(0, m.start() - 30):m.start()]:
            add("error", f"'{m.group(1)}' must be declared 'public override void {m.group(1)}(...)' to run as an Udon event.")

    order = {"error": 0, "warning": 1}
    findings.sort(key=lambda f: (order[f["severity"]], f["line"] or 0))
    return {"file": str(p), "errors": sum(f["severity"] == "error" for f in findings),
            "warnings": sum(f["severity"] == "warning" for f in findings),
            "findings": findings or [{"severity": "ok", "message": "No problems found by the quick lint."}],
            "note": "A regex lint, not a compiler. Unity's Console is the final judge."}
