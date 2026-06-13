"""MAGIC-023 — spell_frenzy blocking messages use $N PERS and ROM's $e quirk.

ROM `spell_frenzy` (`src/magic.c`):
  - `act("$N is already in a frenzy.", ch, NULL, victim, TO_CHAR)`               ($N cap)
  - `act("$N doesn't look like $e wants to fight anymore.", ch, NULL, victim, …)` ($e = CASTER's pronoun — a ROM quirk)
  - `act("Your god doesn't seem to like $N", ch, NULL, victim, TO_CHAR)`         (no trailing period)

The Python baked the keyword `name` + literal "they". `$N` = PERS(victim) = NPC
short_descr; `$e` is ROM's `he_she[ch->sex]` (the caster's), which we replicate.
"""

from __future__ import annotations

from mud.models.character import Character, SpellEffect
from mud.models.constants import AffectFlag, Position, Sex
from mud.models.room import Room
from mud.skills.handlers import frenzy


def _caster(room: Room, sex: Sex = Sex.MALE) -> Character:
    c = Character(name="Zealot", level=20, is_npc=False, sex=int(sex), position=int(Position.STANDING))
    c.room = room
    room.people.append(c)
    c.messages = []
    return c


def _goblin(room: Room) -> Character:
    g = Character(
        name="goblin", is_npc=True, short_descr="a green goblin", sex=int(Sex.FEMALE), position=int(Position.STANDING)
    )
    g.room = room
    room.people.append(g)
    g.messages = []
    return g


def test_magic023_frenzy_already_frenzied_uses_pers_shortdescr():
    room = Room(vnum=99170, name="Arena")
    caster = _caster(room)
    goblin = _goblin(room)
    goblin.apply_spell_effect(SpellEffect(name="frenzy", duration=10, level=20))

    assert frenzy(caster, target=goblin) is False
    assert any("A green goblin is already in a frenzy." in m for m in caster.messages), caster.messages


def test_magic023_frenzy_calm_target_replicates_caster_e_pronoun_quirk():
    """ROM's `$e` is the CASTER's subject pronoun — male caster -> "he" (about the goblin)."""
    room = Room(vnum=99171, name="Arena")
    caster = _caster(room, sex=Sex.MALE)
    goblin = _goblin(room)
    goblin.affected_by |= int(AffectFlag.CALM)

    assert frenzy(caster, target=goblin) is False
    # $N = "a green goblin" (cap), $e = caster's "he" (NOT the female goblin's "she").
    assert any("A green goblin doesn't look like he wants to fight anymore." in m for m in caster.messages), (
        caster.messages
    )
