"""char_update must survive lethal damage applied inside the per-char tick.

ROM ``src/update.c:char_update`` pre-caches ``ch_next = ch->next`` at the top
of the loop body, then calls ``damage(ch, ch, ...)`` for plague/poison/incap/
mortal ticks.  Those damage calls may extract ``ch`` (raw_kill) when the NPC's
hp drops to ROM's death threshold.  The pre-cache plus the explicit comment
``MUST NOT refer to ch after damage taken`` (lines 788-792) means the outer
loop is safe — it never dereferences a freed ``ch_next`` and continues to
tick every subsequent character.

Python's equivalent in ``mud/game_loop.py:char_update`` snapshots
``list(character_registry)`` once and iterates the copy, which gives it the
same guarantee against registry mutation mid-loop.  This test pins that
contract: a poisoned NPC at 1 hp dies during its poison tick; the second NPC
in the same registry slot (later in the snapshot) must still receive its
tick.  If a future refactor switches to live iteration of
``character_registry`` (which a ``for ch in character_registry`` over a list
that ``raw_kill`` mutates would silently skip the next element on), this
test fails.
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
    for vnum in (9100,):
        room_registry.pop(vnum, None)


def _make_room() -> Room:
    room = Room(vnum=9100, name="Tick Test", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[9100] = room
    return room


def _make_npc(room: Room, name: str, *, hp: int = 50, poisoned: bool = False) -> Character:
    mob = Character(
        name=name,
        short_descr=name,
        level=5,
        room=room,
        is_npc=True,
        hit=hp,
        max_hit=50,
        mana=50,
        max_mana=50,
        move=50,
        max_move=50,
        position=int(Position.STANDING),
    )
    if poisoned:
        mob.affected_by = int(AffectFlag.POISON)
        mob.affected = [
            AffectData(
                type="poison",
                level=20,
                duration=10,
                location=0,
                modifier=0,
                bitvector=int(AffectFlag.POISON),
            )
        ]
    room.people.append(mob)
    character_registry.append(mob)
    return mob


def test_lethal_poison_tick_does_not_skip_subsequent_npc():
    from mud.game_loop import char_update

    room = _make_room()
    dying = _make_npc(room, "Dying", hp=1, poisoned=True)
    survivor = _make_npc(room, "Survivor", hp=10, poisoned=False)

    # Survivor starts with move under cap so the regen path is observable
    # after the snapshot iteration reaches them.
    survivor.move = 0
    original_position = int(survivor.position)

    char_update()

    # 1. Dying NPC was extracted by the poison tick's raw_kill path.
    assert dying not in character_registry, "lethal poison tick must extract the NPC"

    # 2. Survivor still in registry and got a tick (regen ran — move went up).
    assert survivor in character_registry, "survivor must still be in registry"
    assert survivor.move > 0, "survivor must have received a regen tick (proves loop continued)"

    # 3. Iteration did not skip the survivor — its position is still STANDING
    #    (no exception left it in a partial state).
    assert int(survivor.position) == original_position
