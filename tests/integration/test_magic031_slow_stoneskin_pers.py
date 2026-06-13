"""MAGIC-031 — slow/stone_skin cross-target reject lines use $N PERS (cap).

ROM:
  - `spell_slow`       `src/magic.c:4396` — `act("$N can't get any slower than that.", ch, NULL, victim, TO_CHAR)`
  - `spell_stone_skin` `src/magic.c:4452` — `act("$N is already as hard as can be.", ch, NULL, victim, TO_CHAR)`

Both `$N` = PERS(victim) = NPC short_descr, capitalized. The self-cast legs are
ROM literals ("You can't move any slower!" / "Your skin is already as hard as a
rock.") and were already correct. The Python baked `_character_name`.
"""

from __future__ import annotations

from mud.models.character import Character, SpellEffect
from mud.models.constants import AffectFlag, Position
from mud.models.room import Room
from mud.skills.handlers import slow, stone_skin


def _caster(room: Room) -> Character:
    c = Character(name="Mage", level=30, ch_class=0, is_npc=False, position=int(Position.STANDING))
    room.add_character(c)
    c.messages = []
    return c


def _goblin(room: Room) -> Character:
    g = Character(name="goblin", is_npc=True, short_descr="a green goblin", level=15, position=int(Position.STANDING))
    room.add_character(g)
    g.messages = []
    return g


def test_magic031_slow_already_slowed_npc_uses_pers_cap():
    room = Room(vnum=99202, name="Arena")
    caster = _caster(room)
    goblin = _goblin(room)
    goblin.affected_by |= int(AffectFlag.SLOW)

    assert slow(caster, target=goblin) is False
    assert any("A green goblin can't get any slower than that." in m for m in caster.messages), caster.messages


def test_magic031_stone_skin_already_stoned_npc_uses_pers_cap():
    room = Room(vnum=99203, name="Arena")
    caster = _caster(room)
    goblin = _goblin(room)
    goblin.apply_spell_effect(SpellEffect(name="stone skin", duration=10, level=30))

    assert stone_skin(caster, target=goblin) is False
    assert any("A green goblin is already as hard as can be." in m for m in caster.messages), caster.messages
