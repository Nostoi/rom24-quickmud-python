"""MAGIC-022 — protection_from_evil/good messages use the victim's PERS short_descr.

ROM `spell_protection_evil`/`_good` (`src/magic.c`): the cross-target lines
`act("$N is already protected.", …, TO_CHAR)` and `act("$N is protected from
evil/good.", …, TO_CHAR)` render `$N` = PERS(victim) = NPC short_descr,
capitalized. The Python handlers baked the keyword `name`.
"""

from __future__ import annotations

from mud.models.character import Character, SpellEffect
from mud.models.constants import Position
from mud.models.room import Room
from mud.skills.handlers import protection_evil, protection_good


def _caster(room: Room) -> Character:
    c = Character(name="Priest", level=20, is_npc=False, position=int(Position.STANDING))
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


def test_magic022_protection_evil_success_uses_pers_shortdescr():
    room = Room(vnum=99160, name="Chapel")  # default sector 0 = INSIDE (lit)
    caster = _caster(room)
    goblin = _goblin(room)

    assert protection_evil(caster, target=goblin) is True
    assert any("A green goblin is protected from evil." in m for m in caster.messages), caster.messages


def test_magic022_protection_good_already_protected_uses_pers_shortdescr():
    room = Room(vnum=99161, name="Chapel")
    caster = _caster(room)
    goblin = _goblin(room)
    goblin.apply_spell_effect(SpellEffect(name="protection good", duration=24, level=10))

    assert protection_good(caster, target=goblin) is False
    assert any("A green goblin is already protected." in m for m in caster.messages), caster.messages
