"""ARITH-005: ``xp_compute`` must use ``gch->level`` raw, not floored to 1.

ROM ``src/fight.c:1818-1819`` opens with::

    int xp_compute (CHAR_DATA *gch, CHAR_DATA *victim, int total_levels)
    {
        ...
        level_range = victim->level - gch->level;

There is no floor on ``gch->level``.  At the bottom of the function::

    xp = xp * gch->level / UMAX(1, total_levels - 1);

So a level-0 PC reaching ``xp_compute`` naturally receives ``0`` XP via
``xp * 0``.  Python's ``mud/groups/xp.py:130`` had::

    gch_level = max(1, _resolve_level(getattr(gch, "level", 0)))

This floor treats a level-0 PC as level-1 throughout the routine, so they
receive non-zero XP they should not have, and consume a different row of
``base_exp`` (``level_range = victim_level - 1`` vs ROM's ``victim_level - 0``).

A level-0 PC IS reachable in practice: ``Character`` defaults
``level: int = 0`` (``mud/models/character.py:229``), the test helper
``create_character_record(level=0)`` persists rows with level 0, and the
second loop in ``group_gain`` (``mud/groups/xp.py:114-124``) only skips
NPCs, so a level-0 PC in the kill room reaches ``xp_compute``.
"""

from __future__ import annotations

import pytest

from mud.groups.xp import xp_compute
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
    room_registry.pop(9201, None)


def _make_room() -> Room:
    room = Room(vnum=9201, name="ARITH-005", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[9201] = room
    return room


def _make_pc(room: Room, level: int) -> Character:
    pc = Character(
        name="Newbie",
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
    pc.leader = pc
    pc.played = 0
    pc.logon = 0
    pc.messages = []
    room.people.append(pc)
    character_registry.append(pc)
    return pc


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


def test_level_zero_pc_receives_zero_xp_in_xp_compute():
    """ROM `xp = xp * gch->level / divisor` returns 0 when gch->level == 0.

    Python's pre-fix `max(1, gch_level)` floor treats the level-0 PC as
    level-1, giving non-zero XP. This test pins the ROM-faithful behavior.
    """
    room = _make_room()
    pc = _make_pc(room, level=0)
    victim = _make_victim(room, level=5)

    rng_mm.seed_mm(12345)
    awarded = xp_compute(pc, victim, total_levels=1)
    assert awarded == 0, (
        f"Level-0 PC should receive 0 XP per ROM src/fight.c:1818 (xp * gch->level == 0), got {awarded}"
    )


def test_level_one_pc_unchanged_after_fix():
    """Sanity: a level-1 PC, the boundary case the floor was masking,
    must still get the level-1 XP. This guards against accidentally
    breaking the normal path when the floor is removed."""
    room = _make_room()
    pc = _make_pc(room, level=1)
    victim = _make_victim(room, level=5)

    rng_mm.seed_mm(12345)
    awarded = xp_compute(pc, victim, total_levels=1)
    assert awarded > 0, f"Level-1 PC should still receive positive XP after the floor is removed, got {awarded}"
