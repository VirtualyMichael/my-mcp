# The community tools worth knowing

Install most via VCC (*Manage Project > add repository*), or via the vendor's `Add to VCC` button.

| Tool | Use it for |
|---|---|
| **Modular Avatar** (bd_) | Non-destructive: add outfits, merge animators/menus/parameters, bone merge, by dropping prefabs onto an avatar. |
| **VRCFury** | One-component toggles, outfit swaps, gesture toggles; merges at build time; helps with Write Defaults. |
| **NDMF** | The framework Modular Avatar/AAO plug into; installed automatically as a dependency. |
| **Avatar Optimizer (AAO)** by anatawa12 | Merge meshes and materials, remove unused objects/blendshapes, trace-and-optimize with one click. Biggest performance saver. |
| **lilToon** / **Poiyomi** | Popular shaders for avatars. |
| **Av3 Emulator** / **Gesture Manager** | Test animator parameters and menus in Unity Play mode without uploading. |
| **VRCQuestTools** | Convert avatars for Android/Quest. |
| **VRC Fury / MA vs hand-made controllers** | Hand-made: full control, maximum learning; tools: faster, safer to update. |

## Advice
- Use at most **one** of VRCFury or Modular Avatar for a given feature to avoid conflicts (they can coexist but plan carefully).
- All of these run **at build time**; the original scene stays clean, so keep a backup before enabling "bake" options.
- Prefer tools listed in the **VCC community repositories** over random downloads; check licenses and source reputations.
