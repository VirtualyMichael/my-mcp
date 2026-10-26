# Expression Parameters and the Expression Menu

## Expression Parameters (a `VRCExpressionParameters` asset)
A list of variables the avatar's animators can read and the menu can change. Create via *Assets > Create > VRChat > Avatars > Expression Parameters*, then assign it on the Avatar Descriptor (*Customize Expressions / Parameters*).

Each entry has:
- **Name** - exact string; typos silently break things (case-sensitive).
- **Type** - `Bool`, `Int` (0-255), or `Float` (-1 to 1).
- **Default** - starting value.
- **Saved** - remembered between avatar loads/worlds.
- **Synced** - sent to other players. Unsynced parameters work only locally (good for things only you need).

### The 256-bit budget
Synced parameters share **256 bits** of memory: Bool = 1 bit, Int = 8 bits, Float = 8 bits. Over 256 and the build is blocked. Tips: use Bools for toggles; use one **Int** to select among many options (a *selector* parameter) instead of many bools; unsync parameters that only matter locally. (Total shown at the bottom of the parameter asset's inspector.)

### Built-in parameters (always exist, do not declare)
Read-only values from VRChat: `GestureLeft`, `GestureRight` (Int 0-7), `GestureLeftWeight`, `GestureRightWeight` (Float), `Viseme` (Int 0-14), `Voice` (Float), `IsLocal`, `AFK`, `MuteSelf`, `InStation`, `Grounded`, `Seated`, `Upright`, `VelocityX/Y/Z`, `AngularY`, `TrackingType`, `VRMode`, `Earmuffs`, `IsOnFriendsList`, `AvatarVersion`, `ScaleModified`, `ScaleFactor`, `EyeHeightAsMeters` and others (see docs "Animator Parameters"). Gestures: 0 Neutral, 1 Fist, 2 Open hand, 3 Point, 4 Victory, 5 Rock'n'Roll, 6 Hand gun, 7 Thumbs up.

## Expression Menu (a `VRCExpressionsMenu` asset)
Assigned on the Avatar Descriptor. A menu holds **up to 8 controls**. Control types:
- **Button** - sets a parameter to a value while pressed.
- **Toggle** - sets a parameter to a value when switched on (back to 0 when off).
- **Sub Menu** - opens another menu asset (nest as deep as you like).
- **Two Axis Puppet / Four Axis Puppet** - joystick(s), each axis drives a Float parameter.
- **Radial Puppet** - a dial that drives one Float parameter (0 to 1).

A control's **Parameter** must match a name in the Expression Parameters asset, otherwise it does nothing.

## Standard flow for any new feature
1. Add a parameter (name, type, synced/saved).
2. Add the animator logic in the FX controller that reads that parameter (`fx-controller`).
3. Add a menu control that writes the parameter.
4. Build & Test, check the toggle works, and check the performance/bit budget.

(The `vrchat-unity` tools can do steps 1-3 for toggles and blendshape sliders: see `queue_avatar_job`.)
