"""FIGHT-099 — damage() epilogue: a link-dead PC victim auto-recalls.

ROM src/fight.c:981-991:

    /*
     * Take care of link dead people.
     */
    if (!IS_NPC (victim) && victim->desc == NULL)
    {
        if (number_range (0, victim->wait) == 0)
        {
            do_function (victim, &do_recall, "");
            return TRUE;
        }
    }

After damage lands (victim alive, victim != ch), a PLAYER victim with no
descriptor rolls number_range(0, wait); on 0 it recalls out of the fight
("$n prays for transportation!" → temple). With wait == 0 the roll is
number_range(0, 0) == 0 — the recall attempt ALWAYS fires. Untrained recall
while fighting never fails the skill roll (80 * 0 / 100 == 0 threshold,
src/act_move.c:1599), so the victim lands in ROOM_VNUM_TEMPLE.

Python's apply_damage was missing the whole tail; C-oracle ground truth is
the aggr_two_pc_victim_selection differential scenario (descriptorless Ally
recalls after the first pierce). Surfaced 2026-07-16 by the GL-050 probe.
"""

from __future__ import annotations

import pytest

from mud.combat.engine import apply_damage, set_fighting
from mud.models.constants import ROOM_VNUM_TEMPLE, Position
from mud.world import create_test_character, initialize_world

# NOT the temple (ROOM_VNUM_TEMPLE == 3001) — recall must be an observable move.
_ROOM = 3005


@pytest.fixture(autouse=True)
def _world():
    initialize_world("area/area.lst")


def test_fight099_linkdead_pc_victim_recalls_after_damage() -> None:
    """mirrors ROM src/fight.c:984-991 — desc==NULL PC victim with wait 0
    always attempts recall after taking damage, landing in the temple."""
    victim = create_test_character("LinkDead", _ROOM)
    victim.is_npc = False
    victim.level = 10
    victim.max_hit = 200
    victim.hit = 200
    victim.desc = None
    victim.wait = 0

    attacker = create_test_character("Mauler", _ROOM)
    attacker.is_npc = True
    attacker.level = 10
    set_fighting(attacker, victim)

    apply_damage(attacker, victim, 20)

    assert victim.hit == 180, "damage must land before the epilogue"
    assert victim.room is not None and victim.room.vnum == ROOM_VNUM_TEMPLE, (
        "a link-dead PC victim (desc==NULL, wait 0) must auto-recall to the "
        f"temple after damage (ROM src/fight.c:984-991); ended in {getattr(victim.room, 'vnum', None)}"
    )


def test_fight099_connected_pc_victim_does_not_recall() -> None:
    """A victim WITH a descriptor never enters the link-dead branch."""
    victim = create_test_character("Connected", _ROOM)
    victim.is_npc = False
    victim.level = 10
    victim.max_hit = 200
    victim.hit = 200
    victim.desc = object()  # any live descriptor
    victim.wait = 0

    attacker = create_test_character("Mauler2", _ROOM)
    attacker.is_npc = True
    attacker.level = 10
    set_fighting(attacker, victim)

    apply_damage(attacker, victim, 20)

    assert victim.room is not None and victim.room.vnum == _ROOM, (
        f"a connected PC must stay put (ROM gate victim->desc == NULL); ended in {getattr(victim.room, 'vnum', None)}"
    )


def test_fight099_npc_victim_does_not_recall() -> None:
    """NPC victims are excluded by the !IS_NPC(victim) gate."""
    victim = create_test_character("MobVictim", _ROOM)
    victim.is_npc = True
    victim.level = 10
    victim.max_hit = 200
    victim.hit = 200
    victim.desc = None
    victim.wait = 0

    attacker = create_test_character("Mauler3", _ROOM)
    attacker.is_npc = True
    attacker.level = 10
    set_fighting(attacker, victim)

    apply_damage(attacker, victim, 20)

    assert victim.room is not None and victim.room.vnum == _ROOM, (
        f"an NPC victim must never auto-recall (ROM !IS_NPC gate); ended in {getattr(victim.room, 'vnum', None)}"
    )


def test_fight099_self_damage_skips_the_epilogue() -> None:
    """ROM src/fight.c:978-979 — `if (victim == ch) return TRUE;` guards the
    tail: self-damage never triggers the link-dead recall."""
    victim = create_test_character("SelfHarm", _ROOM)
    victim.is_npc = False
    victim.level = 10
    victim.max_hit = 200
    victim.hit = 200
    victim.desc = None
    victim.wait = 0
    victim.position = Position.STANDING

    apply_damage(victim, victim, 20)

    assert victim.room is not None and victim.room.vnum == _ROOM, (
        f"self-damage must skip the link-dead tail (ROM victim==ch guard); ended in {getattr(victim.room, 'vnum', None)}"
    )
