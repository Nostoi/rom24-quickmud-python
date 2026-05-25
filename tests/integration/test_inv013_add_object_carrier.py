"""INV-013/INV-011 follow-up: ``Character.add_object`` must set
``obj.carried_by`` and update carry counters per ROM
``src/handler.c:1626 obj_to_char``.

ROM ``obj_to_char`` does three things atomically:

    obj->next_content = ch->carrying;
    ch->carrying = obj;
    obj->carried_by = ch;
    obj->in_room = NULL;
    obj->in_obj = NULL;
    ch->carry_number += get_obj_number(obj);
    ch->carry_weight += get_obj_weight(obj);

The Python ``Character.add_object`` previously updated
``inventory`` + carry counters but never set ``obj.carried_by``, so
the canonical INV-013 carrier field stayed ``None`` for every direct
``add_object`` caller. Per the INV-013 property dispatch,
``obj.location = self`` is the convergent way to set the field and
clear the other two (``in_room``, ``in_obj``).

Surfaced through the ``do_mpoload`` audit: the script command
appended directly to ``ch.inventory`` instead of going through
``add_object``, so it hit BOTH gaps — the carrier field stayed unset
AND the carry counters drifted. Both regression tests live here so
``Character.add_object`` and ``do_mpoload`` are pinned to ROM
contracts together.
"""

from __future__ import annotations

import pytest

from mud.mob_cmds import do_mpoload
from mud.models.character import Character
from mud.models.obj import ObjIndex
from mud.models.room import Room
from mud.registry import obj_registry, room_registry
from mud.spawning.obj_spawner import spawn_object

_TEST_VNUM = 91510
_ROOM_VNUM = 9511


@pytest.fixture
def add_room() -> Room:
    room = room_registry.get(_ROOM_VNUM)
    if room is None:
        room = Room(vnum=_ROOM_VNUM, name="Add-Object Test Room")
        room_registry[_ROOM_VNUM] = room
    room.contents.clear()
    room.people.clear()
    return room


@pytest.fixture(autouse=True)
def _register_proto():
    proto = ObjIndex(
        vnum=_TEST_VNUM,
        name="anvil",
        short_descr="an anvil",
        description="A heavy anvil.",
        item_type=1,
        level=5,
        weight=20,
        value=[0, 0, 0, 0, 0],
    )
    obj_registry[_TEST_VNUM] = proto
    yield
    obj_registry.pop(_TEST_VNUM, None)


@pytest.fixture
def carrier(add_room: Room) -> Character:
    ch = Character(name="Carrier", is_npc=True)
    ch.level = 30
    ch.trust = 30
    add_room.add_character(ch)
    return ch


def test_add_object_sets_carried_by(carrier: Character) -> None:
    """``Character.add_object`` must set ``obj.carried_by`` per
    ROM ``src/handler.c:1626 obj_to_char``.
    """

    obj = spawn_object(_TEST_VNUM)
    assert obj is not None

    carrier.add_object(obj)

    assert obj in carrier.inventory
    assert obj.carried_by is carrier, (
        "Character.add_object appended to inventory without setting "
        "obj.carried_by; ROM src/handler.c:1626 obj_to_char sets it "
        "atomically and INV-013 makes carried_by the canonical "
        "carrier field."
    )
    # INV-013: setting carried_by must clear the other two location
    # fields atomically (property dispatch contract).
    assert obj.in_room is None
    assert obj.in_obj is None


def test_mpoload_inventory_sets_carried_by(carrier: Character) -> None:
    """``do_mpoload`` (inventory mode) must route through
    ``Character.add_object`` so the carrier field is set.
    """

    do_mpoload(carrier, f"{_TEST_VNUM}")

    assert len(carrier.inventory) == 1
    obj = carrier.inventory[0]
    assert obj.carried_by is carrier, (
        "do_mpoload appended to ch.inventory directly without calling "
        "ch.add_object(obj); obj.carried_by stayed None, violating "
        "INV-013 and ROM src/mob_cmds.c:603-607 → src/handler.c:1626 "
        "obj_to_char."
    )


def test_mpoload_inventory_updates_carry_counters(carrier: Character) -> None:
    """``do_mpoload`` (inventory mode) must update ``carry_weight``
    and ``carry_number`` per ROM ``obj_to_char`` (INV-011).
    """

    initial_weight = carrier.carry_weight
    initial_number = carrier.carry_number

    do_mpoload(carrier, f"{_TEST_VNUM}")

    obj = carrier.inventory[0]
    proto_weight = int(getattr(obj.prototype, "weight", 0) or 0)
    assert carrier.carry_weight == initial_weight + proto_weight, (
        f"carry_weight={carrier.carry_weight}; expected initial "
        f"({initial_weight}) + obj.weight ({proto_weight}). do_mpoload "
        "must route through Character.add_object so INV-011 carry "
        "counters stay in lockstep with inventory contents."
    )
    assert carrier.carry_number == initial_number + 1
