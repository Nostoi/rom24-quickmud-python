"""Integration tests for ``do_mpassist`` (MOBprog ``assist`` script command).

ROM C reference: ``src/mob_cmds.c:380-398`` — ROM gates with
``victim == ch || ch->fighting != NULL || victim->fighting == NULL``.
Python had only checked the third clause (``ally->fighting`` resolves to
``None`` and the function returns), so a script mob already in combat
could be told to assist someone else and would re-engage with the new
opponent, and a script mob could even be told to assist itself.

Closes MOBCMD-002.
"""

from __future__ import annotations

import pytest

from mud.mob_cmds import do_mpassist
from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room


@pytest.fixture
def assist_room() -> Room:
    return Room(vnum=9810, name="Assist Test Room")


@pytest.fixture
def script_mob(assist_room: Room) -> Character:
    mob = Character(name="Helper", is_npc=True)
    mob.position = Position.STANDING
    mob.level = 30
    mob.hit = 100
    mob.max_hit = 100
    assist_room.add_character(mob)
    return mob


@pytest.fixture
def ally(assist_room: Room) -> Character:
    other = Character(name="Ally", is_npc=False)
    other.position = Position.FIGHTING
    other.hit = 100
    other.max_hit = 100
    assist_room.add_character(other)
    return other


@pytest.fixture
def opponent(assist_room: Room) -> Character:
    foe = Character(name="Foe", is_npc=True)
    foe.position = Position.FIGHTING
    foe.hit = 100
    foe.max_hit = 100
    assist_room.add_character(foe)
    return foe


class TestMpAssistRomGates:
    """MOBCMD-002: ``do_mpassist`` must enforce all three ROM gates from
    ``src/mob_cmds.c:393``: ``victim == ch``, ``ch->fighting != NULL``,
    and ``victim->fighting == NULL``."""

    def test_already_fighting_mob_does_not_call_multi_hit(
        self, monkeypatch, script_mob, ally, opponent, assist_room
    ):
        # script_mob is already fighting an existing enemy; assisting an ally
        # in another fight must not call multi_hit at all (ROM gates before
        # multi_hit on `ch->fighting != NULL`).
        existing = Character(name="Existing", is_npc=True)
        existing.position = Position.FIGHTING
        existing.hit = 100
        existing.max_hit = 100
        assist_room.add_character(existing)

        script_mob.position = Position.FIGHTING
        script_mob.fighting = existing
        ally.fighting = opponent

        invocations: list[tuple] = []
        from mud import combat

        def fake_multi_hit(*args, **kwargs):
            invocations.append((args, kwargs))

        monkeypatch.setattr(combat, "multi_hit", fake_multi_hit)

        do_mpassist(script_mob, "Ally")

        assert invocations == [], (
            "do_mpassist invoked multi_hit despite ch already fighting"
            " (ROM src/mob_cmds.c:393, `ch->fighting != NULL`)."
        )

    def test_self_assist_does_not_call_multi_hit(
        self, monkeypatch, script_mob, opponent
    ):
        # ROM src/mob_cmds.c:393 — `victim == ch` must short-circuit before
        # multi_hit. Even if "self" is in a fight (opponent fighting us, so
        # ally->fighting is non-NULL), self-assist must refuse.
        script_mob.fighting = opponent
        opponent.fighting = script_mob

        invocations: list[tuple] = []
        from mud import combat

        def fake_multi_hit(*args, **kwargs):
            invocations.append((args, kwargs))

        monkeypatch.setattr(combat, "multi_hit", fake_multi_hit)

        do_mpassist(script_mob, "Helper")

        assert invocations == [], (
            "do_mpassist invoked multi_hit on a self-assist (ROM"
            " src/mob_cmds.c:393, `victim == ch`)."
        )
