"""Regression tests for live in-game runtime crashes observed 2026-04-30.

These are Python defects (not ROM parity gaps) — fixes are defensive coding
and JSON-loader normalization. ROM C is unaffected.

Bugs covered:
- BUG-NLOWER: ``get_obj_carry`` / friends crash with ``'NoneType' object has
  no attribute 'lower'`` when an object's prototype ``name`` field is None
  (JSON-loaded prototypes drop the keyword list field).
- BUG-EDDICT: ``look`` / ``read`` on objects with extra_descr loaded as
  dicts crash with ``'dict' object has no attribute 'description'``.
- BUG-CORPSEINT: ``get coins corpse`` crashes with
  ``invalid literal for int() with base 10: 'npc_corpse'`` because the JSON
  loader stores prototype ``item_type`` as the raw string token.
"""

from __future__ import annotations

import pytest

from mud.commands.inventory import do_get
from mud.models.character import Character, character_registry
from mud.models.constants import ItemType
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Room
from mud.registry import room_registry
from mud.world.look import _look_obj
from mud.world.obj_find import get_obj_carry


@pytest.fixture
def crash_room():
    room = Room(vnum=99000, name="Crash Test Room", description=".", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[99000] = room
    yield room
    room_registry.pop(99000, None)


@pytest.fixture
def crash_char(crash_room):
    char = Character(
        name="Tester",
        level=5,
        room=crash_room,
        gold=0,
        hit=100,
        max_hit=100,
        is_npc=False,
    )
    crash_room.people.append(char)
    character_registry.append(char)
    yield char
    if char in crash_room.people:
        crash_room.people.remove(char)
    if char in character_registry:
        character_registry.remove(char)


def test_get_obj_carry_handles_prototype_name_none(crash_char):
    """BUG-NLOWER: prototype.name=None must not crash inventory keyword lookup."""
    proto = ObjIndex(vnum=99100, name=None, short_descr="a featherlight scroll")
    obj = Object(instance_id=None, prototype=proto)
    crash_char.add_object(obj)

    # Match by short_descr substring; name is None and must be coerced safely.
    found = get_obj_carry(crash_char, "scroll")
    assert found is obj


def test_look_obj_handles_dict_extra_descr(crash_char):
    """BUG-EDDICT: prototype.extra_descr stored as list-of-dicts must work."""
    proto = ObjIndex(
        vnum=99101,
        name="fountain",
        short_descr="a marble fountain",
        description="A marble fountain.",
    )
    proto.extra_descr = [
        {"keyword": "fountain marble", "description": "Sparkling water."}
    ]
    obj = Object(instance_id=None, prototype=proto)

    result = _look_obj(crash_char, obj)
    assert "Sparkling water." in result


def test_do_get_corpse_handles_string_item_type(crash_char):
    """BUG-CORPSEINT: container prototype with string item_type must not crash do_get."""
    corpse_proto = ObjIndex(
        vnum=99102,
        name="corpse",
        short_descr="the corpse of a goblin",
        description="The corpse of a goblin lies here.",
        item_type="npc_corpse",  # string token, mirroring JSON-loaded data
    )
    corpse_proto.value = [0, 0, 0, 0, 0]
    corpse = Object(instance_id=None, prototype=corpse_proto)
    corpse.item_type = int(ItemType.CORPSE_NPC)
    corpse.location = crash_char.room

    coin_proto = ObjIndex(
        vnum=99103,
        name="coins silver",
        short_descr="some coins",
        item_type="money",
    )
    coin_proto.value = [10, 0, 0, 0, 0]
    coin = Object(instance_id=None, prototype=coin_proto)
    coin.item_type = int(ItemType.MONEY)
    coin.value = [10, 0, 0, 0, 0]
    corpse.contained_items.append(coin)
    crash_char.room.contents.append(corpse)

    # Must not raise ValueError on int("npc_corpse").
    result = do_get(crash_char, "coins corpse")
    assert "coin" in result.lower() or "silver" in result.lower()
