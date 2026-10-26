# PhysBones and Contacts

## PhysBones (jiggle for hair, tails, skirts, ears)
1. Add **VRC PhysBone** to the *root bone* of a chain (e.g. the first hair joint). Leave **Root Transform** empty to use itself.
2. Key settings: **Pull** (return to rest), **Spring/Momentum** (how bouncy), **Stiffness**, **Gravity** and **Gravity Falloff**, **Immobile** (resist body movement), **Limits** (angle clamp).
3. **Colliders**: add *VRC PhysBone Collider* components (sphere/capsule/plane) on body bones and list them in the PhysBone's *Colliders* so hair does not clip into the shoulders.
4. **Grab / Pose**: allow others to grab or pose; set **Allow Grabbing / Posing** to *Self* / *Others* / *Both*; use *Max Stretch* to limit pulling.
5. Add a **Parameter** prefix to expose `_IsGrabbed`, `_Angle`, `_Stretch`, etc.

Performance: PhysBone components, affected transforms, colliders and collision checks all count toward performance rank. Tips: fewer, longer chains; **Multi-Child Type** "Ignore" to treat many children as one; remove colliders you do not need.

## Contacts
- **VRC Contact Sender**: emits a *collision tag* (like "Hand"). **VRC Contact Receiver**: reacts to matching tags; its output (Constant bool, OnEnter, or Proximity float) goes into a **Parameter** name you type.
- Use cases: headpat, touch-reactive clothes, "boop" sliders.
- Default *Allow Self* / *Allow Others* control who can trigger it; leave "Allow Self" off to avoid accidental triggers.
- Receivers count toward the performance stats; unsync (do not sync) parameters that only affect you.

## Common mistakes
- Colliders on the *same* bone as the PhysBone chain they should block - move them to the parent.
- Forgetting to add the parameter to Expression Parameters (nothing will read it).
- Too much **Stiffness**/ **Pull** = chain looks rigid; too little = floppy; tune in Play mode with the SDK's Preview (Av3 Emulator) or Build & Test.
