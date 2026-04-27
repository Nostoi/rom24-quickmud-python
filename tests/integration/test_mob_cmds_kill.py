"""Integration tests for ``do_mpkill`` (MOBprog ``kill`` script command).

ROM C reference: ``src/mob_cmds.c:348-373`` — ROM gates with
``victim == ch || IS_NPC(victim) || ch->position == POS_FIGHTING``.
Python had been checking ``ch->fighting`` (object-truthy) instead of
``ch->position == POS_FIGHTING``, and was missing the self-attack check.

Closes MOBCMD-003.
"""

from __future__ import annotations

import pytest

from mud.mob_cmds import do_mpkill
from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room


@pytest.fixture
def kill_room() -> Room:
    return Room(vnum=9801, name="Kill Test Room")


@pytest.fixture
def script_mob(kill_room: Room) -> Character:
    mob = Character(name="Killer", is_npc=True)
    mob.position = Position.STANDING
    mob.level = 30
    mob.hit = 100
    mob.max_hit = 100
    kill_room.add_character(mob)
    return mob


@pytest.fixture
def victim(kill_room: Room) -> Character:
    target = Character(name="Target", is_npc=False)
    target.position = Position.STANDING
    target.hit = 100
    target.max_hit = 100
    kill_room.add_character(target)
    return target


class TestMpKillPositionGate:
    """MOBCMD-003: ROM blocks via ``ch->position == POS_FIGHTING`` (not
    ``ch->fighting``). Witness via inconsistent state — position FIGHTING
    but fighting=None: ROM refuses, old Python proceeded.
    """

    def test_position_fighting_blocks_even_with_no_fighting_target(
        self, script_mob, victim
    ):
        # Inconsistent state: position FIGHTING but fighting attr None.
        script_mob.position = Position.FIGHTING
        script_mob.fighting = None

        do_mpkill(script_mob, "Target")

        # ROM blocks on position; mob should NOT have engaged.
        assert script_mob.fighting is None, (
            "do_mpkill should refuse when ch.position == FIGHTING (ROM"
            " src/mob_cmds.c:361). Old Python checked ch.fighting which"
            " was None here, so it incorrectly called multi_hit."
        )

    def test_self_attack_refused(self, kill_room):
        # ROM src/mob_cmds.c:361 — `victim == ch` clause must short-circuit
        # before the IS_NPC(victim) check. Witness with is_npc=False so the
        # NPC gate does not also block.
        actor = Character(name="Solo", is_npc=False)
        actor.position = Position.STANDING
        actor.hit = 100
        actor.max_hit = 100
        kill_room.add_character(actor)

        do_mpkill(actor, "Solo")

        # Mob should not be fighting itself.
        assert actor.fighting is not actor, "must not target self"


class TestMpKillCharmedMasterGuard:
    """MOBCMD-001: ROM ``src/mob_cmds.c:364-369`` — when ``ch`` is charmed
    (``IS_AFFECTED(ch, AFF_CHARM)``) and the chosen victim is the charmer
    (``ch->master == victim``), ROM logs a bug and refuses to attack.
    Python had been missing this guard, so a charmed mob scripted to
    ``mob kill <master>`` would attack its own charmer.
    """

    def test_charmed_mob_refuses_to_attack_master(self, script_mob, victim):
        from mud.models.constants import AffectFlag

        # Charm the script mob and bind its master to the prospective victim.
        script_mob.add_affect(AffectFlag.CHARM)
        script_mob.master = victim

        do_mpkill(script_mob, "Target")

        assert script_mob.fighting is None, (
            "do_mpkill must refuse when ch is charmed and ch.master is the"
            " victim (ROM src/mob_cmds.c:364-369)."
        )
