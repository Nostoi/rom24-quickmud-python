"""ARITH-203 / ARITH-204: plague tick mana/move drain must not floor at 0.

ROM ``src/update.c:843-845`` (`char_update`, plague branch):

    dam = UMIN (ch->level, af->level / 5 + 1);
    ch->mana -= dam;
    ch->move -= dam;
    damage (ch, ch, dam, gsn_plague, DAM_DISEASE, FALSE);

ROM subtracts ``dam`` from mana and move raw — no floor.  When the
character's current mana/move is below ``dam`` the stats go negative,
exactly as ROM's regen/penalty math expects (a negative pool simply
regenerates back toward zero next tick).

Python's plague tick at ``mud/commands`` → ``mud/game_loop.py:626-627``
clamped both with ``max(0, ... - dam)``, swallowing the negative
drift.  This test pins ROM's raw subtraction: a plagued character with
mana/move below the per-tick ``dam`` must end the tick with negative
mana and move.

Both stats share one ROM line family and one tick, so a single test
covers ARITH-203 (mana) and ARITH-204 (move).
"""

from __future__ import annotations

import pytest

from mud.models.character import AffectData, Character, character_registry
from mud.models.constants import AffectFlag, Position
from mud.models.room import Room
from mud.registry import room_registry


@pytest.fixture(autouse=True)
def _cleanup():
    snapshot = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(snapshot)
    room_registry.pop(9200, None)


def _make_room() -> Room:
    room = Room(vnum=9200, name="Plague Test", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[9200] = room
    return room


def test_plague_tick_drains_mana_and_move_below_zero():
    from mud.game_loop import _char_update_tick_effects

    room = _make_room()
    # level=10, plague af->level=10 → dam = min(10, 10//5 + 1) = min(10, 3) = 3.
    mob = Character(
        name="Plagued",
        short_descr="Plagued",
        level=10,
        room=room,
        is_npc=True,
        hit=100,
        max_hit=100,
        mana=1,
        max_mana=50,
        move=2,
        max_move=50,
        position=int(Position.STANDING),
    )
    mob.affected_by = int(AffectFlag.PLAGUE)
    mob.affected = [
        AffectData(
            type="plague",
            level=10,
            duration=10,
            location=0,
            modifier=-5,
            bitvector=int(AffectFlag.PLAGUE),
        )
    ]
    room.people.append(mob)
    character_registry.append(mob)

    extracted = _char_update_tick_effects(mob)
    assert extracted is False, "100-hp NPC must survive a dam=3 plague tick"

    # ROM src/update.c:843-845 — dam = 3, subtracted raw:
    #   mana: 1 - 3 = -2 ; move: 2 - 3 = -1
    assert mob.mana == -2, (
        f"ARITH-203: plague mana drain must not floor at 0 (ROM "
        f"src/update.c:844 `ch->mana -= dam`). Expected -2, got {mob.mana}."
    )
    assert mob.move == -1, (
        f"ARITH-204: plague move drain must not floor at 0 (ROM "
        f"src/update.c:845 `ch->move -= dam`). Expected -1, got {mob.move}."
    )
