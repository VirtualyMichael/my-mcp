# Troubleshooting checklist

(For a specific error message, use the `explain_vrchat_error` tool.)

## Avatar does nothing / toggle broken
1. Layer weight = 1? Parameter names identical (case) in controller, expression parameters and menu?
2. Transition: *Has Exit Time* off? Conditions correct (Bool true/false, Int ==)?
3. Clip path still valid after renames? (red path in Animation window)
4. Write Defaults consistent? (`write-defaults`)
5. Parameter budget exceeded? (>256 bits blocks upload; the SDK validation shows it)
6. Is the right controller assigned in the Avatar Descriptor (FX slot not "Default")?
7. Test with Av3 Emulator / Gesture Manager in Play mode to see parameter values live.

## Avatar looks wrong
- **Pink**: shader missing/unsupported. **Black**: lightmap/normal map or Unity lighting; check in-game lighting.
- **T-pose in game**: bad Humanoid rig or controller issue; check the Rig tab and Base layer.
- **Too tall/short**: View Position and scale.
- **Mouth not moving**: Lip Sync mode and viseme blendshape mapping on the descriptor.
- **Clothes poke through**: hide body parts with a toggled blendshape or AAO's *Remove Mesh By Blendshape*.

## Project/Unity problems
- **Compile errors** (Console, red): a script or package conflict. Read the first error; fix or remove the script; compile errors block build.
- **Missing script (Script)**: a component whose package/script was removed; delete the component.
- **SDK/Unity mismatch or "Package resolution failed"**: use VCC's *Manage Project* to reinstall the SDK; close Unity first.
- **VCC "project is not VRChat-compatible"**: update/migrate from VCC; do not open it directly in Unity until VCC says OK.
- **Unity is frozen on import**: check `%LOCALAPPDATA%\Unity\Editor\Editor.log`; usually a large asset or a shader compiling. Wait a few minutes.

## Worlds
- **Script does nothing**: not assigned a Collider (for Interact), wrong class/file name, compile errors (red) elsewhere, or UdonBehaviour has no program.
- **Sync works for you only**: missing `Networking.SetOwner` / `RequestSerialization()`, wrong SyncMode, or testing with a single client.
- **Lights look wrong**: bake lightmaps; add light probes.
