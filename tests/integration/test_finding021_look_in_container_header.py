"""FINDING-021 — `look in <container>` header parity with ROM.

ROM `src/act_info.c:1166-1167` renders the container-contents view with two
unconditional steps:

    act ("$p holds:", ch, obj, NULL, TO_CHAR);   /* header, act-capitalized */
    show_list_to_char (obj->contains, ch, TRUE, TRUE);

`act_new` capitalizes the first visible character of the header (INV-029 /
ACT-CAP), so a bag whose short_descr is "a bag" prints ``A bag holds:``. When
the container is empty, `show_list_to_char` with ``fShowNothing == TRUE`` and
``nShow == 0`` prints ``Nothing.`` (no leading indent for a normal PC — the
5-space pad is NPC/COMM_COMBINE only, `act_info.c:229-230`). ROM has **no**
"is empty" branch for containers — that wording was a Python invention.

These tests pin both the capitalized header and the ROM empty rendering.
"""

from __future__ import annotations

from mud.commands.dispatcher import process_command
from mud.models.character import Character
from mud.models.constants import ItemType, Position
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Room


def _make_pc_in_room() -> tuple[Character, Room]:
    room = Room(vnum=9501, name="test-room")
    pc = Character(name="testpc", is_npc=False, level=10, position=Position.STANDING)
    room.add_character(pc)
    return pc, room


def _make_bag() -> Object:
    proto = ObjIndex(
        vnum=8600,
        name="bag",
        short_descr="a bag",
        item_type=int(ItemType.CONTAINER),
    )
    obj = Object(instance_id=0, prototype=proto)
    obj.short_descr = "a bag"
    # value[1] container flags = 0 → open.
    obj.value = [0, 0, 0, 0, 0]
    return obj


def _make_loot(name: str = "sword") -> Object:
    proto = ObjIndex(vnum=8601, name=name, short_descr=f"a {name}")
    obj = Object(instance_id=0, prototype=proto)
    obj.short_descr = f"a {name}"
    return obj


def test_finding021_look_in_container_header_is_act_capitalized():
    """ROM src/act_info.c:1166 — act("$p holds:") caps the first visible char."""
    pc, room = _make_pc_in_room()
    bag = _make_bag()
    sword = _make_loot("sword")
    bag.contained_items.append(sword)
    sword.in_obj = bag
    room.add_object(bag)

    result = process_command(pc, "look in bag")

    assert "A bag holds:" in result, f"expected act-capitalized header, got: {result!r}"
    assert "a bag holds:" not in result, f"header must not be lowercase, got: {result!r}"
    assert "a sword" in result, f"contents stay lowercase (not act-capped), got: {result!r}"


def test_finding021_look_in_empty_container_renders_nothing():
    """ROM src/act_info.c:1166-1167 — empty container: "A bag holds:" then "Nothing."."""
    pc, room = _make_pc_in_room()
    bag = _make_bag()  # no contents
    room.add_object(bag)

    result = process_command(pc, "look in bag")

    assert "A bag holds:" in result, f"empty container still emits the header, got: {result!r}"
    assert "Nothing." in result, f"empty container lists 'Nothing.', got: {result!r}"
    # ROM has no "is empty" branch for containers (only drink-cons say "It is empty.").
    assert "is empty" not in result.lower(), f"container must not say 'is empty', got: {result!r}"
