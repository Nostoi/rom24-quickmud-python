"""FIGHT-055 enforcement — xp_compute alignment mutation + multiplier snapshot.

ROM src/fight.c:1878-1914 xp_compute has two contracts Python violated:

SUB-GAP A — zero base_exp does not skip alignment mutation:
    When level_range < -9, base_exp == 0.  ROM still runs the alignment block.
    UMAX(1, change) forces change=1 when align > 500 or align < -500, even though
    base_exp==0 makes the raw arithmetic give 0.  Python returned early at
    `if base_exp <= 0: return 0`, skipping the alignment write entirely.

    ROM src/fight.c:1890-1895:
        align = victim->alignment - gch->alignment;
        else if (align > 500) {
            change = (align - 500) * base_exp / 500 * gch->level / total_levels;  // == 0
            change = UMAX(1, change);   // == 1  <-- still fires!
            gch->alignment = UMAX(-1000, gch->alignment - change);  // decremented by 1

SUB-GAP B — XP multiplier reads post-mutation gch->alignment:
    Python captured a snapshot `gch_alignment` before mutation and used it in the
    XP multiplier branch conditions (ROM src/fight.c:1916+).  A character whose
    alignment crosses a threshold during mutation gets the wrong multiplier path.

    ROM src/fight.c:1916 (post mutation block):
        else if (gch->alignment > 500) {  /* goodie two shoes  */
    Python (pre-mutation snapshot):
        elif gch_alignment > 500:   # BUG: uses old value
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from mud.groups.xp import xp_compute
from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.models.room import Room
from mud.registry import room_registry
from mud.utils import rng_mm

_ROOM_VNUM = 9210


@pytest.fixture(autouse=True)
def _cleanup():
    snapshot = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(snapshot)
    room_registry.pop(_ROOM_VNUM, None)


def _make_room() -> Room:
    room = Room(vnum=_ROOM_VNUM, name="FIGHT-055", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[_ROOM_VNUM] = room
    return room


def _make_pc(room: Room, *, level: int, alignment: int) -> Character:
    pc = Character(
        name="Fighter",
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
        alignment=alignment,
    )
    pc.leader = pc
    pc.played = 0
    pc.logon = 1000  # fixed epoch (int) for deterministic elapsed in test B
    pc.messages = []
    room.people.append(pc)
    character_registry.append(pc)
    return pc


def _make_victim(room: Room, *, level: int, alignment: int) -> Character:
    victim = Character(
        name="Victim",
        short_descr="a victim",
        level=level,
        room=room,
        is_npc=True,
        hit=0,
        max_hit=20,
        position=int(Position.DEAD),
        alignment=alignment,
    )
    room.people.append(victim)
    character_registry.append(victim)
    return victim


def test_fight055_zero_base_exp_alignment_mutates():
    """ROM fight.c:1890-1895 — UMAX(1, change) shifts alignment by 1 even when base_exp==0.

    level_range = 5 - 20 = -15 → base_exp = 0 (below -9 cutoff, switch default).
    align_delta = 1000 - (-600) = 1600 > 500 → change = (1600-500)*0/500*... = 0 → UMAX(1,0) = 1.
    gch->alignment = UMAX(-1000, -600 - 1) = -601.

    Python's early `if base_exp <= 0: return 0` skips the mutation entirely (remains -600).

    Mutation target: remove the early return, let alignment block always run.
    Red before fix: alignment stays -600.
    """
    room = _make_room()
    gch = _make_pc(room, level=20, alignment=-600)
    victim = _make_victim(room, level=5, alignment=1000)

    rng_mm.seed_mm(12345)
    awarded = xp_compute(gch, victim, total_levels=20)

    # XP is 0 since base_exp == 0 drives all multiplier paths to 0
    assert awarded == 0, f"Expected 0 XP for out-of-range kill, got {awarded}"
    # mirroring ROM src/fight.c:1893-1894: UMAX(1, 0) = 1 shift even at base_exp == 0
    assert gch.alignment == -601, (
        f"ROM forces alignment shift of 1 via UMAX(1,change) even when base_exp==0; expected -601, got {gch.alignment}"
    )


def test_fight055_xp_multiplier_uses_post_mutation_alignment():
    """ROM fight.c:1916 — XP multiplier reads gch->alignment after mutation, not before.

    Setup: gch alignment 510, victim alignment 1000 (very good), same level (base_exp=83).
    align_delta = 1000 - 510 = 490 → else (neutral) branch.
    change = c_div(c_div(510*83, 500)*15, 15) = 84.
    gch.alignment = 510 - 84 = 426 (crosses the 500 threshold downward).

    Post-mutation (426 > 200): 'a little good' path → xp = base_exp/2 = 41.
    Pre-mutation  (510 > 500): 'goodie two shoes' path → xp = base_exp/4 = 20.

    After time/level scaling (elapsed=0 → time_per_level=2, nr returns low):
      post: 41 → *2/12=6 → nr(4,7)=4 → *15/14=4
      pre:  20 → *2/12=3 → nr(2,3)=2 → *15/14=2

    Mutation target: replace gch_alignment with gch.alignment in the multiplier.
    Red before fix: awarded == 2 (snapshot path).
    """
    room = _make_room()
    # gch.logon = 1000.0 set by _make_pc; patch time.time to same value → elapsed=0
    gch = _make_pc(room, level=15, alignment=510)
    victim = _make_victim(room, level=15, alignment=1000)

    with (
        patch("mud.groups.xp.time.time", return_value=1000.0),
        patch("mud.groups.xp.rng_mm.number_range", side_effect=lambda lo, hi: lo),
    ):
        awarded = xp_compute(gch, victim, total_levels=15)

    # mirroring ROM src/fight.c:1916: gch->alignment is post-mutation (426)
    # 'a little good' path: victim > 750 → xp = base_exp/2, scales to 4
    assert awarded == 4, (
        f"Post-mutation alignment 426 (>200) gives 'a little good' XP path (expected 4); "
        f"got {awarded} (snapshot path 510>500 gives 'goodie' xp=2)"
    )
    # alignment mutation itself is also correctly computed
    assert gch.alignment == 426, f"Expected post-mutation alignment 426, got {gch.alignment}"
