"""Regression for FINDING-013 (differential `spell_combat` scenario, 2026-05-29).

ROM `do_cast` (`src/magic.c:553-563`) sends nothing to the player on a
*successful* cast — it deducts mana, calls the spell function, and `check_improve`;
the only player-facing output is whatever the spell function itself sends. Python's
`do_cast` returned `f"You cast {skill.name}."`, a confirmation line ROM never
produces, so the player saw an extra line above the spell's own message.

Surfaced by the `spell_combat` differential scenario, step 5:
  C : ['Your magic missile maims the drunk.']
  py: ['You cast magic missile.', 'Your magic missile maims the drunk.']

ROM C: src/magic.c:553-563 (do_cast success path — no send_to_char).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mud.commands.combat import do_cast
from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room
from mud.skills.registry import load_skills, skill_registry
from mud.utils import rng_mm


@pytest.fixture(autouse=True)
def _load_skills():
    skill_registry.skills.clear()
    skill_registry.handlers.clear()
    load_skills(Path("data/skills.json"))
    yield
    skill_registry.skills.clear()
    skill_registry.handlers.clear()


def test_do_cast_is_silent_on_success_like_rom():
    room = Room(vnum=99100, name="Arena")
    caster = Character(
        name="Tester",
        level=20,
        ch_class=0,
        is_npc=False,
        perm_stat=[0, 18, 0, 0, 0],
        mana=200,
        position=int(Position.STANDING),
        skills={"magic missile": 100},
    )
    victim = Character(name="Fido", level=20, ch_class=0, is_npc=True, hit=200, max_hit=200)
    caster.room = room
    victim.room = room
    room.people.extend([caster, victim])
    caster.messages = []

    rng_mm.seed_mm(42)
    result = do_cast(caster, "'magic missile' Fido")

    # ROM is silent on a successful cast — no "You cast <spell>." confirmation.
    assert result == ""
    # The spell's own message is delivered to the caster via char.messages,
    # exactly as ROM's spell_fun -> damage() sends it (one line, not two).
    assert any("magic missile" in m for m in caster.messages), caster.messages
    assert victim.hit < 200, "the offensive spell must still damage the target"
