"""GL-024: a level-1 plague affect is dormant — no spread, drain, or damage.

ROM ``src/update.c:803-846`` (`char_update`, plague branch):

    act ("$n writhes in agony ...", ...);      // 803-804  (always)
    send_to_char ("You writhe in agony ...");  // 805      (always)
    for (af = ...) { if (af->type == gsn_plague) break; }
    ...
    if (af->level == 1)                          // 818
        continue;                                // 819  <-- skips the rest
    ...spread...                                 // 821-841
    dam = UMIN (ch->level, af->level / 5 + 1);   // 843
    ch->mana -= dam;                             // 844
    ch->move -= dam;                             // 845
    damage (ch, ch, dam, gsn_plague, ...);       // 846

At ``af->level == 1`` ROM prints the writhe messages, then ``continue``
skips spread + mana/move drain + ``damage()`` entirely — a level-1
plague is effectively dormant that tick.

Python's ``_char_update_tick_effects`` gated only the *spread* on
``if af_level > 1:``; the drain and ``damage()`` ran regardless, so a
level-1 plague kept draining mana/move and dealing disease damage.
This test pins ROM's behaviour: at ``af.level == 1`` the character's
mana, move, and hit are all unchanged by the tick.
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
    room_registry.pop(9201, None)


def _make_room() -> Room:
    room = Room(vnum=9201, name="Plague L1 Test", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[9201] = room
    return room


def test_level1_plague_does_not_drain_or_damage():
    from mud.game_loop import _char_update_tick_effects

    room = _make_room()
    mob = Character(
        name="Plagued",
        short_descr="Plagued",
        level=10,
        room=room,
        is_npc=True,
        hit=50,
        max_hit=50,
        mana=20,
        max_mana=50,
        move=20,
        max_move=50,
        position=int(Position.STANDING),
    )
    mob.affected_by = int(AffectFlag.PLAGUE)
    mob.affected = [
        AffectData(
            type="plague",
            level=1,  # ROM src/update.c:818 — level 1 plague is dormant
            duration=10,
            location=0,
            modifier=-5,
            bitvector=int(AffectFlag.PLAGUE),
        )
    ]
    room.people.append(mob)
    character_registry.append(mob)

    extracted = _char_update_tick_effects(mob)
    assert extracted is False

    # ROM src/update.c:818-819 — `if (af->level == 1) continue;` skips the
    # drain + damage block, so all three pools are untouched this tick.
    assert mob.mana == 20, f"GL-024: level-1 plague must not drain mana; got {mob.mana}"
    assert mob.move == 20, f"GL-024: level-1 plague must not drain move; got {mob.move}"
    assert mob.hit == 50, f"GL-024: level-1 plague must not deal damage; got {mob.hit}"
