"""FIGHT-094 — damage() itself calls check_killer (ROM src/fight.c:733).

ROM's damage() pre-application block (victim != ch):

    if (is_safe (ch, victim))
        return FALSE;
    check_killer (ch, victim);           /* fight.c:733 */
    ... set_fighting (victim, ch) ... set_fighting (ch, victim) ...

The ORDER is load-bearing: check_killer early-outs when
``ch->fighting == victim`` (fight.c:1278), so the damage()-layer call is the
one that actually SETS the KILLER flag on the FIRST hit of a PvP engagement
(fighting still NULL). Python called check_killer only from the command layer
(do_kill/bash/trip/… tails), so any first-hit damage path not routed through
one of those verbs never PK-flagged the attacker. ROM double-calls (command
layer AND damage()) — check_killer's own guards make that idempotent, so
adding the damage() call exactly mirrors ROM.
"""

from __future__ import annotations

import pytest

from mud.combat.engine import apply_damage
from mud.models.character import Character
from mud.models.constants import PlayerFlag, Position
from mud.world import create_test_character, initialize_world

_ROOM = 3001


@pytest.fixture(autouse=True)
def _world():
    initialize_world("area/area.lst")


def _pvp_pair() -> tuple[Character, Character]:
    attacker = create_test_character("Rogue", _ROOM)
    attacker.is_npc = False
    attacker.level = 20
    attacker.clan = 1  # is_clan gate (fight.c:1277) + is_safe PvP clan ladder
    attacker.desc = object()
    attacker.hit = 500
    attacker.max_hit = 500

    victim = create_test_character("Mark", _ROOM)
    victim.is_npc = False
    victim.level = 20
    victim.clan = 1
    victim.desc = object()
    victim.hit = 500
    victim.max_hit = 500
    victim.position = int(Position.STANDING)
    return attacker, victim


def test_fight094_first_hit_through_damage_sets_killer_flag() -> None:
    """mirrors ROM src/fight.c:733 — check_killer runs inside damage() BEFORE
    set_fighting, so the first PvP hit flags the attacker even when no
    command-layer check_killer ran."""
    attacker, victim = _pvp_pair()
    assert attacker.fighting is None

    apply_damage(attacker, victim, 10)

    assert int(getattr(attacker, "act", 0) or 0) & int(PlayerFlag.KILLER), (
        "damage() must check_killer before set_fighting (ROM src/fight.c:733) — "
        "the first PvP hit through any damage path PK-flags the attacker"
    )


def test_fight094_established_fight_does_not_reflag() -> None:
    """mirrors ROM src/fight.c:1278 — `ch->fighting == victim` early-out: once
    the fight is established, further hits never (re)flag."""
    attacker, victim = _pvp_pair()
    attacker.fighting = victim
    attacker.position = int(Position.FIGHTING)

    apply_damage(attacker, victim, 10)

    assert not int(getattr(attacker, "act", 0) or 0) & int(PlayerFlag.KILLER), (
        "an established fight (attacker.fighting is victim) must not flag "
        "(ROM check_killer early-out, src/fight.c:1278)"
    )


def test_fight094_npc_victim_never_flags() -> None:
    """mirrors ROM src/fight.c:1240 — NPCs are fair game."""
    attacker, _ = _pvp_pair()
    mob = create_test_character("Slime", _ROOM)
    mob.is_npc = True
    mob.level = 10
    mob.hit = 500
    mob.max_hit = 500

    apply_damage(attacker, mob, 10)

    assert not int(getattr(attacker, "act", 0) or 0) & int(PlayerFlag.KILLER)
