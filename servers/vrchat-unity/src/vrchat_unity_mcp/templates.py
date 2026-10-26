"""UdonSharp script templates for VRChat worlds, and the safe writer that puts them into a project."""

from __future__ import annotations

import re
from pathlib import Path

from vrchat_unity_mcp.unityyaml import find_project_root

HEADER = "using UdonSharp;\nusing UnityEngine;\nusing VRC.SDKBase;\nusing VRC.Udon;\n"
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_CS_KEYWORDS = {"abstract", "as", "base", "bool", "break", "byte", "case", "catch", "char", "class", "const", "continue", "decimal", "default",
                "delegate", "do", "double", "else", "enum", "event", "explicit", "extern", "false", "finally", "float", "for", "foreach", "goto",
                "if", "implicit", "in", "int", "interface", "internal", "is", "lock", "long", "namespace", "new", "null", "object", "operator",
                "out", "override", "params", "private", "protected", "public", "readonly", "ref", "return", "sbyte", "sealed", "short", "sizeof",
                "static", "string", "struct", "switch", "this", "throw", "true", "try", "typeof", "uint", "ulong", "unchecked", "unsafe",
                "ushort", "using", "virtual", "void", "volatile", "while"}


def _sync_attr(synced: bool) -> str:
    return "[UdonBehaviourSyncMode(BehaviourSyncMode.Manual)]" if synced else "[UdonBehaviourSyncMode(BehaviourSyncMode.None)]"


def interact_toggle(cls: str, synced: bool = False, **_) -> str:
    if not synced:
        return f"""{HEADER}
{_sync_attr(False)}
public class {cls} : UdonSharpBehaviour
{{
    [Tooltip("Objects switched on/off when a player clicks this object (needs a Collider).")]
    public GameObject[] targets;
    [Tooltip("State when the world loads.")]
    public bool startOn = false;

    private bool isOn;

    void Start()
    {{
        isOn = startOn;
        Apply();
    }}

    public override void Interact()
    {{
        isOn = !isOn;
        Apply();
    }}

    private void Apply()
    {{
        foreach (GameObject t in targets)
        {{
            if (t != null) t.SetActive(isOn);
        }}
    }}
}}
"""
    return f"""{HEADER}
{_sync_attr(True)}
public class {cls} : UdonSharpBehaviour
{{
    [Tooltip("Objects switched on/off for EVERYONE (including late joiners) when a player clicks this object (needs a Collider).")]
    public GameObject[] targets;
    [Tooltip("State when the world loads.")]
    public bool startOn = false;

    [UdonSynced, FieldChangeCallback(nameof(IsOn))]
    private bool _isOn;

    public bool IsOn
    {{
        get => _isOn;
        set
        {{
            _isOn = value;
            Apply();
        }}
    }}

    void Start()
    {{
        // Every client starts from the same value; later changes (and late joiners) arrive through the synced field.
        IsOn = startOn;
    }}

    public override void Interact()
    {{
        Networking.SetOwner(Networking.LocalPlayer, gameObject);
        IsOn = !IsOn;
        RequestSerialization();
    }}

    private void Apply()
    {{
        foreach (GameObject t in targets)
        {{
            if (t != null) t.SetActive(_isOn);
        }}
    }}
}}
"""


def teleporter(cls: str, on_trigger: bool = False, **_) -> str:
    entry = ("""    public override void OnPlayerTriggerEnter(VRCPlayerApi player)
    {
        if (player != null && player.isLocal) Teleport();
    }""" if on_trigger else """    public override void Interact()
    {
        Teleport();
    }""")
    note = "Put a Collider with Is Trigger ON on this object." if on_trigger else "Needs a Collider on this object so players can click it."
    return f"""{HEADER}
{_sync_attr(False)}
public class {cls} : UdonSharpBehaviour
{{
    [Tooltip("Where the player lands. Position AND facing direction are used. {note}")]
    public Transform destination;

{entry}

    private void Teleport()
    {{
        VRCPlayerApi me = Networking.LocalPlayer;
        if (!Utilities.IsValid(me) || destination == null) return;
        me.TeleportTo(destination.position, destination.rotation);
    }}
}}
"""


def audio_button(cls: str, **_) -> str:
    return f"""{HEADER}
{_sync_attr(False)}
public class {cls} : UdonSharpBehaviour
{{
    [Tooltip("Plays or stops this source for the local player. Needs a Collider on THIS object to be clickable.")]
    public AudioSource source;

    public override void Interact()
    {{
        if (source == null) return;
        if (source.isPlaying) source.Stop();
        else source.Play();
    }}
}}
"""


def trigger_zone(cls: str, **_) -> str:
    return f"""{HEADER}
{_sync_attr(False)}
public class {cls} : UdonSharpBehaviour
{{
    [Tooltip("Shown only to the local player while they stand inside this zone. Needs a Collider with Is Trigger ON.")]
    public GameObject[] showWhileInside;
    [Tooltip("Hidden only while the local player is inside.")]
    public GameObject[] hideWhileInside;

    void Start()
    {{
        Set(false);
    }}

    public override void OnPlayerTriggerEnter(VRCPlayerApi player)
    {{
        if (player != null && player.isLocal) Set(true);
    }}

    public override void OnPlayerTriggerExit(VRCPlayerApi player)
    {{
        if (player != null && player.isLocal) Set(false);
    }}

    private void Set(bool inside)
    {{
        foreach (GameObject g in showWhileInside) if (g != null) g.SetActive(inside);
        foreach (GameObject g in hideWhileInside) if (g != null) g.SetActive(!inside);
    }}
}}
"""


def spinner(cls: str, **_) -> str:
    return f"""{HEADER}
{_sync_attr(False)}
public class {cls} : UdonSharpBehaviour
{{
    [Tooltip("Degrees per second around each local axis. Runs locally on every client; spinning is cosmetic.")]
    public Vector3 degreesPerSecond = new Vector3(0f, 45f, 0f);

    void Update()
    {{
        transform.Rotate(degreesPerSecond * Time.deltaTime, Space.Self);
    }}
}}
"""


def pickup_events(cls: str, **_) -> str:
    return f"""{HEADER}
{_sync_attr(False)}
public class {cls} : UdonSharpBehaviour
{{
    [Tooltip("Optional: shown only while the object is held by the local player.")]
    public GameObject heldIndicator;
    [Tooltip("Optional: played when the use button is pressed (trigger/click) while held.")]
    public AudioSource useSound;

    // Put this on an object that already has VRC Pickup + Collider (+ Rigidbody). Add VRC Object Sync to sync it for others.
    public override void OnPickup()
    {{
        if (heldIndicator != null) heldIndicator.SetActive(true);
    }}

    public override void OnDrop()
    {{
        if (heldIndicator != null) heldIndicator.SetActive(false);
    }}

    public override void OnPickupUseDown()
    {{
        if (useSound != null) useSound.Play();
    }}
}}
"""


def animator_switch(cls: str, synced: bool = False, parameter: str = "Open", **_) -> str:
    parameter = parameter if _IDENT.match(parameter) else "Open"
    if not synced:
        return f"""{HEADER}
{_sync_attr(False)}
public class {cls} : UdonSharpBehaviour
{{
    [Tooltip("Animator with a Bool parameter named \\"{parameter}\\" (e.g. a door). Needs a Collider on this object.")]
    public Animator animator;
    private bool state;

    public override void Interact()
    {{
        state = !state;
        if (animator != null) animator.SetBool("{parameter}", state);
    }}
}}
"""
    return f"""{HEADER}
{_sync_attr(True)}
public class {cls} : UdonSharpBehaviour
{{
    [Tooltip("Animator with a Bool parameter named \\"{parameter}\\" (e.g. a door). Needs a Collider on this object.")]
    public Animator animator;

    [UdonSynced, FieldChangeCallback(nameof(State))]
    private bool _state;

    public bool State
    {{
        get => _state;
        set
        {{
            _state = value;
            if (animator != null) animator.SetBool("{parameter}", _state);
        }}
    }}

    public override void Interact()
    {{
        Networking.SetOwner(Networking.LocalPlayer, gameObject);
        State = !State;
        RequestSerialization();
    }}
}}
"""


def join_greeter(cls: str, **_) -> str:
    return f"""{HEADER}using TMPro;

{_sync_attr(False)}
public class {cls} : UdonSharpBehaviour
{{
    [Tooltip("A TextMeshPro text object (UI or 3D) that shows the latest join/leave.")]
    public TMP_Text label;

    public override void OnPlayerJoined(VRCPlayerApi player)
    {{
        if (label != null && Utilities.IsValid(player)) label.text = player.displayName + " joined";
    }}

    public override void OnPlayerLeft(VRCPlayerApi player)
    {{
        if (label != null && Utilities.IsValid(player)) label.text = player.displayName + " left";
    }}
}}
"""


TEMPLATES = {
    "interact_toggle": (interact_toggle, "Click to show/hide objects. Option synced=true shares it with everyone and late joiners."),
    "teleporter": (teleporter, "Click (or walk into a trigger, option on_trigger=true) to teleport the local player to a destination Transform."),
    "audio_button": (audio_button, "Click to play/stop an AudioSource."),
    "trigger_zone": (trigger_zone, "Show/hide objects for the local player while they stand in a trigger collider."),
    "spinner": (spinner, "Continuously rotates the object (local, cosmetic)."),
    "pickup_events": (pickup_events, "Reacts to a VRC Pickup being picked up / dropped / used."),
    "animator_switch": (animator_switch, "Click to flip a Bool on an Animator (doors, lifts). Options: synced, parameter."),
    "join_greeter": (join_greeter, "Writes 'Name joined/left' into a TextMeshPro label."),
}


def list_templates() -> list[dict]:
    return [{"template": k, "description": d} for k, (_, d) in TEMPLATES.items()]


def validate_class_name(name: str) -> str:
    if not _IDENT.match(name) or name in _CS_KEYWORDS:
        raise ValueError(f"'{name}' is not a valid C# class name (letters, digits, underscore; no spaces; cannot start with a digit).")
    return name


def render(template: str, class_name: str, **options) -> str:
    if template not in TEMPLATES:
        raise ValueError(f"Unknown template '{template}'. Available: {', '.join(TEMPLATES)}")
    validate_class_name(class_name)
    return TEMPLATES[template][0](class_name, **options)


def write_script(project: str, template: str, class_name: str, folder: str = "Assets/Scripts/ClaudeVRC", **options) -> dict:
    root = find_project_root(Path(project))
    if root is None:
        raise ValueError(f"{project} is not inside a Unity project.")
    folder_path = (root / folder).resolve()
    if not str(folder_path).startswith(str((root / "Assets").resolve())):
        raise ValueError("Scripts can only be written inside the project's Assets folder.")
    code = render(template, class_name, **options)
    target = folder_path / f"{class_name}.cs"
    if target.exists():
        raise ValueError(f"{target.relative_to(root)} already exists; pick another class name (nothing was overwritten).")
    folder_path.mkdir(parents=True, exist_ok=True)
    target.write_text(code, encoding="utf-8", newline="\n")
    return {"written": str(target), "project_relative": str(target.relative_to(root)).replace("\\", "/")}
