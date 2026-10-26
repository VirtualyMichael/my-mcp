import json
import textwrap

import pytest

from test_vrchat_unity import make_project
from vrchat_unity_mcp import backups, jobs, scan, templates, udonlint


def test_every_template_passes_own_lint(tmp_path):
    for name in templates.TEMPLATES:
        for synced in (False, True):
            cls = f"T{name.title().replace('_', '')}{int(synced)}"
            f = tmp_path / f"{cls}.cs"
            f.write_text(templates.render(name, cls, synced=synced, on_trigger=synced), encoding="utf-8")
            r = udonlint.lint(str(f))
            assert r["errors"] == 0, (name, synced, r["findings"])


def test_lint_catches_common_mistakes(tmp_path):
    f = tmp_path / "Wrong.cs"
    f.write_text(textwrap.dedent("""\
        using System.Collections.Generic;
        using System.Linq;
        public class Other : MonoBehaviour
        {
            static int counter = 0;
            [UdonSynced] public int score;
            List<int> items;
            async void Go() { }
            void Interact() { }
            private void Ping() { }
            void Fire() { SendCustomNetworkEvent(VRC.Udon.Common.Interfaces.NetworkEventTarget.All, nameof(Ping)); }
        }
        """))
    msgs = " | ".join(x["message"] for x in udonlint.lint(str(f))["findings"])
    for expected in ("must equal the file name", "derives from", "Missing 'using UdonSharp;'", "LINQ", "Static fields", "async/await",
                     "System.Collections.Generic", "must be declared 'public override void Interact", "must be public"):
        assert expected in msgs, expected


def test_lint_manual_sync_needs_serialization(tmp_path):
    f = tmp_path / "S.cs"
    f.write_text("using UdonSharp;\n[UdonBehaviourSyncMode(BehaviourSyncMode.Manual)]\npublic class S : UdonSharpBehaviour\n"
                 "{ [UdonSynced] bool b; public override void Interact() { b = !b; } }\n")
    assert any("RequestSerialization" in x["message"] for x in udonlint.lint(str(f))["findings"])


def _queue(root, ops):
    for n in ("FX.controller", "P.asset", "M.asset"):
        (root / "Assets" / n).write_text("x")
    return jobs.queue_job(str(root), "j", "Assets/FX.controller", "Assets/P.asset", "Assets/M.asset", ops)


def test_selector_job_validation(tmp_path):
    root = make_project(tmp_path)
    with pytest.raises(ValueError, match="1-8 options"):
        _queue(root, [{"op": "outfit_selector", "name": "Outfit", "options": []}])
    with pytest.raises(ValueError, match="object_paths"):
        _queue(root, [{"op": "outfit_selector", "name": "Outfit", "options": [{"label": "A"}]}])
    with pytest.raises(ValueError, match="default_option"):
        _queue(root, [{"op": "outfit_selector", "name": "Outfit", "default_option": 5,
                       "options": [{"label": "A", "object_paths": ["Body/A"]}]}])
    with pytest.raises(ValueError, match="does not exist"):
        _queue(root, [{"op": "material_swap", "name": "Eyes", "renderer_path": "Body",
                       "options": [{"label": "Blue", "material": "Assets/Missing.mat"}]}])
    (root / "Assets" / "Blue.mat").write_text("x")
    r = _queue(root, [{"op": "outfit_selector", "name": "Outfit", "options": [{"label": "A", "object_paths": ["Body/A", "Body/B"]}]},
                      {"op": "material_swap", "name": "Eyes", "renderer_path": "Body", "material_index": 2,
                       "options": [{"label": "Blue", "material": "Assets/Blue.mat"}]}])
    job = json.loads((root / r["queued"]).read_text())
    assert job["ops"][0]["options"][0]["object_paths"] == ["Body/A", "Body/B"] and job["ops"][1]["material_index"] == 2


def test_backup_restore(tmp_path):
    root = make_project(tmp_path)
    ctrl = root / "Assets" / "FX.controller"
    ctrl.write_text("original")
    bdir = root / "Assets" / "ClaudeVRC" / "Backups" / "j1"
    bdir.mkdir(parents=True)
    (bdir / "FX.controller").write_text("original")
    (bdir / "manifest.json").write_text(json.dumps({"files": [{"original": "Assets/FX.controller", "backup": "Assets/ClaudeVRC/Backups/j1/FX.controller"}]}))
    ctrl.write_text("changed")
    assert backups.list_backups(str(root))[0]["job"] == "j1"
    backups.restore_backup(str(root), "j1")
    assert ctrl.read_text() == "original"
    with pytest.raises(ValueError, match="No backup manifest"):
        backups.restore_backup(str(root), "nope")
    (bdir / "manifest.json").write_text(json.dumps({"files": [{"original": "../escape.txt", "backup": "Assets/ClaudeVRC/Backups/j1/FX.controller"}]}))
    with pytest.raises(ValueError, match="looks wrong"):
        backups.restore_backup(str(root), "j1")


PREFAB = textwrap.dedent("""\
    %YAML 1.1
    %TAG !u! tag:unity3d.com,2011:
    --- !u!1 &1
    GameObject:
      m_Name: Avatar
    --- !u!4 &2
    Transform:
      m_GameObject: {fileID: 1}
      m_Father: {fileID: 0}
    --- !u!1 &3
    GameObject:
      m_Name: Body
    --- !u!4 &4
    Transform:
      m_GameObject: {fileID: 3}
      m_Father: {fileID: 2}
    --- !u!1 &5
    GameObject:
      m_Name: Hat
    --- !u!4 &6
    Transform:
      m_GameObject: {fileID: 5}
      m_Father: {fileID: 4}
    --- !u!114 &7
    MonoBehaviour:
      m_GameObject: {fileID: 1}
      baseAnimationLayers: []
      content:
        type: {class: Toggle, ns: VF.Model.Feature, asm: x}
        name: Hat Toggle
    """)


def test_scene_objects_and_tool_scan(tmp_path):
    f = tmp_path / "Avatar.prefab"
    f.write_text(PREFAB)
    r = scan.list_scene_objects(str(f))
    assert r["avatar_root"] == "Avatar" and r["paths"] == ["Body", "Body/Hat"]
    assert scan.list_scene_objects(str(f), "hat")["paths"] == ["Body/Hat"]
    t = scan.scan_avatar_tools(str(f))
    assert t["vrcfury_features"] == {"Toggle": 1}


def test_bloat_scan(tmp_path):
    root = make_project(tmp_path)
    (root / "Assets" / "big.png").write_bytes(b"0" * 3_000_000)
    (root / "Assets" / "big.png.meta").write_text(
        "textureImporter:\n  platformSettings:\n  - serializedVersion: 3\n    buildTarget: DefaultTexturePlatform\n"
        "    maxTextureSize: 4096\n    resizeAlgorithm: 0\n    crunchedCompression: 0\n")
    r = scan.bloat_scan(str(root))
    assert r["largest_textures"][0]["max_size"] == 4096 and r["largest_textures"][0]["crunched"] is False
    assert any("4096" in t for t in r["tips"])
