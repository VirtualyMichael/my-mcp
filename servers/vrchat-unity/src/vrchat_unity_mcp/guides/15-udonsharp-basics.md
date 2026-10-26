# UdonSharp (C# for VRChat worlds)

**Udon** is VRChat's world scripting VM; **UdonSharp (U#)** compiles a restricted subset of C# into it. Worlds only; avatars cannot run scripts (use animators).

## Anatomy of a script
```csharp
using UdonSharp;
using UnityEngine;
using VRC.SDKBase;
using VRC.Udon;

[UdonBehaviourSyncMode(BehaviourSyncMode.None)]   // None / Continuous / Manual / NoVariableSync
public class MyThing : UdonSharpBehaviour
{
    public GameObject target;          // public fields show up in the Inspector

    public override void Interact()    // player clicks it (needs a Collider)
    {
        target.SetActive(!target.activeSelf);
    }
}
```
- The class name **must equal the file name** (`MyThing.cs`).
- Add it to a GameObject through *Add Component* (it is an *UdonBehaviour* with a U# program asset; current SDKs create the program asset automatically, older ones need *Create > U# Script*).
- **Interact** needs a Collider; set the *Interaction Text* and *Proximity* on the UdonBehaviour.

## Events you will use
`Start()`, `Update()` (use sparingly), `Interact()`, `OnPlayerJoined(VRCPlayerApi p)`, `OnPlayerLeft(VRCPlayerApi p)`, `OnPlayerTriggerEnter/Exit(VRCPlayerApi p)` (collider set as **Is Trigger**), `OnPickup()`, `OnDrop()`, `OnPickupUseDown()`, `OnTriggerEnter(Collider c)`, `OnDeserialization()`, `OnOwnershipTransferred(VRCPlayerApi p)`, `OnPlayerRespawn(...)`.

## The local player
```csharp
VRCPlayerApi me = Networking.LocalPlayer;   // may be null in the editor Play mode
me.TeleportTo(pos, rot);
me.SetWalkSpeed(4f); me.SetJumpImpulse(4f);
```
Always check for `Utilities.IsValid(me)` / null before using it.

## Networking (the part that confuses everyone)
- **BehaviourSyncMode**: `None` (local only), `Continuous` (frequent small values like positions), `Manual` (you call `RequestSerialization()` after changing; best for state like toggles), `NoVariableSync` (only events).
- A synced variable is marked **`[UdonSynced]`** and only the **owner** of that object can change it for everyone. Take ownership first: `Networking.SetOwner(Networking.LocalPlayer, gameObject);` then change the variable and call `RequestSerialization();` (Manual mode).
- **Late joiners** receive the last serialized value. React in `OnDeserialization()` or use **`[FieldChangeCallback(nameof(Prop))]`** to run code whenever the synced field changes.
- **Events to everyone**: `SendCustomNetworkEvent(VRC.Udon.Common.Interfaces.NetworkEventTarget.All, nameof(MethodName));` The method must be **public** and take no arguments (events do not carry parameters).
- Pickups/vehicles that move: add **VRC Object Sync** rather than writing your own.
- Keep synced data small; per-object limits apply (~280 bytes manual, less for continuous).

## Rules of the subset
- No `async/await`, no `try/catch` (limited), no generics beyond arrays/lists exposed via `DataList/DataDictionary`, no most .NET APIs; use **VRC Data Containers** (`DataList`, `DataDictionary`) for dynamic collections.
- Only whitelisted ("exposed") Unity/VRC APIs work; if the compiler says it is not exposed, find another way.
- Prefer **arrays** over lists; avoid `Update` for things that can be events; cache `GetComponent` results in `Start`.
- Test in **Build & Test** with 2 clients (*Number of Clients = 2*) to check sync - the editor Play mode does **not** simulate networking.

## Useful starting points
This server's `list_script_templates` / `generate_udon_script` produce working scripts for: toggles (local or synced), teleporters, audio buttons, player trigger zones, spinners, pickup events, animator switches, and a join greeter.
