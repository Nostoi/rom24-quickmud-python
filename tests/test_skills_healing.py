"""Regression tests for ROM cure/heal spell parity."""

from __future__ import annotations

import pytest

from mud.math.c_compat import c_div
from mud.models.character import Character, SpellEffect
from mud.models.constants import AffectFlag
from mud.models.room import Room
from mud.skills import handlers as skill_handlers
from mud.utils import rng_mm


def test_cure_light_heals_using_rom_dice(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Cleric", level=24, is_npc=False)
    target = Character(name="Tank", hit=20, max_hit=40, is_npc=False)
    room = Room(vnum=3001)
    for ch in (caster, target):
        room.add_character(ch)

    monkeypatch.setattr(rng_mm, "dice", lambda number, size: 6)

    healed = skill_handlers.cure_light(caster, target)

    expected = 6 + c_div(caster.level, 3)
    assert healed == expected
    assert target.hit == 20 + expected
    assert target.messages[-1] == "You feel better!"
    assert caster.messages[-1] == "Ok."


def test_cure_disease_and_poison_remove_affects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    caster = Character(name="Healer", level=30, is_npc=False)
    target = Character(name="Patient", hit=55, max_hit=70, is_npc=False)
    observer = Character(name="Watcher", is_npc=False)
    room = Room(vnum=3002)
    for ch in (caster, target, observer):
        room.add_character(ch)

    monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)

    plague_effect = SpellEffect(
        name="plague",
        duration=10,
        level=20,
        affect_flag=AffectFlag.PLAGUE,
        wear_off_message="Your sores vanish.",
    )
    target.apply_spell_effect(plague_effect)

    assert skill_handlers.cure_disease(caster, target) is True
    assert not target.has_spell_effect("plague")
    assert not target.has_affect(AffectFlag.PLAGUE)
    assert "Your sores vanish." in target.messages
    assert "Patient looks relieved as their sores vanish." in observer.messages

    poison_effect = SpellEffect(
        name="poison",
        duration=8,
        level=18,
        affect_flag=AffectFlag.POISON,
        wear_off_message="You feel less sick.",
    )
    target.apply_spell_effect(poison_effect)

    assert skill_handlers.cure_poison(caster, target) is True
    assert not target.has_spell_effect("poison")
    assert not target.has_affect(AffectFlag.POISON)
    assert any(
        message == "A warm feeling runs through your body."
        for message in target.messages
    )
    assert "Patient looks much better." in observer.messages
