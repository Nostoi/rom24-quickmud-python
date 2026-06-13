"""MAGIC-025 — fly/infravision/pass_door already-affected lines use $N PERS.

ROM (`src/magic.c:2892/3594/3874`): `act("$N doesn't need your help to fly.", …)`,
`act("$N already has infravision.", …)`, `act("$N is already shifted out of phase.",
…)` — all TO_CHAR with `$N` = PERS(victim) = NPC short_descr, capitalized. The
Python baked the keyword `name`.
"""

from __future__ import annotations

from mud.models.character import Character, SpellEffect
from mud.models.constants import AffectFlag, Position
from mud.models.room import Room
from mud.skills.handlers import fly, infravision, pass_door


def _caster(room: Room) -> Character:
    c = Character(name="Mage", level=20, ch_class=0, is_npc=False, position=int(Position.STANDING))
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


def test_magic025_fly_already_flying_uses_pers_shortdescr():
    room = Room(vnum=99190, name="Arena")
    caster = _caster(room)
    goblin = _goblin(room)
    goblin.affected_by |= int(AffectFlag.FLYING)

    fly(caster, target=goblin)
    assert any("A green goblin doesn't need your help to fly." in m for m in caster.messages), caster.messages


def test_magic025_infravision_already_has_uses_pers_shortdescr():
    room = Room(vnum=99191, name="Arena")
    caster = _caster(room)
    goblin = _goblin(room)
    goblin.apply_spell_effect(SpellEffect(name="infravision", duration=10, level=20))

    infravision(caster, target=goblin)
    assert any("A green goblin already has infravision." in m for m in caster.messages), caster.messages


def test_magic025_pass_door_already_phased_uses_pers_shortdescr():
    room = Room(vnum=99192, name="Arena")
    caster = _caster(room)
    goblin = _goblin(room)
    goblin.apply_spell_effect(SpellEffect(name="pass door", duration=10, level=20))

    pass_door(caster, target=goblin)
    assert any("A green goblin is already shifted out of phase." in m for m in caster.messages), caster.messages
