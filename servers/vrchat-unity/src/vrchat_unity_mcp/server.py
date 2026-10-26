"""MCP server (stdio) for VRChat + Unity creation: teaches, inspects projects, writes UdonSharp, and edits avatar controllers.

  teach      list_vrchat_guides, get_vrchat_guide, learning_path, explain_vrchat_error
  inspect    find_vrchat_projects, inspect_vrchat_project, analyze_controller, read_expression_parameters,
             read_expression_menu, check_avatar_setup, list_scene_objects, scan_avatar_tools, project_bloat_scan,
             lint_udon_script, list_job_backups                                (all read-only)
  write      list_script_templates, generate_udon_script (new .cs file only, never overwrites)
  control    queue_avatar_job (installs a Unity-side runner + writes a job), run_unity_jobs (headless Unity applies it),
             restore_job_backup (puts the three assets back as they were)

Avatar edits happen inside Unity through a runner script that backs up every asset, validates first and rolls back on failure.
"""

from __future__ import annotations

import functools
import json

try:  # MCP SDK 2.x
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:  # MCP SDK 1.x
    from mcp.server.fastmcp import FastMCP as _Server
from mcp.types import ToolAnnotations

from vrchat_unity_mcp import backups, guides, jobs, projects, scan, templates, udonlint
from vrchat_unity_mcp.unityyaml import UnityYamlError

INSTRUCTIONS = (
    "Helps people make VRChat avatars and worlds in Unity, from first install to FX controllers and UdonSharp. Ask or infer the user's "
    "experience level, then teach with get_vrchat_guide / learning_path in plain words. Before changing anything, inspect the project "
    "(inspect_vrchat_project, analyze_controller, check_avatar_setup). Edits: generate_udon_script writes only new .cs files; avatar changes "
    "go through queue_avatar_job, which is applied inside Unity with backups. Tell the user what you will change and get their OK first, "
    "and never run_unity_jobs on a project that is open in Unity. Do not claim something works until it has been Build & Tested."
)

mcp = _Server("vrchat-unity", instructions=INSTRUCTIONS)
RO = ToolAnnotations(readOnlyHint=True)


def _json(obj) -> str:
    return json.dumps(obj, indent=2, default=str)


def _safe(fn):
    @functools.wraps(fn)
    def wrapper(*a, **k):
        try:
            return fn(*a, **k)
        except (ValueError, UnityYamlError, OSError) as e:
            return f"Not done: {e}"

    return wrapper


@mcp.tool(annotations=RO)
def list_vrchat_guides() -> str:
    """All built-in guides with their level (beginner / intermediate / advanced)."""
    return _json(guides.topics())


@mcp.tool(annotations=RO)
@_safe
def get_vrchat_guide(topic: str) -> str:
    """Full text of one guide, e.g. 'getting-started', 'avatar-toggles', 'fx-controller', 'write-defaults', 'udonsharp-basics'.
    Partial names work. Teach from it in the user's own words; do not dump it all at once."""
    return guides.get(topic)


@mcp.tool(annotations=RO)
@_safe
def learning_path(level: str = "beginner") -> str:
    """Ordered guide list for a level: beginner (install to first toggle), intermediate (adds controllers, parameters, optimisation, worlds),
    advanced (adds blend trees, drivers, PhysBones/Contacts, UdonSharp)."""
    return _json(guides.path(level))


@mcp.tool(annotations=RO)
def explain_vrchat_error(error_text: str) -> str:
    """Paste a Console/SDK error or symptom; get likely meaning and fixes for common VRChat/Unity problems."""
    return _json(guides.explain(error_text))


@mcp.tool(annotations=RO)
def find_vrchat_projects() -> str:
    """Unity projects registered in the VRChat Creator Companion, with Unity version, avatar/world kind, and whether Unity has them open."""
    return _json(projects.find_projects())


@mcp.tool(annotations=RO)
@_safe
def inspect_vrchat_project(project_path: str) -> str:
    """Summarise a project: Unity version, SDK/packages (Modular Avatar, VRCFury, AAO...), animator controllers, expression
    parameter/menu assets, scenes, and UdonSharp script count. Lists are capped at 60."""
    return _json(projects.inspect_project(project_path))


@mcp.tool(annotations=RO)
@_safe
def analyze_controller(controller_path: str) -> str:
    """Read an Animator Controller (.controller): parameters, layers, states, transitions and conditions, Write Defaults, and problems
    (zero-weight layers, mixed Write Defaults, undeclared parameters). Needs text serialization (Unity default)."""
    return _json(projects.analyze_controller(controller_path))


@mcp.tool(annotations=RO)
@_safe
def read_expression_parameters(parameters_asset_path: str) -> str:
    """Read a VRCExpressionParameters asset: each parameter, and how many of the 256 synced bits are used."""
    return _json(projects.read_expression_parameters(parameters_asset_path))


@mcp.tool(annotations=RO)
@_safe
def read_expression_menu(menu_asset_path: str) -> str:
    """Read a VRCExpressionsMenu asset (one level): controls, types and the parameters they drive."""
    return _json(projects.read_expression_menu(menu_asset_path))


@mcp.tool(annotations=RO)
@_safe
def check_avatar_setup(controller_path: str, parameters_asset_path: str, menu_asset_path: str = "") -> str:
    """Cross-check an avatar's FX controller, Expression Parameters and (optionally) root menu: bit budget, missing/mismatched
    parameters, menu controls driving unknown parameters, Write Defaults consistency, zero-weight layers."""
    return _json(projects.analyze_avatar_assets(controller_path, parameters_asset_path, menu_asset_path or None))


@mcp.tool(annotations=RO)
@_safe
def list_scene_objects(file_path: str, name_contains: str = "", limit: int = 300) -> str:
    """Object paths in a .prefab or .unity file, relative to the avatar root (the VRC Avatar Descriptor object). Use it to get a
    correct object_path / renderer_path for queue_avatar_job. Objects inside imported models or nested prefabs may be missing."""
    return _json(scan.list_scene_objects(file_path, name_contains, limit))


@mcp.tool(annotations=RO)
@_safe
def scan_avatar_tools(file_path: str) -> str:
    """Count VRCFury features (with toggle names) and Modular Avatar components in an avatar .prefab/.unity file. These add layers,
    parameters and menus at build time, so the raw FX controller understates what the avatar does."""
    return _json(scan.scan_avatar_tools(file_path))


@mcp.tool(annotations=RO)
@_safe
def project_bloat_scan(project_path: str, top: int = 15) -> str:
    """Largest textures and models in a project with their import max size and crunch setting, plus optimisation tips."""
    return _json(scan.bloat_scan(project_path, top))


@mcp.tool(annotations=RO)
@_safe
def lint_udon_script(script_path: str) -> str:
    """Quick lint of an UdonSharp .cs file for unsupported C# (async, LINQ, List<>, try/catch, static, lambdas), class/file name
    mismatch, missing 'override', Manual sync without RequestSerialization, private/parameterised network events. Not a compiler."""
    return _json(udonlint.lint(script_path))


@mcp.tool(annotations=RO)
@_safe
def list_job_backups(project_path: str) -> str:
    """Backups made before each avatar job (job name and the assets saved)."""
    return _json(backups.list_backups(project_path))


@mcp.tool()
@_safe
def restore_job_backup(project_path: str, job_name: str) -> str:
    """Undo an avatar job by putting its controller, expression parameters and menu back as they were. Refuses if Unity has the
    project open. Confirm with the user first."""
    return _json(backups.restore_backup(project_path, job_name))


@mcp.tool(annotations=RO)
def list_script_templates() -> str:
    """UdonSharp templates generate_udon_script can write (toggle, teleporter, audio button, trigger zone, spinner, pickup events,
    animator switch, join greeter, synced counter, respawn button, speed zone)."""
    return _json(templates.list_templates())


@mcp.tool()
@_safe
def generate_udon_script(project_path: str, template: str, class_name: str, synced: bool = False, on_trigger: bool = False,
                         animator_parameter: str = "Open", folder: str = "Assets/Scripts/ClaudeVRC") -> str:
    """Write a NEW UdonSharp .cs file into a world project's Assets (never overwrites; class name must equal the file name).
    synced=True (interact_toggle, animator_switch) shares state with everyone incl. late joiners. on_trigger=True (teleporter) fires when
    walking into a trigger. Afterwards tell the user to attach it to an object, fill the public fields, and Build & Test with 2 clients."""
    r = templates.write_script(project_path, template, class_name, folder=folder, synced=synced, on_trigger=on_trigger,
                               parameter=animator_parameter)
    r["next_steps"] = ["Let Unity compile (check the Console for red errors).", f"Add the '{class_name}' component to a GameObject.",
                       "Fill in its public fields; give it a Collider (Is Trigger for zone events).",
                       "Build & Test with Number of Clients = 2 to verify syncing."]
    return _json(r)


@mcp.tool()
@_safe
def queue_avatar_job(project_path: str, job_name: str, controller_path: str, parameters_asset_path: str, menu_asset_path: str,
                     ops: list[dict]) -> str:
    """Prepare avatar edits for Unity to apply (nothing changes until the job is run). Installs the runner script in the project
    and writes the job. Each op: {"op":"toggle","name":"Hat","object_path":"Body/Hat","default_on":false,"menu_path":"Clothes",
    "synced":true,"saved":true} or {"op":"blendshape_slider","name":"Ear Size","parameter":"EarSize","renderer_path":"Body",
    "blendshape":"EarSize","min_value":0,"max_value":100,"default_value":0}, or an Int selector (8 bits, menu value 1..N, 0 = none/default):
    {"op":"outfit_selector","name":"Outfit","options":[{"label":"Hoodie","object_paths":["Body/Hoodie"]},...],"default_option":0} and
    {"op":"material_swap","name":"Eye Color","renderer_path":"Body","material_index":2,"options":[{"label":"Blue","material":"Assets/.../Blue.mat"},...]}
    (options become a sub menu named after the op; max 8). Paths are project-relative (Assets/...) for the three
    assets and avatar-root-relative for objects. The runner adds the parameter, a layer (weight 1, instant transitions, Write Defaults
    matching the controller), clips, the expression parameter and the menu control; it backs up first and rolls back on error.
    Confirm the plan with the user first. Use a COPY of the stock FX controller, never the VRChat default."""
    return _json(jobs.queue_job(project_path, job_name, controller_path, parameters_asset_path, menu_asset_path, ops))


@mcp.tool()
@_safe
def run_unity_jobs(project_path: str, timeout_seconds: int = 900) -> str:
    """Apply queued avatar jobs by launching that project's exact Unity version headless. Refuses if the project is open in Unity
    (then use Tools > Claude VRC > Run Pending Jobs inside Unity). Can take several minutes on first import. Returns the runner's report."""
    return _json(jobs.run_batch(project_path, timeout_seconds))


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
