"""MAGIC-034 — detect_* cross-target "can already …" lines use $N PERS (cap).

ROM (`src/magic.c`): the duplicate-cast reject for each detect spell is
`act("$N can already …", ch, NULL, victim, TO_CHAR)` — `$N` = PERS(victim) = NPC
short_descr, capitalized. The self-cast legs are ROM `send_to_char` literals and
were already correct. The Python baked the keyword `name`:

  - detect_evil   `:1846` "$N can already detect evil."
  - detect_good   `:1875` "$N can already detect good."
  - detect_hidden `:1905` "$N can already sense hidden lifeforms."
  - detect_invis  `:1936` "$N can already see invisible things."
  - detect_magic  `:1968` "$N can already detect magic."
"""

from __future__ import annotations

import pytest

from mud.models.character import Character
from mud.models.constants import AffectFlag, Position
from mud.models.room import Room
from mud.skills.handlers import detect_evil, detect_good, detect_hidden, detect_invis, detect_magic


@pytest.mark.parametrize(
    ("handler", "flag", "expected"),
    [
        (detect_evil, AffectFlag.DETECT_EVIL, "A green goblin can already detect evil."),
        (detect_good, AffectFlag.DETECT_GOOD, "A green goblin can already detect good."),
        (detect_hidden, AffectFlag.DETECT_HIDDEN, "A green goblin can already sense hidden lifeforms."),
        (detect_invis, AffectFlag.DETECT_INVIS, "A green goblin can already see invisible things."),
        (detect_magic, AffectFlag.DETECT_MAGIC, "A green goblin can already detect magic."),
    ],
)
def test_magic034_detect_duplicate_cross_target_uses_pers_cap(handler, flag, expected):
    room = Room(vnum=99208, name="Arena")
    caster = Character(name="Mage", level=30, ch_class=0, is_npc=False, position=int(Position.STANDING))
    room.add_character(caster)
    caster.messages = []
    goblin = Character(name="goblin", is_npc=True, short_descr="a green goblin", position=int(Position.STANDING))
    room.add_character(goblin)
    goblin.affected_by |= int(flag)

    assert handler(caster, target=goblin) is False
    assert any(expected in m for m in caster.messages), (expected, caster.messages)
