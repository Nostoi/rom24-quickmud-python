"""RESTORE-001 — ``do_restore`` must strip plague/poison/blindness/sleep/curse.

ROM contract (``src/act_wiz.c:2785-2869 do_restore``)::

    affect_strip (vch, gsn_plague);
    affect_strip (vch, gsn_poison);
    affect_strip (vch, gsn_blindness);
    affect_strip (vch, gsn_sleep);
    affect_strip (vch, gsn_curse);

    vch->hit  = vch->max_hit;
    vch->mana = vch->max_mana;
    vch->move = vch->max_move;
    update_pos (vch);

The five ``affect_strip`` calls run at all three restore code paths
(room loop line 2807, "all" descriptor loop line 2839, named victim
line 2861). Python's ``_restore_char`` in ``mud/commands/imm_load.py``
only refilled hit/mana/move and clamped position — the affect strip
was left as a TODO comment. A poisoned/plagued/blinded/sleeping/cursed
character that gets restored stays afflicted, contrary to ROM.
"""

from __future__ import annotations

import pytest

from mud.commands.imm_load import do_restore
from mud.models.character import Character, SpellEffect, character_registry
from mud.models.constants import Position
from mud.models.room import Room


@pytest.fixture(autouse=True)
def _cleanup():
    snapshot = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(snapshot)


def test_restore_strips_poison_plague_blindness_sleep_curse() -> None:
    """``do_restore`` must clear the five named negative affects.

    ROM ``src/act_wiz.c:2807, 2839, 2861`` — all three restore paths
    affect_strip plague/poison/blindness/sleep/curse before refilling
    vitals. Python skipped the strip entirely.
    """
    room = Room(vnum=99963, name="Restore strip probe")
    immortal = Character(name="Immortal", is_npc=False, position=Position.STANDING)
    immortal.level = 60
    immortal.trust = 60
    immortal.messages = []

    victim = Character(name="Victim", is_npc=False, position=Position.STANDING)
    victim.level = 10
    victim.hit = 5
    victim.max_hit = 100
    victim.mana = 5
    victim.max_mana = 100
    victim.move = 5
    victim.max_move = 100
    victim.messages = []

    for name in ("plague", "poison", "blindness", "sleep", "curse"):
        victim.apply_spell_effect(SpellEffect(name=name, duration=10))

    room.add_character(immortal)
    room.add_character(victim)
    character_registry.extend([immortal, victim])

    assert all(victim.has_spell_effect(n) for n in ("plague", "poison", "blindness", "sleep", "curse")), (
        "pre-condition: all 5 negative affects applied"
    )

    do_restore(immortal, "")

    leftovers = [n for n in ("plague", "poison", "blindness", "sleep", "curse") if victim.has_spell_effect(n)]
    assert not leftovers, (
        "ROM src/act_wiz.c:2861 affect_strip plague/poison/blindness/sleep/curse. "
        f"Restored victim still affected by: {leftovers!r}."
    )
    assert victim.hit == victim.max_hit, "vitals must also be refilled (sanity)"
