"""FIGHT-065 — disarm "no weapon" message is ROM's literal, not a baked name.

ROM `do_disarm` (`src/fight.c:3175`): when the victim has no wielded weapon,
`send_to_char("Your opponent is not wielding a weapon.\n\r", ch)` — a LITERAL
string, not `act("$N …")`. The `handlers.py:disarm` skill handler (the path
`mob_hit`/`_mob_offensive_skill` dispatches) baked `_character_name(victim)`,
producing "goblin is not wielding a weapon." vs ROM "Your opponent is not
wielding a weapon." (The player command `combat.py:do_disarm` was already
correct; this is the duplicate skill-handler path.)
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room
from mud.skills.handlers import disarm


def _char(room: Room, name: str, is_npc: bool, short: str | None = None) -> Character:
    c = Character(name=name, is_npc=is_npc, short_descr=short, position=int(Position.FIGHTING))
    c.room = room
    room.people.append(c)
    c.messages = []
    return c


def test_fight065_disarm_unarmed_victim_uses_rom_literal():
    room = Room(vnum=99195, name="Arena")
    caster = _char(room, "Mage", is_npc=False)
    goblin = _char(room, "goblin", is_npc=True, short="a green goblin")
    # goblin wields nothing -> get_wielded_weapon(goblin) is None

    assert disarm(caster, target=goblin) is False
    assert any("Your opponent is not wielding a weapon." in m for m in caster.messages), caster.messages
    # And it must NOT bake the victim's keyword / short_descr.
    assert not any("goblin is not wielding" in m for m in caster.messages), caster.messages
