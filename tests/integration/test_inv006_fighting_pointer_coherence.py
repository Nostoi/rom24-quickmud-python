"""INV-006 FIGHTING-POINTER-COHERENCE enforcement.

ROM ref: src/fight.c:stop_fighting(victim, TRUE) sweeps char_list and clears
``fch->fighting`` for every fch where ``fch->fighting == victim``. This keeps
multi-attacker scenarios from leaving stale ``.fighting`` pointers when the
shared target dies.

Python: mud/combat/engine.py:stop_fighting(ch, both=True) iterates
``character_registry``. If that sweep regresses (wrong list, wrong predicate,
``both`` ignored), surviving attackers would keep targeting a dead victim and
re-enter combat on the next violence pulse.

See docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md INV-006.
"""

from __future__ import annotations

import pytest

from mud.combat.engine import stop_fighting
from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.models.room import Room
from mud.registry import room_registry


@pytest.fixture(autouse=True)
def _reset_registry():
    snapshot = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(snapshot)


def _mk_room(vnum: int) -> Room:
    room = Room(vnum=vnum, name=f"Room {vnum}", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[vnum] = room
    return room


def _mk_char(name: str, room: Room, *, is_npc: bool) -> Character:
    ch = Character(name=name, level=10, room=room, is_npc=is_npc, hit=100, max_hit=100)
    ch.position = Position.FIGHTING
    room.people.append(ch)
    character_registry.append(ch)
    return ch


def test_stop_fighting_both_clears_all_attackers() -> None:
    room = _mk_room(91001)
    try:
        victim = _mk_char("Victim", room, is_npc=False)
        a1 = _mk_char("Mob1", room, is_npc=True)
        a2 = _mk_char("Mob2", room, is_npc=True)
        a3 = _mk_char("Mob3", room, is_npc=True)
        bystander = _mk_char("Bystander", room, is_npc=True)

        a1.fighting = victim
        a2.fighting = victim
        a3.fighting = victim
        victim.fighting = a1
        bystander.fighting = None  # not in combat

        stop_fighting(victim, both=True)

        assert victim.fighting is None
        assert a1.fighting is None, "attacker a1 still pointed at dead victim"
        assert a2.fighting is None, "attacker a2 still pointed at dead victim"
        assert a3.fighting is None, "attacker a3 still pointed at dead victim"
        assert bystander.fighting is None  # untouched

        # Position handling — NPCs go to default_pos (STANDING for our mobs);
        # the PC victim goes to STANDING.
        assert victim.position == Position.STANDING
        assert a1.position == Position.STANDING
    finally:
        room_registry.pop(91001, None)


def test_stop_fighting_both_false_only_clears_self() -> None:
    """Inverse: both=False must NOT sweep other attackers.

    ROM ref: src/fight.c:stop_fighting(ch, FALSE) only clears ch->fighting.
    """
    room = _mk_room(91002)
    try:
        victim = _mk_char("Victim", room, is_npc=False)
        a1 = _mk_char("Mob1", room, is_npc=True)
        a2 = _mk_char("Mob2", room, is_npc=True)

        a1.fighting = victim
        a2.fighting = victim
        victim.fighting = a1

        stop_fighting(a1, both=False)

        assert a1.fighting is None
        assert a2.fighting is victim, "both=False should not sweep other attackers"
        assert victim.fighting is a1, "both=False should not touch victim's pointer"
    finally:
        room_registry.pop(91002, None)


def test_stop_fighting_npc_with_negative_hp_ends_at_dead_not_default_pos() -> None:
    """Position-ordering sub-contract: ROM src/fight.c:1448-1451.

    stop_fighting sets ``fch->position = IS_NPC ? default_pos : POS_STANDING``
    *then* calls ``update_pos(fch)``.  update_pos overrides the reset for
    negative-HP characters.  If the two steps were swapped (update_pos first,
    then position reset), a mortally-wounded NPC would end at ``default_pos``
    (STANDING) instead of DEAD — the reset would stomp the HP-driven value.

    Discriminating case: NPC with hit=0 (< 1 threshold) in combat.
    default_pos is STANDING; update_pos forces DEAD.  The ordering is correct
    iff the final position is DEAD, not STANDING.
    """
    room = _mk_room(91003)
    try:
        victim = _mk_char("DyingMob", room, is_npc=True)
        attacker = _mk_char("Attacker", room, is_npc=False)

        victim.hit = 0  # NPC: hit < 1 → DEAD in update_pos
        victim.position = Position.FIGHTING
        victim.fighting = attacker
        attacker.fighting = victim

        stop_fighting(victim, both=True)

        assert victim.position == Position.DEAD, (
            "NPC with hit=0 must be DEAD after stop_fighting "
            "(ROM src/fight.c:1448: update_pos runs AFTER position reset, "
            "so the HP-driven position wins over the default_pos reset)"
        )
    finally:
        room_registry.pop(91003, None)


def test_stop_fighting_pc_with_negative_hp_ends_at_incap_not_standing() -> None:
    """Position-ordering sub-contract — PC side (src/fight.c:1448-1451).

    For a PC, stop_fighting resets to POS_STANDING then calls update_pos.
    update_pos at hit=-5 returns POS_INCAP.  If the order were reversed,
    the STANDING reset would overwrite the INCAP value, leaving the PC
    apparently healthy after a losing fight.

    Discriminating case: PC with hit=-5 (-6 < hit <= -3 → INCAP).
    """
    room = _mk_room(91004)
    try:
        pc = _mk_char("PC", room, is_npc=False)
        mob = _mk_char("Mob", room, is_npc=True)

        pc.hit = -5  # PC: -6 < hit <= -3 → INCAP in update_pos
        pc.position = Position.FIGHTING
        pc.fighting = mob
        mob.fighting = pc

        stop_fighting(pc, both=True)

        assert pc.position == Position.INCAP, (
            "PC with hit=-5 must be INCAP after stop_fighting "
            "(ROM src/fight.c:1448: update_pos runs AFTER position reset, "
            "so update_pos's INCAP overrides the initial POS_STANDING reset)"
        )
    finally:
        room_registry.pop(91003, None)
        room_registry.pop(91004, None)
