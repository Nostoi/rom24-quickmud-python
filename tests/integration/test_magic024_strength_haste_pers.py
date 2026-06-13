"""MAGIC-024 — giant_strength/haste blocking messages use $N/$E PERS.

ROM:
  - `spell_giant_strength`: `act("$N can't get any stronger.", ch, NULL, victim, TO_CHAR)` ($N cap)
  - `spell_haste`:          `act("$N is already moving as fast as $E can.", ch, NULL, victim, TO_CHAR)`
    ($N PERS short_descr + $E = the VICTIM's subject pronoun — correct uppercase $E)

The Python baked the keyword `name` + literal "they".
"""

from __future__ import annotations

from mud.models.character import Character, SpellEffect
from mud.models.constants import AffectFlag, Position, Sex
from mud.models.room import Room
from mud.skills.handlers import giant_strength, haste


def _caster(room: Room) -> Character:
    c = Character(name="Mage", level=20, ch_class=0, is_npc=False, position=int(Position.STANDING))
    c.room = room
    room.people.append(c)
    c.messages = []
    return c


def _goblin(room: Room, sex: Sex = Sex.FEMALE) -> Character:
    g = Character(
        name="goblin", is_npc=True, short_descr="a green goblin", sex=int(sex), position=int(Position.STANDING)
    )
    g.room = room
    room.people.append(g)
    g.messages = []
    return g


def test_magic024_giant_strength_already_strong_uses_pers_shortdescr():
    room = Room(vnum=99180, name="Arena")
    caster = _caster(room)
    goblin = _goblin(room)
    goblin.apply_spell_effect(SpellEffect(name="giant strength", duration=10, level=20))

    assert giant_strength(caster, target=goblin) is False
    assert any("A green goblin can't get any stronger." in m for m in caster.messages), caster.messages


def test_magic024_haste_already_hasted_uses_pers_and_victim_E_pronoun():
    """$E is the VICTIM's subject pronoun — a female goblin -> "she"."""
    room = Room(vnum=99181, name="Arena")
    caster = _caster(room)
    goblin = _goblin(room, sex=Sex.FEMALE)
    goblin.affected_by |= int(AffectFlag.HASTE)

    assert haste(caster, target=goblin) is False
    assert any("A green goblin is already moving as fast as she can." in m for m in caster.messages), caster.messages
