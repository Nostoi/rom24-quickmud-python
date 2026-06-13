"""PICK-002 — do_pick WAIT_STATE uses skill beats (12) with UMAX semantics.

ROM ``do_pick_lock`` (``src/act_move.c:856``) applies
``WAIT_STATE(ch, skill_table[gsn_pick_lock].beats)`` *before* the guard/skill
checks. The ``WAIT_STATE`` macro is ``ch->wait = UMAX(ch->wait, beats)``, and
``gsn_pick_lock``'s beats is 12 (``src/const.c:1739`` / ``data/skills.json``
``lag: 12``). The Python ``mud/commands/doors.py:do_pick`` used
``char.wait += 24`` — wrong value (24 not 12) and wrong operator (additive,
not max), so repeated picks stacked wait absurdly and a single pick cost twice
the ROM lag.
"""

from __future__ import annotations

import pytest

from mud import registry as global_registry
from mud.models.character import character_registry
from mud.models.constants import ContainerFlag, ItemType
from mud.models.room import Room
from mud.registry import room_registry
from mud.utils import rng_mm
from mud.world import create_test_character


@pytest.fixture(autouse=True)
def _clean_state():
    rooms = set(room_registry)
    char_ids = {id(c) for c in character_registry}
    yield
    for vnum in list(room_registry):
        if vnum not in rooms:
            room_registry.pop(vnum, None)
    character_registry[:] = [c for c in character_registry if id(c) in char_ids]
    for attr in ("players", "char_list", "descriptor_list"):
        if hasattr(global_registry, attr):
            delattr(global_registry, attr)


def _room(vnum: int) -> Room:
    room = Room(vnum=vnum, name=f"Room {vnum}", description="")
    room_registry[vnum] = room
    return room


def _picker(name: str, room_vnum: int):
    char = create_test_character(name, room_vnum)
    char.level = 20
    char.trust = 20
    char.is_npc = False
    char.skills = {"pick lock": 100}
    char.messages = []
    char.wait = 0
    return char


def _locked_chest(room: Room):
    from mud.models.obj import ObjIndex
    from mud.models.object import Object

    proto = ObjIndex(vnum=88950, name="chest", short_descr="a wooden chest")
    chest = Object(instance_id=None, prototype=proto)
    chest.item_type = ItemType.CONTAINER
    chest.value = [0, int(ContainerFlag.CLOSED | ContainerFlag.LOCKED), 1, 0, 0]
    chest.in_room = room
    room.contents = [chest]
    return chest


def test_pick_wait_state_equals_skill_beats_not_24():
    """ROM src/act_move.c:856 — WAIT_STATE(ch, beats=12), not the old +=24 placeholder."""
    from mud.commands.doors import do_pick

    rng_mm.seed_mm(42)
    room = _room(50400)
    picker = _picker("Thief", 50400)
    _locked_chest(room)

    do_pick(picker, "chest")

    assert picker.wait == 12, f"expected ROM pick-lock beats 12, got {picker.wait}"


def test_pick_wait_state_uses_umax_not_addition():
    """ROM WAIT_STATE macro is ch->wait = UMAX(ch->wait, beats) — a higher
    existing wait is preserved, not increased by beats."""
    from mud.commands.doors import do_pick

    rng_mm.seed_mm(42)
    room = _room(50401)
    picker = _picker("Thief", 50401)
    picker.wait = 30  # already higher than beats(12)
    _locked_chest(room)

    do_pick(picker, "chest")

    assert picker.wait == 30, f"UMAX must preserve the higher existing wait, got {picker.wait}"
