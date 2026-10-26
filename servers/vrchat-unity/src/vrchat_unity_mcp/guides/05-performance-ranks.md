# Avatar performance ranks and optimisation

VRChat ranks avatars **Excellent / Good / Medium / Poor / Very Poor**, based on the *worst* stat. Many users hide Poor and Very Poor avatars. Open the **Avatar Performance Stats** window from *VRChat SDK > Show Control Panel > Builder* (it shows your numbers live).

## What is counted (PC)
Triangles, texture memory, skinned meshes, meshes, material slots, bones, PhysBones components/transforms/colliders/collision checks, Contacts, Animators, lights, particle systems/ trails/ lines, audio sources, constraints, and download size.
Approximate "Good" ceilings on PC: **70,000 triangles**, **1-2 skinned meshes** (Excellent: 1), **8 material slots** at Good (Excellent: 4), **150 bones** at Good (Excellent: 75). The exact current table is on docs.vrchat.com ("Avatar Performance Ranks"); check it, because VRChat revises numbers.

## The big wins, in order
1. **Material slots / skinned meshes**: *every* material slot is a draw call. Merge meshes and atlas textures (tools: Avatar Optimizer *AAO: Trace and Optimize*, Modular Avatar mesh merge, or *Combine Meshes*). Delete hidden/unused mesh pieces.
2. **Textures**: lower *Max Size* (1024 or 2048 is plenty for most), enable *Crunch Compression* for non-hero textures; remove unused textures from the project (only referenced ones are uploaded).
3. **Triangles**: delete hidden body under clothes (or use *AAO Remove Mesh By Blendshape*), or decimate the mesh.
4. **PhysBones**: fewer components, shorter chains, fewer colliders. Collision checks multiply fast.
5. **Constraints/animators/particles**: remove what you do not need; lights and particle systems are heavy.
6. **Download size**: compress textures; avoid huge audio.

## Rules of thumb
- Aim for **Good** for general use. **Excellent** is for public/social crowds.
- Anything toggleable still counts toward the rank (unless removed at build time by a tool like AAO that can strip unused things).
- Blendshape count affects memory; delete unused shape keys in Blender.
- Mobile (Android/iOS) limits are much stricter and have hard caps; see the docs.
