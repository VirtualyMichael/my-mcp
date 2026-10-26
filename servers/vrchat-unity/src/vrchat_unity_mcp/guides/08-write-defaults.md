# Write Defaults (the #1 source of mysterious animator bugs)

Every **Animator State** has a *Write Defaults* checkbox.

- **WD ON**: when the state does not animate a property that other states in the controller animate, Unity writes that property back to its *default value* (the value it had in the scene). Convenient, but can unexpectedly reset things, and a state with no clip can hold the avatar "frozen" or revert toggles.
- **WD OFF**: the state writes **only** what its clip animates. A property keeps its last animated value after you leave a state. This is explicit and predictable, but you must make sure every state in a toggle pair animates the property (an ON state and an OFF state, each with a keyframe).

## The rule
**Be consistent: do not mix WD ON and WD OFF in the same controller** (the default VRChat stock controllers use WD ON for some layers, so mixing is easy to do by accident). Mixed settings are the classic cause of "my toggle works but my face blendshapes reset" and "the avatar goes into a T-pose/ resets when I use an emote".
- Many creators pick **WD OFF** for new work (cleaner), animating both on and off values.
- Some prefabs/tools (older Modular Avatar/VRCFury setups, many marketplace outfits) assume **WD ON**; both tools can auto-match or warn.
- Gesture/ Action layers in VRChat's reference controllers have their own rules; follow whatever the existing layer uses, and when adding new layers, **match the controller's existing majority**.

## Quick checklist
1. Open the Animator, select every state (Ctrl+A in the layer), look at Write Defaults in the Inspector.
2. If mixed, pick one and set all to match, then re-test every toggle.
3. With WD OFF, any toggle needs *both* On and Off clips (this server's `queue_avatar_job` generates both).
4. Layers with a "default" or empty state: an empty state with WD OFF does nothing (fine); with WD ON it forces defaults (can undo other layers).
