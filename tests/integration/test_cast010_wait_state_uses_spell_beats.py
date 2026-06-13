"""CAST-010 — do_cast WAIT_STATE uses the spell's beats, not a flat PULSE_VIOLENCE.

ROM ``do_cast`` (``src/magic.c:547``) applies ``WAIT_STATE(ch, skill_table[sn].beats)``
— the *per-spell* cast lag — before the success roll. Spell beats vary: most are 12,
but ~34 spells differ (fly=18, enchant armor=24, mass healing=36, …) and 19 are 0.
The Python ``mud/commands/combat.py:do_cast`` applied a flat
``get_pulse_violence()`` (== 12) for every spell, so any spell whose beats ≠ 12
got the wrong cast lag (and beats-0 spells were over-lagged). ROM uses the *raw*
beats — no HASTE/SLOW adjustment for casting — so the fix reads ``skill.beats``
directly via the canonical UMAX helper.
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


def test_cast_wait_state_equals_spell_beats_not_pulse_violence():
    """ROM src/magic.c:547 — WAIT_STATE(ch, skill_table[sn].beats); fly beats == 18."""
    fly = skill_registry.skills.get("fly")
    assert fly is not None
    beats = int(getattr(fly, "beats", 0) or 0)
    assert beats == 18, f"test premise: fly beats should be 18, got {beats}"

    room = Room(vnum=99200, name="Arena")
    caster = Character(
        name="Mage",
        level=60,
        ch_class=0,
        is_npc=False,
        perm_stat=[0, 18, 0, 0, 0],
        mana=500,
        position=int(Position.STANDING),
        skills={"fly": 90},
    )
    caster.room = room
    room.people.append(caster)
    caster.messages = []
    caster.wait = 0

    rng_mm.seed_mm(12345)
    do_cast(caster, "fly")

    # ROM applies the spell's own beats (18), not a flat PULSE_VIOLENCE (12).
    assert caster.wait == beats == 18, f"expected cast wait == fly beats (18), got {caster.wait}"
