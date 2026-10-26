# Avatar basics: from model to a working avatar

## Pipeline in one view
Model (.fbx, from Blender/VRoid/Booth/etc.) > import into Unity > check the **Rig** is *Humanoid* > put it in a scene > add **VRC Avatar Descriptor** > set **View Position** (eye height) > set up **eyes / visemes (mouth)** > fix materials/shaders > check **Performance** > **Build & Test** > **Build & Publish**.

## Step by step
1. **Import**: drag the .fbx (and its textures folder) into `Assets/`. Select the .fbx > *Rig* tab > Animation Type **Humanoid** > Apply. If the bone mapping has a red/"missing" slot, open *Configure* and fix it, or the avatar will not animate properly.
2. **Scene**: drag the model into the Hierarchy. Reset its position to 0,0,0, rotation 0, scale 1 (for a unit-correct model). Facing the +Z direction (blue arrow) is "forward".
3. **Avatar Descriptor**: Add Component > *VRC Avatar Descriptor*. This turns on the avatar's VRChat features.
   - **View Position**: the point between the eyes. Use the *Edit* button or move the yellow ball in the Scene view; getting it wrong makes the avatar feel too tall/short in first person.
   - **Lip Sync**: Mode *Viseme Blend Shape* if the face has the 15 viseme blendshapes (`vrc.v_sil`, `vrc.v_pp`, ...); the *Auto Detect* button works with standard names. *Jaw Flap Bone* works for simple rigs.
   - **Eye Look**: enable it and assign eye bones for eye tracking and blink (optional but nice).
4. **Materials**: any pink material means the shader is missing or incompatible. Switch to a supported shader (lilToon is a good default).
5. **Test**: *VRChat SDK > Show Control Panel > Builder > Validations*. Fix errors (red) first; warnings are optional.
6. **Build & Test** (local test, only you see it) then **Build & Publish** (upload; see `avatar-upload`).

## Customising: the three systems to know
- **Expression Parameters**: the list of variables the avatar exposes (name + type + saved/synced).
- **Expression Menu**: the radial menu a player opens in-game; its controls change those parameters.
- **Animator Controllers** (Base, Additive, Gesture, Action, FX): the state machines that react to parameters. **FX** is where toggles, blendshape sliders and material changes live.

Detail: `avatar-parameters-and-menu`, `fx-controller`, `avatar-toggles`.

## Quality and safety
- Respect the creator's license for any model/asset you use; paid assets usually forbid redistributing their files.
- Check `performance-ranks` before publishing, or many users will hide your avatar.
- Keep a **backup** of the project before big edits.
