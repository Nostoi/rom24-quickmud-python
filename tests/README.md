# Test Fixtures Cheat Sheet

This repo includes a small set of pytest fixtures and helpers to keep tests concise and parity‑oriented.

Use these instead of hand‑rolled setup when possible.

- ensure_can_move(entity, points=100)
  - Callable fixture that sets `move/max_move` and initializes `affected_by` and `wait` fields when absent.
  - Use when a test character/NPC must be able to move.

- movable_char_factory(name, room_vnum, points=100)
  - Creates a test character in a room and ensures it can move.

- movable_mob_factory(vnum, room_vnum, points=100)
  - Spawns a mob and places it in a room, ensuring movement fields are set.

- object_factory(proto_kwargs)
  - Returns an `Object` built from an `ObjIndex(**proto_kwargs)` without placing it in a room.

- place_object_factory(room_vnum, vnum=None, proto_kwargs=None)
  - Places an object into a room. Use `vnum` to spawn from prototypes or `proto_kwargs` to construct ad‑hoc.

- portal_factory(room_vnum, to_vnum, closed=False)
  - Convenience helper to place a portal in a room. Sets `value` fields ROM‑style.

Examples

```python
# Make a movable character in the Temple and walk north
ch = movable_char_factory('Walker', 3001)
msg = process_command(ch, 'north')

# Spawn a mob in the Temple prepared for movement
mob = movable_mob_factory(3000, 3001)

# Create an inventory boat (not placed in room)
boat = object_factory({
    'vnum': 9999,
    'short_descr': 'a small boat',
    'item_type': int(ItemType.BOAT),
})
ch.add_object(boat)

# Place a portal to room 3054 in the Temple
portal_factory(3001, to_vnum=3054, closed=False)
```

Guideline
- Prefer these fixtures for new tests. If you see hand‑rolled object creation or room placement, consider replacing with `object_factory` / `place_object_factory` / `portal_factory` for consistency and clarity.
