"""MAGIC-018 — spell_bless TO_CHAR lines use the victim's PERS short_descr.

ROM `spell_bless` (`src/magic.c`):
  - already-affected cross-target: `act("$N already has divine favor.", ch, NULL, victim, TO_CHAR)` ($N at start -> cap)
  - success cross-target:          `act("You grant $N the favor of your god.", ch, NULL, victim, TO_CHAR)` ($N mid-sentence)

`$N` = `PERS(victim)` = the NPC short_descr; the Python `bless` handler baked the
keyword `name`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mud.commands.combat import do_cast
from mud.models.character import Character, SpellEffect
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


def _priest(name: str, room: Room) -> Character:
    char = Character(
        name=name,
        level=20,
        ch_class=1,
        is_npc=False,
        perm_stat=[0, 0, 18, 0, 0],
        mana=200,
        position=int(Position.STANDING),
        skills={"bless": 100},
    )
    char.room = room
    room.people.append(char)
    char.messages = []
    return char


def _goblin(room: Room) -> Character:
    g = Character(name="goblin", is_npc=True, short_descr="a green goblin", level=10, position=int(Position.STANDING))
    g.room = room
    room.people.append(g)
    g.messages = []
    return g


def test_magic018_bless_success_cross_target_uses_pers_shortdescr():
    """ROM act("You grant $N the favor of your god.", …) — $N -> short_descr."""
    room = Room(vnum=99130, name="Chapel")
    caster = _priest("Priest", room)
    _goblin(room)

    rng_mm.seed_mm(42)
    do_cast(caster, "bless goblin")

    assert any("You grant a green goblin the favor of your god." in m for m in caster.messages), caster.messages


def test_magic018_bless_already_blessed_uses_pers_shortdescr_capitalized():
    """ROM act("$N already has divine favor.", …) — $N at start -> "A green goblin …"."""
    room = Room(vnum=99131, name="Chapel")
    caster = _priest("Priest", room)
    goblin = _goblin(room)
    goblin.apply_spell_effect(SpellEffect(name="bless", duration=6, level=10, hitroll_mod=1, saving_throw_mod=-1))

    rng_mm.seed_mm(42)
    do_cast(caster, "bless goblin")

    assert any("A green goblin already has divine favor." in m for m in caster.messages), caster.messages
