# Unity basics for VRChat creators

## The windows you will use all day
- **Scene** - the 3D view. **Game** - what a camera sees.
- **Hierarchy** - every object in the open scene, in a tree. Children move with parents.
- **Inspector** - the settings of whatever is selected. Components (Transform, Mesh Renderer, Animator...) are listed here.
- **Project** - the files in `Assets/` on disk. **Console** - errors and logs (open it: Window > General > Console). Red errors in the Console usually block VRChat uploads; yellow warnings usually do not.
- **Animation** (Window > Animation > Animation) and **Animator** (Window > Animation > Animator) - covered in the animation guides.

## Core ideas
- **GameObject** = an empty thing in the scene. **Component** = behaviour you attach to it.
- **Prefab** = a saved object you can reuse. Dragging a model (.fbx) into the scene makes one instance.
- **Mesh** (the shape) + **Material** (surface settings) + **Shader** (the program that draws it) + **Texture** (image). Avatars normally use a VRChat-friendly shader such as *lilToon* (free) or *Poiyomi*; the stock "Standard" shader also works.
- **Transform**: position, rotation, scale. Keep avatar root scale at 1,1,1.
- **Skinned Mesh Renderer** is what bends a mesh with bones; it also holds **blendshapes** (face morphs / shape keys).

## Handy shortcuts
`W/E/R` move/rotate/scale, `F` frame selection, `Ctrl+Z` undo, `Ctrl+D` duplicate, `Alt+Click` expand a whole hierarchy branch, hold right mouse + `WASD` to fly in Scene view.

## Editing safely
- Changes made in Play mode are **lost** when you stop. Tick off Play before editing real settings (tint of the Play button changes when active).
- Right-click an asset > *Show in Explorer* to see where it lives.
- If something breaks, `Ctrl+Z` first; Unity's undo is reliable for scene edits.
- Duplicate an asset (`Ctrl+D`) before editing a VRChat default (like the stock FX controller) - edit your copy.
