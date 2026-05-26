"""INV-024 — CONTAINER-CLOSED-VISIBILITY.

ROM `src/act_obj.c:291-295` (`do_get`) and `:384-388` (`do_put`)
short-circuit with ``act("The $d is closed.", ...)`` whenever the
target ITEM_CONTAINER has ``CONT_CLOSED`` set on ``value[1]``.
``src/act_info.c:1160-1162`` (the ``do_look`` "in <container>"
branch) emits ``"It is closed."`` and returns. ROM `do_examine`
(`src/act_info.c:1320-1386`) delegates to ``do_look "in
<container>"`` for ITEM_CONTAINER / ITEM_CORPSE_NPC /
ITEM_CORPSE_PC, so it inherits the gate transitively.

The contract spans four command surfaces in three modules:

- ``mud/commands/inventory.py:do_get`` (line 515) — gates the
  transfer; without it, ``get all sack`` from a locked chest
  would pull contents through the closed lid.
- ``mud/commands/obj_manipulation.py:do_put`` (line 104) — gates
  insertion; without it, ``put sword chest`` into a closed
  container would silently succeed and the item would vanish
  into a locked box.
- ``mud/world/look.py:_look_at_object`` (line 325) — gates
  the contents listing; without it, ``look in chest`` would
  reveal the closed container's inventory.
- ``mud/commands/info_extended.py:do_examine`` — routes through
  ``do_look "in <name>"`` (line 88, 94), inheriting the gate.

Without all four gates aligned, a player can read or move items
through a closed lid. This row pins the contract end-to-end.
"""

from __future__ import annotations

from mud.commands.dispatcher import process_command
from mud.models.character import Character
from mud.models.constants import ContainerFlag, ItemType, Position, WearFlag
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Room


def _make_pc_in_room() -> tuple[Character, Room]:
    room = Room(vnum=9500, name="test-room")
    pc = Character(
        name="testpc", is_npc=False, level=10, position=Position.STANDING
    )
    room.add_character(pc)
    return pc, room


def _make_chest(closed: bool) -> Object:
    proto = ObjIndex(
        vnum=8500,
        name="chest",
        short_descr="a heavy chest",
        item_type=int(ItemType.CONTAINER),
    )
    obj = Object(instance_id=0, prototype=proto)
    obj.short_descr = "a heavy chest"
    # value[1] is the container-flags slot in ROM.
    obj.value = [0, int(ContainerFlag.CLOSED) if closed else 0, 0, 0, 0]
    return obj


def _make_loot(name: str = "ruby") -> Object:
    proto = ObjIndex(vnum=8501, name=name, short_descr=f"a {name}")
    obj = Object(instance_id=0, prototype=proto)
    obj.short_descr = f"a {name}"
    # ITEM_TAKE so do_get can transfer it (ROM src/handler.c:can_drop_obj).
    obj.wear_flags = int(WearFlag.TAKE)
    return obj


def test_inv024_get_all_from_closed_container_is_blocked():
    """ROM src/act_obj.c:291-295 — `get all <closed>` returns "is closed", no transfer."""
    pc, room = _make_pc_in_room()
    chest = _make_chest(closed=True)
    ruby = _make_loot("ruby")
    chest.contained_items.append(ruby)
    ruby.in_obj = chest
    room.add_object(chest)

    result = process_command(pc, "get all chest")

    assert "closed" in result.lower(), f"expected 'closed' refusal, got: {result!r}"
    assert ruby in chest.contained_items, (
        "ruby must still be inside the closed chest (no transfer through lid)"
    )
    assert ruby not in pc.inventory, "ruby must not have moved to PC inventory"


def test_inv024_put_into_closed_container_is_blocked():
    """ROM src/act_obj.c:384-388 — `put X <closed>` returns "is closed", no insert."""
    pc, room = _make_pc_in_room()
    chest = _make_chest(closed=True)
    ruby = _make_loot("ruby")
    pc.inventory.append(ruby)
    ruby.carried_by = pc
    room.add_object(chest)

    result = process_command(pc, "put ruby chest")

    assert "closed" in result.lower(), f"expected 'closed' refusal, got: {result!r}"
    assert ruby not in chest.contained_items, (
        "ruby must not pass through the closed lid"
    )
    assert ruby in pc.inventory, "ruby must remain in PC inventory"


def test_inv024_look_in_closed_container_hides_contents():
    """ROM src/act_info.c:1160-1162 — `look in <closed>` returns "It is closed.\"."""
    pc, room = _make_pc_in_room()
    chest = _make_chest(closed=True)
    ruby = _make_loot("ruby")
    chest.contained_items.append(ruby)
    ruby.in_obj = chest
    room.add_object(chest)

    result = process_command(pc, "look in chest")

    assert "closed" in result.lower(), f"expected closed message, got: {result!r}"
    assert "ruby" not in result.lower(), (
        f"closed container must not leak its contents (got: {result!r})"
    )


def test_inv024_get_all_from_OPEN_container_succeeds():
    """Negative control: opening the chest lifts every gate."""
    pc, room = _make_pc_in_room()
    chest = _make_chest(closed=False)  # OPEN
    ruby = _make_loot("ruby")
    chest.contained_items.append(ruby)
    ruby.in_obj = chest
    room.add_object(chest)

    process_command(pc, "get all chest")

    assert ruby not in chest.contained_items, (
        "open chest must allow transfer"
    )
    assert ruby in pc.inventory, "ruby must have moved to PC inventory"
