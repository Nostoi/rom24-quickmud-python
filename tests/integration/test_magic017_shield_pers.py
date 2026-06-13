"""MAGIC-017 — spell_shield TO_CHAR/TO_ROOM lines use PERS, not baked name.

ROM `spell_shield` (`src/magic.c`):
  - already-affected cross-target: `act("$N is already protected by a shield.", ch, NULL, victim, TO_CHAR)`
  - success room:                  `act("$n is surrounded by a force shield.", victim, NULL, NULL, TO_ROOM)`

`$N`/`$n` = `PERS(victim, looker)` = the NPC short_descr (capitalized buf[0]); an
invisible victim masks to "Someone". The Python `shield` handler baked the keyword
`name` (TO_CHAR) and used a hand-rolled room loop baking `target.name` (TO_ROOM).
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


def _mage(name: str, room: Room) -> Character:
    char = Character(
        name=name,
        level=20,
        ch_class=0,
        is_npc=False,
        perm_stat=[0, 18, 0, 0, 0],
        mana=200,
        position=int(Position.STANDING),
        skills={"shield": 100},
        armor=[100, 100, 100, 100],
    )
    char.room = room
    room.people.append(char)
    char.messages = []
    return char


def _goblin(room: Room) -> Character:
    g = Character(
        name="goblin",
        is_npc=True,
        short_descr="a green goblin",
        level=10,
        position=int(Position.STANDING),
        armor=[100, 100, 100, 100],
    )
    g.room = room
    room.people.append(g)
    g.messages = []
    return g


def test_magic017_shield_room_broadcast_uses_pers_shortdescr():
    """TO_ROOM: an observer sees the victim's PERS short_descr, capitalized."""
    room = Room(vnum=99120, name="Arena")  # default sector 0 = INSIDE (lit)
    caster = _mage("Caster", room)
    _goblin(room)  # the cast target; resolved by name
    observer = _mage("Watcher", room)

    rng_mm.seed_mm(42)
    do_cast(caster, "shield goblin")

    assert any("A green goblin is surrounded by a force shield." in m for m in observer.messages), observer.messages


def test_magic017_shield_already_protected_uses_pers_shortdescr():
    """TO_CHAR already-affected: caster sees "A green goblin is already protected by a shield."."""
    room = Room(vnum=99121, name="Arena")
    caster = _mage("Caster", room)
    goblin = _goblin(room)
    goblin.apply_spell_effect(SpellEffect(name="shield", duration=8, level=10, ac_mod=-20))

    rng_mm.seed_mm(42)
    do_cast(caster, "shield goblin")

    assert any("A green goblin is already protected by a shield." in m for m in caster.messages), caster.messages
