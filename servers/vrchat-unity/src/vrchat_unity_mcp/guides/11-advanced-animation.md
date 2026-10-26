# Advanced avatar animation

## Blend trees
A **blend tree** state blends several clips by parameter values: 1D (one float), 2D (two floats), or **Direct** (each child has its own weight parameter).
- **Radial / slider** puppets: a 1D tree with "off" at 0 and "on" at 1, or a single clip with Motion Time.
- **Direct blend tree** with a constant `1` parameter (commonly named `One`) lets one layer drive *many* toggles cheaply; each child clip's weight is its own Bool/Float parameter. This is how large toggle sets avoid dozens of layers.
- For a Direct blend tree, **Write Defaults** and the child *Normalize* setting matter; keep it OFF consistently.

## Gesture-driven features
`GestureLeft` / `GestureRight` are Ints 0-7 (see `avatar-parameters-and-menu`). Typical use: Gesture layer (with a hands-only **Avatar Mask**) switches hand poses; FX layer swaps face blendshapes for each gesture. For "fist to toggle a glow", combine `GestureRight == 1` with a menu Bool in transition conditions.
- Use `GestureLeftWeight` / `GestureRightWeight` (trigger squeeze 0-1) to scale blendshapes or particle strength.

## Animator drivers (state behaviours)
Add via a state > *Add Behaviour*:
- **VRC Avatar Parameter Driver**: sets, adds, randomises or copies parameters when entering a state. Uses: random outfit button (Random), "reset all" button, copy a Float to an Int, or chain actions without reaching the menu.
- **VRC Animator Layer Control**: turns a *playable layer's weight* on/off (e.g. an emote disables the Gesture layer).
- **VRC Animator Tracking Control**: switches body parts between *tracked* and *animated*; use when an emote needs full control of hands/head. **Always restore tracking** on exit or players will be stuck.
- **VRC Animator Temporary Pose Space**: used for sitting/pose adjustments.
- **VRC Play Audio**: plays an AudioSource on state enter.

## Action layer emotes
Full-body emotes live in the Action layer. Use `VRCEmote` (an Int parameter) in the menu to trigger emote states, plus *Tracking Control* and a **Pose Space** if needed. Use `AFK`, `InStation`, and `Seated` to avoid conflicts.

## Contacts and PhysBones as parameters
A **VRC Contact Receiver** writes `Float`/`Bool`/`Proximity` values into parameters when another Contact Sender touches it; a **VRC PhysBone** exposes `<Parameter>_IsGrabbed`, `_IsPosed`, `_Angle`, `_Stretch`, `_Squish` etc. when a *Parameter* prefix is set. These are used for headpats, interactive costumes, and sliders you "pull". Remember to add them to Expression Parameters *with matching type* and mark them **Unsynced** unless other players need them (saves bits).

## OSC
Avatars can be driven externally via **OSC** (UDP). The VRChat client listens on port 9000 for `/avatar/parameters/<name>` messages; outputs are sent on 9001. Only parameters present in the avatar's Expression Parameters are exposed. Requires enabling OSC in the Action Menu > Options.

## Optimising big controllers
- Replace many identical-pattern layers with a Direct blend tree or Int selector.
- Keep **Layer weights** constant, avoid per-frame "any state" cascades when possible.
- Merge animators with **Modular Avatar** / **VRCFury** to keep source controllers clean.
