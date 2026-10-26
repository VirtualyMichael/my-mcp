# Getting started: the VRChat creator toolchain

**You need:** a PC, a VRChat account (free to look around, but you must have reached the "New User" trust rank or higher before you can upload content), Unity Hub, and the **VRChat Creator Companion (VCC)**.

## The pieces
- **Unity** - the 3D editor everything is built in. VRChat only supports one specific Unity version at a time; VCC tells you which (it has been 2022.3.x for a long time). Never "upgrade" Unity yourself; let VCC pick the version.
- **VCC (VRChat Creator Companion)** - creates and manages projects and installs the **VRChat SDK** into them. Always make projects from VCC, not from Unity Hub directly.
- **VRChat SDK** - adds the *VRChat SDK* menu inside Unity and the components you need. There are two flavours, and a project is one or the other:
  - **Avatars** SDK - make a character people wear.
  - **Worlds** SDK - make a place people visit (includes UdonSharp for scripting).

## First-time setup (about 20 minutes)
1. Install Unity Hub, then VCC (vrchat.com/home/download).
2. In VCC: Settings > Unity Editors > make sure the required Unity version is installed (VCC offers a button).
3. Projects > Create New Project > pick **Avatar** or **World** template > name it > Create.
4. Open the project. Unity imports for a few minutes the first time.
5. Open *VRChat SDK > Show Control Panel*, log in, and tick the "I have read and agree to the Creator Guidelines" box (Builder tab).

## Things that save beginners
- **One project per avatar or per world.** Do not mix them.
- **Back up the whole project folder** before big changes (or use git with a `.gitignore` for `Library/`, `Temp/`, `Logs/`).
- Use VCC's **Manage Project** to update the SDK; never import `.unitypackage` SDK files by hand.
- Put your own files in `Assets/` only. Never edit anything under `Packages/`.
- Save often: **File > Save** *and* **File > Save Project**. Unity keeps scene changes separate from asset changes.

## Next
Avatar: see `avatar-basics`. World: see `world-basics`.
