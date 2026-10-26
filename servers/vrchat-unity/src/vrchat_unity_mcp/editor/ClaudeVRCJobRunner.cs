// Installed by the vrchat-unity MCP server. Applies JSON "jobs" to a VRChat avatar's FX controller,
// Expression Parameters and Expression Menu. Safe by design:
//  - every asset it touches is backed up first (Assets/ClaudeVRC/Backups/<job>/)
//  - jobs are validated before anything changes; if anything fails mid-way the backups are restored
//  - it never overwrites an existing parameter, layer or menu control, and never deletes anything
// Run it from  Tools > Claude VRC > Run Pending Jobs  (or headless via -executeMethod ClaudeVRC.JobRunner.RunBatch).
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;
using VRC.SDK3.Avatars.ScriptableObjects;

namespace ClaudeVRC
{
    [Serializable]
    public class JobOp
    {
        public string op;               // "toggle" | "blendshape_slider"
        public string name;             // menu label
        public string parameter;        // animator/expression parameter name
        public string object_path;      // toggle: path of the GameObject relative to the avatar root, e.g. "Body/Hat"
        public string renderer_path;    // slider: path of the SkinnedMeshRenderer relative to the avatar root
        public string blendshape;       // slider: blendshape name
        public float min_value = 0f;    // slider: blendshape value at parameter 0
        public float max_value = 100f;  // slider: blendshape value at parameter 1
        public float default_value = 0f;// slider: parameter default (0..1)
        public bool default_on = false; // toggle: starts on
        public bool saved = true;
        public bool synced = true;
        public string menu_path = "";   // "" = root menu, "Clothes/Hats" = nested sub menus (created when missing)
        public string write_defaults = "auto"; // "auto" | "on" | "off"
    }

    [Serializable]
    public class JobFile
    {
        public string controller;
        public string parameters;
        public string menu;
        public JobOp[] ops;
    }

    public static class JobRunner
    {
        public const string Root = "Assets/ClaudeVRC";
        public const string JobsDir = Root + "/Jobs";
        const string GenDir = Root + "/Generated";
        const string BackupDir = Root + "/Backups";
        const int MaxSyncedBits = 256;
        const int MaxMenuControls = 8;
        static readonly Regex Ident = new Regex("^[A-Za-z0-9_/-]+$");

        [MenuItem("Tools/Claude VRC/Run Pending Jobs")]
        public static void RunFromMenu()
        {
            var report = RunAll();
            EditorUtility.DisplayDialog("Claude VRC", report.Length == 0 ? "No pending jobs in " + JobsDir : report, "OK");
        }

        public static void RunBatch()
        {
            string report = RunAll();
            Debug.Log("[ClaudeVRC] " + report);
            EditorApplication.Exit(report.Contains("FAILED") ? 1 : 0);
        }

        public static string RunAll()
        {
            var sb = new StringBuilder();
            if (!Directory.Exists(JobsDir)) return "";
            AssetDatabase.Refresh();   // make sure Unity has imported every asset the jobs refer to
            foreach (string file in Directory.GetFiles(JobsDir, "*.json").OrderBy(f => f))
            {
                string job = Path.GetFileNameWithoutExtension(file);
                string result;
                try { result = RunJob(job, File.ReadAllText(file)); }
                catch (Exception e) { result = "FAILED: " + e.Message; }
                sb.AppendLine(job + ": " + result);
                Directory.CreateDirectory(JobsDir + "/Done");
                string done = JobsDir + "/Done/" + job;
                if (File.Exists(done + ".json")) File.Delete(done + ".json");
                File.Move(file, done + ".json");
                File.WriteAllText(done + ".result.txt", result);
            }
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            return sb.ToString();
        }

        // ------------------------------------------------------------------ one job

        static string RunJob(string jobName, string json)
        {
            var job = JsonUtility.FromJson<JobFile>(json);
            if (job == null || job.ops == null || job.ops.Length == 0) throw new Exception("job has no ops");
            var controller = AssetDatabase.LoadAssetAtPath<AnimatorController>(job.controller);
            var pars = AssetDatabase.LoadAssetAtPath<VRCExpressionParameters>(job.parameters);
            var menu = AssetDatabase.LoadAssetAtPath<VRCExpressionsMenu>(job.menu);
            if (controller == null) throw new Exception("controller not found: " + job.controller);
            if (pars == null) throw new Exception("expression parameters not found: " + job.parameters);
            if (menu == null) throw new Exception("expression menu not found: " + job.menu);

            Validate(job, controller, pars);

            var backups = Backup(jobName, new[] { job.controller, job.parameters, job.menu });
            try
            {
                var log = new List<string>();
                foreach (var op in job.ops)
                {
                    string pname = ParamName(op);
                    switch (op.op)
                    {
                        case "toggle": ApplyToggle(op, pname, controller, pars, menu); break;
                        case "blendshape_slider": ApplySlider(op, pname, controller, pars, menu); break;
                    }
                    log.Add(op.op + " '" + op.name + "' (parameter " + pname + ")");
                }
                EditorUtility.SetDirty(controller);
                EditorUtility.SetDirty(pars);
                EditorUtility.SetDirty(menu);
                AssetDatabase.SaveAssets();
                return "OK: " + string.Join("; ", log) + ". Synced bits now " + SyncedBits(pars) + "/" + MaxSyncedBits + ". Backups in " + BackupDir + "/" + jobName;
            }
            catch (Exception)
            {
                Restore(backups);
                throw;
            }
        }

        static string ParamName(JobOp op) => string.IsNullOrEmpty(op.parameter) ? op.name : op.parameter;

        static void Validate(JobFile job, AnimatorController controller, VRCExpressionParameters pars)
        {
            var seen = new HashSet<string>();
            int addBits = 0;
            foreach (var op in job.ops)
            {
                if (op.op != "toggle" && op.op != "blendshape_slider") throw new Exception("unknown op '" + op.op + "'");
                if (string.IsNullOrEmpty(op.name)) throw new Exception("every op needs a name");
                string p = ParamName(op);
                if (!Ident.IsMatch(p)) throw new Exception("parameter name '" + p + "' may only contain letters, digits, '_', '/' and '-'");
                if (!seen.Add(p)) throw new Exception("parameter '" + p + "' appears twice in this job");
                if (controller.parameters.Any(x => x.name == p)) throw new Exception("controller already has a parameter named '" + p + "'");
                if (pars.parameters != null && pars.parameters.Any(x => x != null && x.name == p)) throw new Exception("expression parameters already contain '" + p + "'");
                if (controller.layers.Any(l => l.name == op.name)) throw new Exception("controller already has a layer named '" + op.name + "'");
                if (op.op == "toggle" && string.IsNullOrEmpty(op.object_path)) throw new Exception("toggle '" + op.name + "' needs object_path");
                if (op.op == "blendshape_slider" && (string.IsNullOrEmpty(op.renderer_path) || string.IsNullOrEmpty(op.blendshape)))
                    throw new Exception("slider '" + op.name + "' needs renderer_path and blendshape");
                if (op.synced) addBits += op.op == "toggle" ? 1 : 8;
            }
            if (SyncedBits(pars) + addBits > MaxSyncedBits)
                throw new Exception("would use " + (SyncedBits(pars) + addBits) + " synced bits; the limit is " + MaxSyncedBits + ". Make some parameters unsynced or remove unused ones.");
        }

        static int SyncedBits(VRCExpressionParameters pars)
        {
            if (pars.parameters == null) return 0;
            return pars.parameters.Where(p => p != null && p.networkSynced).Sum(p => p.valueType == VRCExpressionParameters.ValueType.Bool ? 1 : 8);
        }

        // ------------------------------------------------------------------ operations

        static void ApplyToggle(JobOp op, string pname, AnimatorController controller, VRCExpressionParameters pars, VRCExpressionsMenu rootMenu)
        {
            bool wd = WriteDefaults(op, controller);
            var binding = EditorCurveBinding.FloatCurve(op.object_path, typeof(GameObject), "m_IsActive");
            var off = MakeClip(pname + "_Off", binding, 0f, 0f);
            var on = MakeClip(pname + "_On", binding, 1f, 1f);

            controller.AddParameter(new AnimatorControllerParameter { name = pname, type = AnimatorControllerParameterType.Bool, defaultBool = op.default_on });
            var sm = AddLayer(controller, op.name);
            var sOff = sm.AddState(op.name + " Off", new Vector3(300, 0, 0));
            var sOn = sm.AddState(op.name + " On", new Vector3(300, 80, 0));
            sOff.motion = off; sOff.writeDefaultValues = wd;
            sOn.motion = on; sOn.writeDefaultValues = wd;
            sm.defaultState = op.default_on ? sOn : sOff;
            Instant(sOff.AddTransition(sOn)).AddCondition(AnimatorConditionMode.If, 0, pname);
            Instant(sOn.AddTransition(sOff)).AddCondition(AnimatorConditionMode.IfNot, 0, pname);

            AddExpressionParameter(pars, pname, VRCExpressionParameters.ValueType.Bool, op.default_on ? 1f : 0f, op);
            var control = new VRCExpressionsMenu.Control
            {
                name = op.name,
                type = VRCExpressionsMenu.Control.ControlType.Toggle,
                parameter = new VRCExpressionsMenu.Control.Parameter { name = pname },
                value = 1f
            };
            AddMenuControl(rootMenu, op.menu_path, control);
        }

        static void ApplySlider(JobOp op, string pname, AnimatorController controller, VRCExpressionParameters pars, VRCExpressionsMenu rootMenu)
        {
            bool wd = WriteDefaults(op, controller);
            var binding = EditorCurveBinding.FloatCurve(op.renderer_path, typeof(SkinnedMeshRenderer), "blendShape." + op.blendshape);
            var clip = new AnimationClip { name = pname + "_Slider" };
            AnimationUtility.SetEditorCurve(clip, binding, new AnimationCurve(new Keyframe(0f, op.min_value), new Keyframe(1f, op.max_value)));
            SaveAsset(clip, "Animations", clip.name + ".anim");

            controller.AddParameter(new AnimatorControllerParameter { name = pname, type = AnimatorControllerParameterType.Float, defaultFloat = op.default_value });
            var sm = AddLayer(controller, op.name);
            var s = sm.AddState(op.name, new Vector3(300, 0, 0));
            s.motion = clip; s.writeDefaultValues = wd;
            s.timeParameterActive = true; s.timeParameter = pname;
            sm.defaultState = s;

            AddExpressionParameter(pars, pname, VRCExpressionParameters.ValueType.Float, op.default_value, op);
            var control = new VRCExpressionsMenu.Control
            {
                name = op.name,
                type = VRCExpressionsMenu.Control.ControlType.RadialPuppet,
                parameter = new VRCExpressionsMenu.Control.Parameter { name = "" },
                subParameters = new[] { new VRCExpressionsMenu.Control.Parameter { name = pname } }
            };
            AddMenuControl(rootMenu, op.menu_path, control);
        }

        // ------------------------------------------------------------------ helpers

        static AnimatorStateMachine AddLayer(AnimatorController controller, string name)
        {
            controller.AddLayer(name);
            var layers = controller.layers;
            var layer = layers[layers.Length - 1];
            layer.defaultWeight = 1f;   // new layers default to 0, which silently disables them
            layers[layers.Length - 1] = layer;
            controller.layers = layers;
            return layer.stateMachine;
        }

        static AnimatorStateTransition Instant(AnimatorStateTransition t)
        {
            t.hasExitTime = false;
            t.exitTime = 0f;
            t.hasFixedDuration = true;
            t.duration = 0f;
            t.canTransitionToSelf = false;
            return t;
        }

        static bool WriteDefaults(JobOp op, AnimatorController controller)
        {
            if (op.write_defaults == "on") return true;
            if (op.write_defaults == "off") return false;
            int on = 0, off = 0;
            foreach (var l in controller.layers) Count(l.stateMachine, ref on, ref off);
            return on > off;   // match the controller's existing majority; an empty controller defaults to Write Defaults OFF
        }

        static void Count(AnimatorStateMachine sm, ref int on, ref int off)
        {
            if (sm == null) return;
            foreach (var cs in sm.states) { if (cs.state.writeDefaultValues) on++; else off++; }
            foreach (var sub in sm.stateMachines) Count(sub.stateMachine, ref on, ref off);
        }

        static AnimationClip MakeClip(string name, EditorCurveBinding binding, float value, float _)
        {
            var clip = new AnimationClip { name = name };
            AnimationUtility.SetEditorCurve(clip, binding, AnimationCurve.Constant(0f, 1f / 60f, value));
            SaveAsset(clip, "Animations", name + ".anim");
            return clip;
        }

        static void SaveAsset(UnityEngine.Object asset, string sub, string fileName)
        {
            string dir = GenDir + "/" + sub;
            EnsureFolder(dir);
            AssetDatabase.CreateAsset(asset, AssetDatabase.GenerateUniqueAssetPath(dir + "/" + fileName));
        }

        static void EnsureFolder(string path)
        {
            if (AssetDatabase.IsValidFolder(path)) return;
            string parent = Path.GetDirectoryName(path).Replace('\\', '/');
            EnsureFolder(parent);
            AssetDatabase.CreateFolder(parent, Path.GetFileName(path));
        }

        static void AddExpressionParameter(VRCExpressionParameters pars, string name, VRCExpressionParameters.ValueType type, float def, JobOp op)
        {
            var list = (pars.parameters ?? new VRCExpressionParameters.Parameter[0]).Where(p => p != null).ToList();
            list.Add(new VRCExpressionParameters.Parameter { name = name, valueType = type, defaultValue = def, saved = op.saved, networkSynced = op.synced });
            pars.parameters = list.ToArray();
        }

        static void AddMenuControl(VRCExpressionsMenu root, string path, VRCExpressionsMenu.Control control)
        {
            var current = root;
            foreach (string segment in (path ?? "").Split(new[] { '/' }, StringSplitOptions.RemoveEmptyEntries))
            {
                if (current.controls == null) current.controls = new List<VRCExpressionsMenu.Control>();
                var existing = current.controls.FirstOrDefault(c => c.type == VRCExpressionsMenu.Control.ControlType.SubMenu && c.name == segment && c.subMenu != null);
                if (existing == null)
                {
                    if (current.controls.Count >= MaxMenuControls) throw new Exception("menu is full (8 controls) before reaching '" + segment + "'. Use a different menu_path.");
                    var sub = ScriptableObject.CreateInstance<VRCExpressionsMenu>();
                    sub.name = segment + "Menu";
                    sub.controls = new List<VRCExpressionsMenu.Control>();
                    SaveAsset(sub, "Menus", sub.name + ".asset");
                    existing = new VRCExpressionsMenu.Control
                    {
                        name = segment,
                        type = VRCExpressionsMenu.Control.ControlType.SubMenu,
                        subMenu = sub,
                        parameter = new VRCExpressionsMenu.Control.Parameter { name = "" }
                    };
                    current.controls.Add(existing);
                    EditorUtility.SetDirty(current);
                }
                current = existing.subMenu;
            }
            if (current.controls == null) current.controls = new List<VRCExpressionsMenu.Control>();
            if (current.controls.Count >= MaxMenuControls) throw new Exception("menu is full (8 controls). Use a different menu_path, e.g. \"More\".");
            current.controls.Add(control);
            EditorUtility.SetDirty(current);
        }

        // ------------------------------------------------------------------ backup / restore

        static Dictionary<string, string> Backup(string job, IEnumerable<string> assetPaths)
        {
            string dir = BackupDir + "/" + job;
            EnsureFolder(dir);
            var map = new Dictionary<string, string>();
            foreach (string p in assetPaths.Distinct())
            {
                string dest = AssetDatabase.GenerateUniqueAssetPath(dir + "/" + Path.GetFileName(p));
                if (!AssetDatabase.CopyAsset(p, dest)) throw new Exception("could not back up " + p);
                map[p] = dest;
            }
            return map;
        }

        static void Restore(Dictionary<string, string> backups)
        {
            foreach (var kv in backups)
            {
                File.Copy(kv.Value, kv.Key, true);
                AssetDatabase.ImportAsset(kv.Key, ImportAssetOptions.ForceUpdate);
            }
        }
    }
}
