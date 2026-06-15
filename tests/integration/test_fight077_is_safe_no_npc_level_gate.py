"""FIGHT-077 — is_safe carried a fabricated NPC-attacker level gate.

mud/combat/safety.py:is_safe had, in the NPC-attacking-PC branch:

    char_level = getattr(char, "level", 1)
    victim_level = getattr(victim, "level", 1)
    if victim_level < char_level - 10:
        return True

ROM src/fight.c:1075-1093 ("NPC doing the killing") has NO such gate. The
"killing players" / IS_NPC(ch) branch contains exactly two guards:

    /* safe room check */
    if (IS_SET(victim->in_room->room_flags, ROOM_SAFE)) ... return TRUE;
    /* charmed mobs and pets cannot attack players while owned */
    if (IS_AFFECTED(ch, AFF_CHARM) && ch->master != NULL
            && ch->master->fighting != victim) ... return TRUE;

There is no level-difference check anywhere in is_safe for an NPC attacking a
player. The fabricated gate made any mob more than 10 levels above a player
"safe" — so aggressive mobs silently refused to attack low-level PCs, and
apply_damage (which re-checks is_safe at entry, ROM src/fight.c:731) returned
"" with no damage and no fighting state. Reproduced live: Eddol (level 1) vs
the Cave Dweller (level 13) in room 2316 — is_safe(mob, Eddol) == True.

This is the missed level-gate facet of INV-050 (silent is_safe over-block); the
faithful message-returning mirror _kill_safety_message in mud/commands/combat.py
already correctly omits any level gate.
"""

from __future__ import annotations

import pytest

from mud.combat.safety import is_safe
from mud.models.character import Character
from mud.models.constants import ActFlag
from mud.world import create_test_character, initialize_world

_ROOM = 2300  # non-safe room in area.lst


@pytest.fixture(autouse=True)
def _world():
    initialize_world("area/area.lst")


def _make_pc(name: str, level: int) -> Character:
    ch = create_test_character(name, _ROOM)
    ch.is_npc = False
    ch.level = level
    ch.act = 0
    ch.affected_by = 0
    ch.master = None
    ch.fighting = None
    return ch


def _make_npc(name: str, level: int) -> Character:
    ch = create_test_character(name, _ROOM)
    ch.is_npc = True
    ch.level = level
    ch.act = int(ActFlag.IS_NPC | ActFlag.AGGRESSIVE)
    ch.affected_by = 0
    ch.master = None
    ch.fighting = None
    return ch


def test_fight077_high_level_npc_can_attack_low_level_pc() -> None:
    # mirrors ROM src/fight.c:1075-1093 — the NPC-attacking-PC branch has NO
    # level-difference gate. A level-13 mob attacking a level-1 PC is NOT safe.
    mob = _make_npc("Cave Dweller", level=13)
    victim = _make_pc("Eddol", level=1)

    result = is_safe(mob, victim)

    assert result is False, (
        f"is_safe must return False (not safe) for a high-level NPC attacking a "
        f"much lower-level PC; got {result!r}. ROM src/fight.c:1075-1093 has no "
        "level-difference gate for NPC-attacking-PC — only safe-room and charmed-pet."
    )


def test_fight077_extreme_level_gap_npc_still_not_safe() -> None:
    # The fabricated gate fired whenever victim_level < char_level - 10. Confirm
    # even an enormous gap (level-50 mob vs level-1 PC) is not safe in ROM.
    mob = _make_npc("Ancient Dragon", level=50)
    victim = _make_pc("Newbie", level=1)

    assert is_safe(mob, victim) is False, (
        "ROM imposes no level cap on NPC aggression against players; a level-50 "
        "mob attacking a level-1 PC must not be 'safe'."
    )
