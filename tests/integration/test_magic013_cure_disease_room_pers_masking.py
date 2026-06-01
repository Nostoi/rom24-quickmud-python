"""Regression for MAGIC-013 (probe of FINDING-015 / INV-025 sweep, 2026-06-01).

ROM ``spell_cure_disease`` (`src/magic.c:1657-1659`) broadcasts the dispel-success
room line as ``act("$n looks relieved as $s sores vanish.", victim, NULL, NULL,
TO_ROOM)``, so ``comm.c`` renders ``$n`` per recipient via ``PERS(victim, to)``
(an invisible victim masks to "someone") and ``$s`` as the victim's gendered
possessive (his/her/its).

The Python ``cure_disease`` handler had two divergences in this one leg:
(a) it baked the victim name + literal "their", with no ``$n`` masking / wrong
``$s`` possessive (same class as MAGIC-012), and (b) it delivered via the
divergent ``occupant.messages.append`` mailbox channel instead of the canonical
per-recipient ``act_to_room`` / ``push_message`` (MAGIC-003 wrong-channel class).

ROM C: src/magic.c:1657-1659 (spell_cure_disease dispel-success room broadcast).
"""

from __future__ import annotations

from unittest.mock import patch

from mud.models.character import Character, SpellEffect
from mud.models.constants import AffectFlag, Sex
from mud.models.room import Room
from mud.skills import handlers as skill_handlers
from mud.utils import rng_mm


def _room(vnum: int = 3044) -> Room:
    room = Room(vnum=vnum, name="Ward")
    room.people = []
    return room


def _give_plague(victim: Character) -> None:
    victim.apply_spell_effect(
        SpellEffect(name="plague", duration=5, level=10, affect_flag=AffectFlag.PLAGUE)
    )


def test_cure_disease_room_line_uses_gendered_possessive() -> None:
    rng_mm.seed_mm(42)
    caster = Character(name="Cleric", level=50, is_npc=False)
    victim = Character(name="Paladin", level=10, is_npc=False, sex=int(Sex.MALE))
    witness = Character(name="Witness", level=18, is_npc=False)
    room = _room()
    for ch in (caster, victim, witness):
        room.add_character(ch)
    _give_plague(victim)
    witness.messages.clear()

    # saves_dispel=False → the victim fails to save → the dispel succeeds.
    with patch("mud.affects.saves.saves_dispel", return_value=False):
        assert skill_handlers.cure_disease(caster, victim) is True

    # ROM `$s` → gendered possessive; a male victim renders "his", not "their".
    assert witness.messages[-1] == "Paladin looks relieved as his sores vanish.", witness.messages


def test_cure_disease_room_line_masks_invisible_victim() -> None:
    rng_mm.seed_mm(42)
    caster = Character(name="Cleric", level=50, is_npc=False)
    victim = Character(name="Paladin", level=10, is_npc=False, sex=int(Sex.FEMALE))
    witness = Character(name="Witness", level=18, is_npc=False)
    room = _room()
    for ch in (caster, victim, witness):
        room.add_character(ch)
    _give_plague(victim)
    # Witness cannot see an invisible victim → ROM `$n` masks to "Someone".
    victim.add_affect(AffectFlag.INVISIBLE)
    witness.messages.clear()

    with patch("mud.affects.saves.saves_dispel", return_value=False):
        assert skill_handlers.cure_disease(caster, victim) is True

    assert witness.messages[-1] == "Someone looks relieved as her sores vanish.", witness.messages
