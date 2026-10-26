import json
import textwrap

import pytest

from vrchat_unity_mcp import guides, jobs, projects, templates


def make_project(tmp_path, avatars=True):
    (tmp_path / "Assets").mkdir()
    (tmp_path / "ProjectSettings").mkdir()
    (tmp_path / "ProjectSettings" / "ProjectVersion.txt").write_text("m_EditorVersion: 2022.3.22f1\n")
    (tmp_path / "Packages").mkdir()
    deps = {"com.vrchat.avatars": {"version": "3.10.1"}} if avatars else {"com.vrchat.worlds": {"version": "3.10.1"}}
    (tmp_path / "Packages" / "vpm-manifest.json").write_text(json.dumps({"dependencies": deps}))
    return tmp_path


CONTROLLER = textwrap.dedent("""\
    %YAML 1.1
    %TAG !u! tag:unity3d.com,2011:
    --- !u!91 &9100000
    AnimatorController:
      m_Name: FX
      m_AnimatorParameters:
      - m_Name: Hat
        m_Type: 4
        m_DefaultBool: 0
      m_AnimatorLayers:
      - serializedVersion: 5
        m_Name: Base
        m_StateMachine: {fileID: 1100}
        m_DefaultWeight: 1
      - serializedVersion: 5
        m_Name: Hat
        m_StateMachine: {fileID: 1200}
        m_DefaultWeight: 0
    --- !u!1102 &1101
    AnimatorState:
      m_Name: Idle
      m_WriteDefaultValues: 1
      m_Transitions: []
      m_Behaviours: []
      m_Motion: {fileID: 0}
    --- !u!1107 &1100
    AnimatorStateMachine:
      m_Name: Base
      m_ChildStates:
      - serializedVersion: 1
        m_State: {fileID: 1101}
      m_AnyStateTransitions: []
    --- !u!1102 &1201
    AnimatorState:
      m_Name: On
      m_WriteDefaultValues: 0
      m_Transitions:
      - {fileID: 1300}
      m_Behaviours: []
      m_Motion: {fileID: 0}
    --- !u!1101 &1300
    AnimatorStateTransition:
      m_Conditions:
      - m_ConditionMode: 1
        m_ConditionEvent: Ghost
        m_EventTreshold: 0
      m_DstState: {fileID: 1101}
      m_HasExitTime: 0
      m_TransitionDuration: 0
    --- !u!1107 &1200
    AnimatorStateMachine:
      m_Name: Hat
      m_ChildStates:
      - serializedVersion: 1
        m_State: {fileID: 1201}
      m_AnyStateTransitions: []
    """)


def test_controller_issues(tmp_path):
    root = make_project(tmp_path)
    f = root / "Assets" / "FX.controller"
    f.write_text(CONTROLLER)
    r = projects.analyze_controller(str(f))
    assert r["layer_count"] == 2 and r["write_defaults"] == "mixed"
    text = " ".join(r["issues"])
    assert "weight 0" in text and "Ghost" in text and "Mixed Write Defaults" in text


def test_binary_asset_rejected(tmp_path):
    f = tmp_path / "x.controller"
    f.write_bytes(b"\x00\x01binary")
    with pytest.raises(ValueError, match="text-serialised"):
        projects.analyze_controller(str(f))


def test_expression_parameters_budget(tmp_path):
    body = "\n".join(f"  - name: P{i}\n    valueType: 1\n    saved: 1\n    defaultValue: 0\n    networkSynced: 1" for i in range(33))
    f = tmp_path / "p.asset"
    f.write_text("%YAML 1.1\n--- !u!114 &11400000\nMonoBehaviour:\n  m_Name: P\n  parameters:\n" + body + "\n")
    r = projects.read_expression_parameters(str(f))
    assert r["synced_bits_used"] == 264 and r["over_budget"]


def test_project_kind_and_detection(tmp_path):
    root = make_project(tmp_path)
    assert projects.project_kind(root) == "avatar"
    assert projects.unity_version(root) == "2022.3.22f1"
    assert projects.is_open(root) is False


def test_every_template_renders():
    for name in templates.TEMPLATES:
        for synced in (False, True):
            code = templates.render(name, "Thing", synced=synced, on_trigger=synced, parameter="Open")
            assert "class Thing : UdonSharpBehaviour" in code
            assert code.count("{") == code.count("}")


def test_script_writer_safety(tmp_path):
    root = make_project(tmp_path, avatars=False)
    r = templates.write_script(str(root), "spinner", "Spin")
    assert (root / "Assets/Scripts/ClaudeVRC/Spin.cs").is_file() and r["project_relative"].endswith("Spin.cs")
    with pytest.raises(ValueError, match="already exists"):
        templates.write_script(str(root), "spinner", "Spin")
    with pytest.raises(ValueError, match="valid C# class name"):
        templates.write_script(str(root), "spinner", "bad name")
    with pytest.raises(ValueError, match="valid C# class name"):
        templates.write_script(str(root), "spinner", "class")
    with pytest.raises(ValueError, match="inside the project's Assets"):
        templates.write_script(str(root), "spinner", "Esc", folder="../outside")


def test_job_queue_validation(tmp_path):
    root = make_project(tmp_path)
    for n, s in (("FX.controller", "x"), ("P.asset", "x"), ("M.asset", "x")):
        (root / "Assets" / n).write_text(s)
    args = dict(project=str(root), job_name="j1", controller="Assets/FX.controller", parameters="Assets/P.asset", menu="Assets/M.asset")
    with pytest.raises(ValueError, match="object_path"):
        jobs.queue_job(ops=[{"op": "toggle", "name": "Hat"}], **args)
    with pytest.raises(ValueError, match="op must be"):
        jobs.queue_job(ops=[{"op": "delete_everything", "name": "x"}], **args)
    with pytest.raises(ValueError, match="starting with Assets/"):
        jobs.queue_job(**{**args, "controller": "../FX.controller"}, ops=[{"op": "toggle", "name": "Hat", "object_path": "Body/Hat"}])
    r = jobs.queue_job(ops=[{"op": "toggle", "name": "Top Hat", "object_path": "Body/Hat"}], **args)
    job = json.loads((root / r["queued"]).read_text())
    assert job["ops"][0]["parameter"] == "TopHat"
    assert (root / jobs.RUNNER_REL).is_file()
    with pytest.raises(ValueError, match="already exists"):
        jobs.queue_job(ops=[{"op": "toggle", "name": "Hat", "object_path": "Body/Hat"}], **args)


def test_runner_refuses_world_project(tmp_path):
    root = make_project(tmp_path, avatars=False)
    with pytest.raises(ValueError, match="Avatars SDK"):
        jobs.install_runner(str(root))


def test_guides_and_errors():
    assert len(guides.topics()) >= 15
    assert "Write Defaults" in guides.get("write defaults")
    assert "udonsharp" in guides.get("udon").lower()
    with pytest.raises(ValueError):
        guides.get("zzzz-nothing")
    assert guides.explain("Parameters over 256 bits")["matched"]
    assert guides.path("advanced")[0] == "getting-started"
