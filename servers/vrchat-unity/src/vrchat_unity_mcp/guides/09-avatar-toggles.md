# Avatar toggles and sliders (hands-on)

## A. Easiest: use a tool
- **Modular Avatar** (free, VCC listing "Modular Avatar"): add *MA Menu Installer* + *MA Parameters* + *MA Merge Animator* style components; it merges your parts non-destructively at build time.
- **VRCFury** (free, VCC): add a *Toggle* component to the object; it creates clips, layer, parameter and menu entry for you.
Both leave your original controller untouched, which makes updates and avatar changes easy. Great default for most people.

## B. By hand (what the tools do under the hood)
Toggle a "Hat" object on/off:
1. **Make the clips.** Select the avatar. Animation window > *Create* > save `Hat_Off.anim`. Click *Add Property* > the Hat GameObject > *Game Object > Is Active* > set to **0**. Create `Hat_On.anim` the same way with **1**. (Or enable *Record*, toggle the object in the Inspector, then stop recording.)
2. **FX controller**: add a Bool parameter `Hat`; add a layer `Hat`, set weight 1; two states `Off` (clip `Hat_Off`) and `On` (clip `Hat_On`); transitions Off>On when `Hat` = true, On>Off when `Hat` = false; for both: Has Exit Time off, Duration 0. Write Defaults: match the rest of the controller (see `write-defaults`).
3. **Parameter**: in the avatar's Expression Parameters add `Hat`, **Bool**, default 0 (or 1 if it starts on), Saved on if you want it remembered, Synced on.
4. **Menu**: in the Expression Menu add control: type **Toggle**, name "Hat", parameter `Hat`.
5. Upload / Build & Test.

## C. Blendshape slider (e.g. "Ear size")
- Clip with a 2-keyframe curve on the Skinned Mesh Renderer's blendshape (e.g. `blendShape.EarSize`, value 0 at time 0 and 100 at the last frame).
- Controller: float parameter `EarSize`; layer with one state using that clip, and set the state's **Motion Time** = parameter `EarSize`.
- Parameter asset: `EarSize` Float; Menu: **Radial Puppet** controlling `EarSize`.

## D. Many outfits: use an Int selector
One Int parameter `Outfit` (8 bits) + one layer per outfit (transition when `Outfit == N`) is far cheaper than a Bool for each outfit.

## Pitfalls
- Clip paths are relative to the **avatar root** (e.g. `Body/Hat`). If you rename/move the object, re-point the clip.
- Toggling a **Skinned Mesh Renderer's GameObject** off is fine; toggling a parent that also holds PhysBones components can reset them.
- Defaults: the object's state in the scene (Inspector checkbox) is what it looks like before any animation runs, so set it to match the parameter default.
