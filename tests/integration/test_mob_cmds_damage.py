"""Integration tests for ``do_mpdamage`` (MOBprog ``damage`` script command).

ROM C reference: ``src/mob_cmds.c:1078-1147`` — ROM ``do_mpdamage`` calls
``damage(victim, victim, ...)`` so the canonical death/position/fight pipeline
runs. Python had been raw-decrementing ``victim.hit`` which skipped position
updates, fight triggers, and death handling.

Closes MOBCMD-014.
"""

from __future__ import annotations

import pytest

from mud.mob_cmds import do_mpdamage
from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room


@pytest.fixture
def damage_room() -> Room:
    return Room(vnum=9001, name="Damage Test Room")


@pytest.fixture
def script_mob(damage_room: Room) -> Character:
    mob = Character(name="ScriptMob", is_npc=True)
    mob.position = Position.STANDING
    damage_room.add_character(mob)
    return mob


@pytest.fixture
def victim(damage_room: Room) -> Character:
    target = Character(name="Victim", is_npc=False)
    target.position = Position.STANDING
    target.hit = 50
    target.max_hit = 100
    damage_room.add_character(target)
    return target


class TestMpDamageCallsDamagePipeline:
    """MOBCMD-014: ``do_mpdamage`` must route through the canonical damage
    function (``apply_damage``) so death + position updates run, mirroring
    ROM ``src/mob_cmds.c:1132-1145`` which calls
    ``damage(victim, victim, amount, TYPE_UNDEFINED, DAM_NONE, FALSE)``.
    """

    def test_lethal_kill_runs_damage_pipeline(self, script_mob, victim):
        """A lethal ``mpdamage <victim> <high> <high> kill`` must route through
        ``apply_damage`` so the death + position-update pipeline runs.

        The previous implementation did a raw ``victim.hit = max(0, hit - amount)``
        which left ``victim.position`` untouched at STANDING (and never fired
        ``raw_kill``, ``mp_death_trigger``, or ``update_pos``). The canonical
        pipeline (``apply_damage`` → ``update_pos`` → ``_handle_death`` →
        ``raw_kill``) ends a lethally-hit PC in a post-death state (RESTING in
        the resurrection room).
        """
        do_mpdamage(script_mob, "Victim 1000 1000 kill")

        # Witness: position must transition out of STANDING. Old implementation
        # never touched position; new pipeline drives it through update_pos and
        # the PC resurrection flow.
        assert victim.position != Position.STANDING, (
            f"victim.position={victim.position!r}; expected a post-damage"
            " position (DEAD/RESTING/etc.). Old implementation left position"
            " untouched at STANDING because it bypassed apply_damage()."
        )

    def test_safe_form_caps_at_current_hit(self, script_mob, victim):
        """Without the kill flag, ROM caps damage at ``victim->hit``
        (``UMIN(victim->hit, number_range(low, high))`` per
        ``src/mob_cmds.c:1134``) so the victim's HP cannot go below zero."""
        victim.hit = 30
        do_mpdamage(script_mob, "Victim 1000 1000")

        # ROM ensures damage <= victim.hit, so post-damage hit cannot be
        # strictly negative for a previously-positive victim.
        assert victim.hit >= 0, f"safe-form mpdamage drove hit to {victim.hit}; ROM caps at victim->hit."


class TestMpDamageNonNumericArgsBugLog:
    """MOBCMD-013: ROM ``src/mob_cmds.c:1101-1116`` calls ``bug(...)`` and
    returns when the min or max argument is not numeric. Python silently
    returned, swallowing what is a script authoring error.
    """

    def test_non_numeric_min_emits_bug_log(self, script_mob, victim, caplog):
        import logging

        with caplog.at_level(logging.WARNING, logger="mud.mob_cmds"):
            do_mpdamage(script_mob, "Victim notanumber 100")

        assert any(
            "MpDamage" in record.message and "min" in record.message.lower()
            for record in caplog.records
        ), (
            f"expected an MpDamage bug log for the non-numeric min arg; got"
            f" {[r.message for r in caplog.records]!r}. ROM"
            " src/mob_cmds.c:1105-1107 calls bug() and returns."
        )
        assert victim.hit == 50, "non-numeric min must abort before damage"

    def test_non_numeric_max_emits_bug_log(self, script_mob, victim, caplog):
        import logging

        with caplog.at_level(logging.WARNING, logger="mud.mob_cmds"):
            do_mpdamage(script_mob, "Victim 10 notanumber")

        assert any(
            "MpDamage" in record.message and "max" in record.message.lower()
            for record in caplog.records
        ), (
            f"expected an MpDamage bug log for the non-numeric max arg; got"
            f" {[r.message for r in caplog.records]!r}. ROM"
            " src/mob_cmds.c:1113-1115 calls bug() and returns."
        )
        assert victim.hit == 50, "non-numeric max must abort before damage"
