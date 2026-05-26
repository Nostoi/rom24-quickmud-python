"""`group_gain` must not floor NPC level contributions at 1.

ROM ``src/fight.c:1751`` accumulates ``group_levels``:

    group_levels += IS_NPC (gch) ? gch->level / 2 : gch->level;

For a level-1 NPC group member (e.g. a charmed pet, an NPC follower the
player has grouped with), ROM contributes ``1 / 2 == 0`` to the denominator.
Python's ``mud/groups/xp.py:104-105`` was:

    if getattr(gch, "is_npc", False):
        total_levels += max(1, level // 2)

The ``max(1, ...)`` floor inflates the denominator by 1 at NPC level 1,
making the PC's share-formula divisor larger than ROM's and reducing the
XP awarded to the PC.  Symptom: a level-10 PC grouped with a level-1
charmed pet kills a victim and receives ~10% less XP than ROM would
award.

This test pins the ROM-faithful arithmetic by exercising ``xp_compute``
through ``group_gain`` end-to-end, asserting the awarded XP matches the
ROM denominator (``max(1, total_levels - 1)`` where ``total_levels``
omits the level-1 NPC's contribution).
"""

from __future__ import annotations

import pytest

from mud.groups.xp import group_gain, xp_compute
from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.models.room import Room
from mud.registry import room_registry
from mud.utils import rng_mm


@pytest.fixture(autouse=True)
def _cleanup():
    snapshot = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(snapshot)
    room_registry.pop(9200, None)


def _make_room() -> Room:
    room = Room(vnum=9200, name="Group XP", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[9200] = room
    return room


def _make_pc(room: Room, level: int) -> Character:
    pc = Character(
        name="Leader",
        level=level,
        room=room,
        is_npc=False,
        hit=100,
        max_hit=100,
        mana=100,
        max_mana=100,
        move=100,
        max_move=100,
        position=int(Position.STANDING),
        exp=0,
        alignment=0,
    )
    pc.leader = pc  # own group leader
    pc.played = 0
    pc.logon = 0
    pc.messages = []
    room.people.append(pc)
    character_registry.append(pc)
    return pc


def _make_npc_pet(room: Room, level: int, master: Character) -> Character:
    pet = Character(
        name="Pet",
        short_descr="a pet",
        level=level,
        room=room,
        is_npc=True,
        hit=20,
        max_hit=20,
        position=int(Position.STANDING),
        alignment=0,
    )
    pet.master = master
    pet.leader = master
    room.people.append(pet)
    character_registry.append(pet)
    return pet


def _make_victim(room: Room, level: int) -> Character:
    victim = Character(
        name="Victim",
        short_descr="a victim",
        level=level,
        room=room,
        is_npc=True,
        hit=0,
        max_hit=20,
        position=int(Position.DEAD),
        alignment=0,
    )
    room.people.append(victim)
    character_registry.append(victim)
    return victim


def test_npc_level_one_contributes_zero_to_group_levels():
    """Level-1 NPC pet must contribute 0 (ROM `gch->level / 2 == 0`),
    not 1 (Python's pre-fix `max(1, level // 2)`)."""
    room = _make_room()
    pc = _make_pc(room, level=10)
    pet = _make_npc_pet(room, level=1, master=pc)
    victim = _make_victim(room, level=10)

    # Expected: xp_compute called with total_levels = 10 (PC only).
    # Python pre-fix: xp_compute called with total_levels = 11.
    # We probe via the shared xp_compute formula at the share-divide step.
    rng_mm.seed_mm(99)
    rom_xp = xp_compute(pc, victim, total_levels=10)
    rng_mm.seed_mm(99)
    bug_xp = xp_compute(pc, victim, total_levels=11)
    assert rom_xp != bug_xp, "test sanity: the two denominators must yield different XP"

    # group_gain must use ROM's denominator.
    rng_mm.seed_mm(99)
    baseline_exp = 100_000  # well above exp_per_level floor
    pc.exp = baseline_exp
    pc.alignment = 0  # reset (xp_compute may mutate via alignment-change)
    group_gain(pc, victim)
    awarded = pc.exp - baseline_exp
    assert awarded == rom_xp, (
        f"group_gain awarded {awarded} but ROM would award {rom_xp} "
        f"(Python pre-fix would award {bug_xp} via inflated denominator)"
    )


def test_npc_level_three_contributes_one_unchanged():
    """Sanity: at NPC level 3, ROM (`3 / 2 == 1`) and Python (`max(1, 3 // 2) == 1`)
    agree.  This test must keep passing after the floor is removed."""
    room = _make_room()
    pc = _make_pc(room, level=10)
    pet = _make_npc_pet(room, level=3, master=pc)
    victim = _make_victim(room, level=10)

    # Expected: total_levels = 10 (PC) + 1 (level-3 NPC halved) = 11.
    rng_mm.seed_mm(99)
    expected = xp_compute(pc, victim, total_levels=11)

    rng_mm.seed_mm(99)
    baseline_exp = 100_000
    pc.exp = baseline_exp
    pc.alignment = 0
    group_gain(pc, victim)
    awarded = pc.exp - baseline_exp
    assert awarded == expected
