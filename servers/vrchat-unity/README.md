# vrchat-unity

An MCP server plus skill that helps someone make VRChat avatars and worlds in Unity, whether they have never opened Unity or are
building animator controllers and UdonSharp.

## What it does
| Area | Tools |
|---|---|
| **Teach** (works without any project) | `list_vrchat_guides`, `get_vrchat_guide`, `learning_path` (beginner / intermediate / advanced), `explain_vrchat_error`. 16 guides: install and VCC, Unity basics, avatar setup, upload, performance ranks, expression parameters and menus, FX controllers, Write Defaults, animation, blend trees, drivers, PhysBones and Contacts, tool ecosystem, world basics, UdonSharp, troubleshooting. |
| **Inspect** (read-only) | `find_vrchat_projects` (from VCC), `inspect_vrchat_project`, `analyze_controller`, `read_expression_parameters`, `read_expression_menu`, `check_avatar_setup`, `list_scene_objects` (correct object paths from a prefab/scene), `scan_avatar_tools` (VRCFury features, Modular Avatar components), `project_bloat_scan` (oversized / uncrunched textures). Reads Unity's text YAML directly; Unity does not need to be running. |
| **Write scripts** | `list_script_templates`, `generate_udon_script`: toggle (local or synced), teleporter, audio button, trigger zone, spinner, pickup events, animator switch, join greeter, synced counter, respawn button, speed zone. New files only, never overwritten. `lint_udon_script` flags unsupported C#, sync mistakes and name mismatches before a Unity compile. |
| **Control Unity** | `queue_avatar_job` + `run_unity_jobs`: add **toggles, blendshape sliders, outfit selectors and material swaps** (parameter, FX layer with clips, expression parameter, menu control, sub menus) to an avatar. A C# runner inside the project does the editing, with backups, validation and rollback. `list_job_backups` / `restore_job_backup` undo a job. |

## How avatar control works (and why)
Editing `.controller`/`.asset` files as text is fragile, so the server never does it. Instead `queue_avatar_job` copies
`ClaudeVRCJobRunner.cs` into `Assets/Editor/ClaudeVRC/` and writes a JSON job to `Assets/ClaudeVRC/Jobs/`. The runner applies it
through Unity's own APIs, either from **Tools > Claude VRC > Run Pending Jobs** or headless via `run_unity_jobs` (only when the
project is not open in Unity; it finds the project's exact Unity version). Backups go to `Assets/ClaudeVRC/Backups/<job>/`.

## Limits
- Avatar jobs need the VRChat Avatars SDK in the project. Add and remove of existing items, materials, PhysBones and scene edits are not automated.
- The runner is compile-tested in headless Unity 2022.3 against stub copies of the SDK classes, and the Python side against real
  projects; it has **not** been Build & Tested in VRChat. Test on a project copy first.
- Not a live editor bridge. For live scene control, pair it with a general Unity MCP (e.g. Coplay's MCP for Unity).

Tests: `python -m pytest`.
