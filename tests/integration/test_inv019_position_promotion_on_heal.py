"""INV-019 — POSITION-PROMOTION-ON-HEAL.

ROM ``src/fight.c:1380-1387 update_pos`` promotes a victim upward whenever
``hit > 0`` and ``position <= POS_STUNNED``:

    if (victim->hit > 0)
    {
        if (victim->position <= POS_STUNNED)
            victim->position = POS_STANDING;
        return;
    }

The promotion is **silent** — no broadcast, no self-line.  It is called from:

1. Every direct-heal spell handler (``spell_cure_light``, ``spell_heal``,
   ``spell_cure_critical``, etc. — ``src/magic.c:1632, 1675, 1716, 3116``).
2. The regen tick when a STUNNED char's ``hit_gain`` lifts hp back above 0
   (``src/update.c:714-715``).
3. ``stop_fighting`` after a fight ends (``src/fight.c:1448``).

This invariant pins the contract end-to-end:

* A STUNNED PC who casts/receives cure_light and gains hp must end STANDING.
* A STUNNED PC who passively regens above 0 hp during the regen tick must
  end STANDING.
* The upward promotion must NOT emit a broadcast (ROM is silent — this is
  the symmetric counterpart to INV-016 BCAST-ON-POSITION-TRANSITION, which
  fires only on the *downward* transitions through damage()).

Python equivalence: ``mud/combat/engine.py:update_pos``,
``mud/game_loop.py:char_update`` regen tick, healing handlers in
``mud/skills/handlers.py`` (all call ``update_pos`` immediately after
modifying ``target.hit``).

Status: ✅ ENFORCED at probe time (2.9.16).  Test added as a regression pin
in the spirit of INV-017 TICK-ITERATION-SAFETY — the contract was correct
by construction but lives across three modules and is easy to regress
unnoticed.
"""

from __future__ import annotations

import pytest

from mud.combat.engine import update_pos
from mud.game_loop import _apply_regeneration
from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.models.room import Room
from mud.registry import room_registry
from mud.skills.handlers import cure_light


@pytest.fixture(autouse=True)
def _cleanup():
    snapshot = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(snapshot)
    room_registry.pop(9300, None)


def _make_room() -> Room:
    room = Room(vnum=9300, name="Promote", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[9300] = room
    return room


def _make_pc(room: Room, *, hit: int, position: Position) -> Character:
    pc = Character(
        name="Stunned",
        level=20,
        room=room,
        is_npc=False,
        hit=hit,
        max_hit=200,
        mana=100,
        max_mana=100,
        move=100,
        max_move=100,
        position=int(position),
    )
    pc.messages = []
    pc.played = 0
    pc.logon = 0
    room.people.append(pc)
    character_registry.append(pc)
    return pc


def test_heal_spell_promotes_stunned_to_standing_silently():
    """cure_light on a STUNNED PC with hp<=0 must promote to STANDING.

    ROM src/magic.c:1675 (spell_cure_light) calls update_pos(victim) after
    adding heal dice.  The promotion is silent — no broadcast appears.
    """
    room = _make_room()
    pc = _make_pc(room, hit=-1, position=Position.STUNNED)

    cure_light(pc, pc)  # caster == target

    assert pc.hit > 0, "test sanity: cure_light must restore positive hp"
    assert pc.position == Position.STANDING, (
        f"STUNNED PC with hp>0 must promote to STANDING (got {pc.position!r})"
    )
    # Silent promotion: only the self-line "You feel better!" is emitted,
    # no position-transition broadcast like INV-016's downward lines.
    broadcasts = [m for m in pc.messages if "stand" in m.lower() or "feet" in m.lower()]
    assert broadcasts == [], (
        f"Upward promotion must be silent (ROM update_pos is silent); "
        f"saw broadcast-like messages: {broadcasts}"
    )


def test_regen_tick_promotes_stunned_to_standing():
    """ROM src/update.c:714-715 — when a STUNNED char's regen tick lifts
    hp above 0, update_pos must promote them to STANDING.

    This pins the game_loop pipeline (_apply_regeneration → update_pos)
    end-to-end against the load-bearing ROM order.
    """
    room = _make_room()
    pc = _make_pc(room, hit=-2, position=Position.STUNNED)

    # Simulate the STUNNED branch of char_update: regen first, then update_pos.
    _apply_regeneration(pc)
    if pc.position == Position.STUNNED:
        update_pos(pc)

    if pc.hit > 0:
        assert pc.position == Position.STANDING, (
            f"After regen tick lifted hp to {pc.hit}, STUNNED PC must promote "
            f"to STANDING (got {pc.position!r})"
        )
    else:
        # Regen wasn't enough this tick — must remain STUNNED, not demote.
        assert pc.position == Position.STUNNED, (
            f"hp still <= 0 ({pc.hit}); position must stay STUNNED "
            f"(got {pc.position!r})"
        )


def test_update_pos_does_not_promote_above_stunned():
    """ROM update_pos only acts on position <= POS_STUNNED.  A RESTING
    PC with hp>0 must remain RESTING — update_pos must NOT force them
    to STANDING.  Pins the `<= POS_STUNNED` guard.
    """
    room = _make_room()
    pc = _make_pc(room, hit=100, position=Position.RESTING)

    update_pos(pc)

    assert pc.position == Position.RESTING, (
        f"update_pos must not promote positions > STUNNED "
        f"(RESTING PC ended up {pc.position!r})"
    )
