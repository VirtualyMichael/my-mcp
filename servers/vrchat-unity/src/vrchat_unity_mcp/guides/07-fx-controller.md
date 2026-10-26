# The FX controller (Animator Controller, Avatars 3.0)

## Playable layers
An avatar has up to five animator controllers on the Avatar Descriptor (*Playable Layers*): **Base** (locomotion), **Additive** (breathing/idle additive motion), **Gesture** (hand/upper-body overlay, uses masks), **Action** (emotes and full-body overrides, triggered by animator drivers), and **FX** (everything else: toggles, blendshapes, materials, particles; it can animate anything *except humanoid bones*). For toggles and visual features, you almost always edit **FX**. If the FX slot is "Default", it uses a VRChat stock controller; duplicate your own (*Create > Animator Controller*) and assign it (uncheck *Default*).

## Anatomy
- **Parameters** (Animator window > Parameters tab): the variables (Float/Int/Bool/Trigger). Names must **exactly** match the Expression Parameters you want to drive them from.
- **Layers**: independent state machines that all run simultaneously. Convention: one layer per feature (e.g. "Hat", "Eye Color"). Layer **weight must be 1** or the layer does nothing (new layers default to weight 0 in the UI: click the gear and set Weight).
- **States**: each plays a Motion (an animation clip or blend tree). Orange state = the default (entry) state.
- **Transitions**: arrows between states with **Conditions** (e.g. `Hat == true`).

## Simple toggle layer (the standard pattern)
- Layer "Hat". Two states: **Hat Off** (clip sets `Hat` GameObject `Is Active` = 0) and **Hat On** (clip sets it to 1).
- Transitions: Off > On when `Hat` is true; On > Off when `Hat` is false.
- For each transition: uncheck **Has Exit Time**, set **Transition Duration** to 0 (instant).
- Parameter `Hat` is a **Bool** also in the Expression Parameters (synced if others should see it), and a Toggle in the Expression Menu points at it.

## Debugging approach
1. Is the layer weight 1?
2. Does the animator parameter name match the expression parameter name exactly?
3. Are the paths inside the animation clip still valid? (If you renamed/moved a child object, the clip's path turns red/"Missing" and nothing happens.)
4. Test with *Build & Test*, or an emulator (Av3Emulator / Gesture Manager) in Play mode, which lets you drive parameters live.

## Layers vs. size
Each layer costs a little; dozens of layers are normal, hundreds will hurt. Prefer blend trees for continuous things (see `advanced-animation`).

See also `write-defaults` (important!) and `avatar-toggles`.
