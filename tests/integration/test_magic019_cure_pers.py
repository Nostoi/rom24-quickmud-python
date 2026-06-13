"""MAGIC-019 — cure_blindness/disease/poison "doesn't appear to be …" use PERS.

ROM (`src/magic.c:1608/1650/1694`): when the victim isn't affected and is not the
caster, `act("$N doesn't appear to be blinded/diseased/poisoned.", ch, NULL,
victim, TO_CHAR)`. `$N` = PERS(victim) = the NPC short_descr, capitalized. The
Python cure handlers baked the keyword `name`.
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room
from mud.skills.handlers import cure_blindness, cure_disease, cure_poison


def _caster(room: Room) -> Character:
    c = Character(name="Cleric", level=20, ch_class=1, is_npc=False, position=int(Position.STANDING))
    c.room = room
    room.people.append(c)
    c.messages = []
    return c


def _goblin(room: Room) -> Character:
    g = Character(name="goblin", is_npc=True, short_descr="a green goblin", level=10, position=int(Position.STANDING))
    g.room = room
    room.people.append(g)
    g.messages = []
    return g


def test_magic019_cure_blindness_not_affected_uses_pers_shortdescr():
    room = Room(vnum=99140, name="Chapel")  # default sector 0 = INSIDE (lit)
    caster = _caster(room)
    goblin = _goblin(room)  # not blind

    cure_blindness(caster, target=goblin)

    assert any("A green goblin doesn't appear to be blinded." in m for m in caster.messages), caster.messages


def test_magic019_cure_disease_not_affected_uses_pers_shortdescr():
    room = Room(vnum=99141, name="Chapel")
    caster = _caster(room)
    goblin = _goblin(room)

    cure_disease(caster, target=goblin)

    assert any("A green goblin doesn't appear to be diseased." in m for m in caster.messages), caster.messages


def test_magic019_cure_poison_not_affected_uses_pers_shortdescr():
    room = Room(vnum=99142, name="Chapel")
    caster = _caster(room)
    goblin = _goblin(room)

    cure_poison(caster, target=goblin)

    assert any("A green goblin doesn't appear to be poisoned." in m for m in caster.messages), caster.messages
