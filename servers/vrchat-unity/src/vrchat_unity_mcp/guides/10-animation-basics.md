# Animation basics in Unity

## Animation clip vs. Animator
- An **Animation Clip** (`.anim`) stores property values over time (a position, a blendshape, a GameObject's active flag).
- An **Animator Controller** (`.controller`) is a graph of states, each playing a clip, plus transitions between them.
- The **Animator** component on the avatar root runs a controller. VRChat sets this up for you from the Avatar Descriptor's Playable Layers, so you rarely edit the Animator component directly.

## Making a clip
1. Select the avatar root (so paths are relative to it).
2. *Window > Animation > Animation*. Click **Create**, save it (e.g. `Assets/Animations/Hat_On.anim`).
3. **Add Property**, pick the object and a property. Common ones:
   - `Game Object > Is Active` - show/hide.
   - `Skinned Mesh Renderer > Blendshape.<name>` - face/body shapes (range 0-100).
   - `Mesh Renderer / SMR > Material._Color` or shader properties like `_EmissionStrength` - recolor/glow (a property must exist on the material's shader).
   - `Material Slot` swaps (`Materials[2]`) - change outfit material.
   - `Transform` position/rotation/scale - move or scale parts (humanoid bones cannot be animated in FX).
4. Add keyframes: with **Record** (red dot) on, change values in the Inspector, or type directly into the curve.
5. For a toggle you need only one frame (a clip with one keyframe at time 0 holds that value).

## Loops and speed
- Select the clip in the Project window > *Loop Time* checkbox for repeating motion.
- State **Speed** and *Motion Time* in the Animator allow scrubbing by a parameter (radial sliders).

## Curve tips
- Right-click keyframes to set tangents: *Constant* for on/off, *Linear* for straight ramps.
- Clips store **paths** (e.g. `Armature/Hips/Hat`). Renaming/moving objects breaks them; red in the Animation window = missing path.

## Working with VRChat's expectations
- Everything about **toggles** you put in the FX layer; humanoid motion goes in Action/Gesture layers (`advanced-animation`).
- Test in Play mode with an emulator (Av3Emulator or Gesture Manager) before uploading.
