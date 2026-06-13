"""MAGIC-021 — spell_change_sex already-changed line replicates ROM's $s(?) quirk.

ROM `spell_change_sex` (`src/magic.c:1321`):
    act ("$N has already had $s(?) sex changed.", ch, NULL, victim, TO_CHAR);

ROM's `$s` is the CASTER's possessive (a likely ROM bug — grammatically it should
be the victim's `$S`), which the author flagged with the literal "(?)". Per the
parity rule "replicate ROM quirks exactly", the Python must render `$N` =
PERS(victim) (capitalized), `$s` = the CASTER's possessive, and the literal "(?)".
The Python previously baked the victim name + "their" with no "(?)".
"""

from __future__ import annotations

from mud.models.character import Character, SpellEffect
from mud.models.constants import Position, Sex
from mud.models.room import Room
from mud.skills.handlers import change_sex


def test_magic021_already_changed_replicates_rom_s_quirk():
    room = Room(vnum=99150, name="Lab")  # default sector 0 = INSIDE (lit)
    caster = Character(name="Wizard", level=30, is_npc=False, sex=Sex.MALE, position=int(Position.STANDING))
    caster.room = room
    room.people.append(caster)
    caster.messages = []

    goblin = Character(
        name="goblin", is_npc=True, short_descr="a green goblin", sex=Sex.FEMALE, position=int(Position.STANDING)
    )
    goblin.room = room
    room.people.append(goblin)
    goblin.messages = []
    goblin.apply_spell_effect(SpellEffect(name="change sex", duration=10, level=30))

    change_sex(caster, target=goblin)

    # ROM: $N = victim PERS "a green goblin" (cap), $s = CASTER's possessive ("his",
    # caster is male — NOT the victim's), literal "(?)".
    assert any("A green goblin has already had his(?) sex changed." in m for m in caster.messages), caster.messages
