# Uploading an avatar

1. Open *VRChat SDK > Show Control Panel* and log in (Authentication tab).
2. **Builder** tab: choose the avatar in the scene. Read the **Validations**; errors must be fixed, warnings are advice.
3. Click **Build & Test** to try it locally first (it builds, then launches VRChat with your local test avatar; you pick it under *Avatars > Other > Local Test*). Great for catching broken toggles without uploading.
4. Click **Build & Publish** (the "Build" tab may need *Build for Windows* selected; a second platform like Android/Quest requires installing that Build Support module for your Unity version).
5. In *Content Manager* / the upload window, set name, description, content warnings, and a thumbnail (use *Capture* in the scene). Tick the rights checkbox. Upload.
6. In VRChat: Avatar menu > "Mine". Test your toggles, gestures and visemes.

## If it fails
- *"You must be at least New User rank"*: playing a bit in-game raises trust rank; there is no workaround.
- *Build blocked / errors in console*: fix compile errors (red in the Console) first. Compile errors in **any** script block the build.
- *Validation failed: a bad component/shader*: remove the listed component or change shader.
- *Unity version mismatch*: use the version VCC lists for the project; do not open with another one.
- *Upload stuck at "Uploading"*: check the avatar's download/uncompressed size in the Builder tab (there are hard size caps and the size also affects performance rank); big textures are the usual cause: lower Max Size and apply crunch compression.
- *Avatar is blue/blocked in-game*: it is hidden by "Safety settings" or performance rank filter; see `performance-ranks`.

## Cross-platform (Android/Quest/iOS)
You upload a separate build for each platform to the **same avatar ID** (Control Panel shows the blueprint ID). Mobile has strict limits (see `performance-ranks`), no custom shaders (use *VRChat/Mobile* shaders), no dynamic bones beyond limits.
