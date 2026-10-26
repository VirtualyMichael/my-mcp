# World basics

## Setup
Create a **World** project in VCC (the template includes the Worlds SDK with **UdonSharp**). Open the sample scene (*VRCSDK > Samples > UdonExampleScene*) to see working examples.

## Minimum viable world
1. A **VRC_SceneDescriptor** on an object in the scene (*VRChat SDK > Show Control Panel > Builder* offers to add it).
   - **Spawns**: at least one Transform where players appear. Set *Respawn Height Y* below the lowest ground.
   - **Reference camera** (optional), **Capacity** (set it in the upload window; **Recommended Capacity** is a hint).
2. **Geometry** with **Colliders**: players walk on collider surfaces. Mesh Colliders on ground meshes work; avoid concave Mesh Colliders on moving things.
3. **Lighting**: bake lightmaps (*Window > Rendering > Lighting*; use Progressive GPU/CPU, mark meshes *Contribute GI*, set lightmap resolution) for good performance. Add **Light Probes** for avatars/dynamic objects and **Reflection Probes** for reflections.
4. **Post-processing** only with VRChat-supported methods (built-in Post Processing Volume works; keep it light).
5. **Test**: *Build & Test* with 1+ clients from the Control Panel; **Build & Publish** to upload.

## Layers
VRChat reserves layers (Player, PlayerLocal, MirrorReflection, Pickup, Walkthrough, etc.). **Do not** rename the first ~20 reserved ones; use free ones for your own logic. Set the **Layer Collision Matrix** in *VRChat SDK > Utilities > Layer Collision Matrix > Reset*.

## Interactivity
- **Mirror**: add the *VRC Mirror Reflection* prefab (SDK samples) set to be toggled by an interactive switch. Mirrors are costly: start disabled.
- **Pickups**: *VRC Pickup* + a Rigidbody + Collider. Add *VRC Object Sync* to sync position to others.
- **Stations**: *VRC Station* for seats and vehicles.
- **Udon** (programming): see `udonsharp-basics`. Use *Udon Graph* (visual) or **UdonSharp** (C#).

## Optimisation
- Keep draw calls low (static batching on, combine meshes/materials).
- **Occlusion Culling** (Window > Rendering > Occlusion Culling) for large worlds.
- Compress textures (crunch) and keep texture sizes modest.
- Test in Quest if cross-platform: mobile shaders only, much stricter limits.
