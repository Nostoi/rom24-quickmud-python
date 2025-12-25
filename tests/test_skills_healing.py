"""Regression tests for ROM cure/heal spell parity."""

from __future__ import annotations

import pytest

from mud.math.c_compat import c_div
from mud.models.character import Character, SpellEffect
from mud.models.constants import AffectFlag, ExtraFlag
from mud.models.obj import ObjIndex
from mud.models.object import Object
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

    monkeypatch.setattr(rng_mm, "number_percent", lambda: 99)

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
    assert any(message == "A warm feeling runs through your body." for message in target.messages)
    assert "Patient looks much better." in observer.messages


def test_refresh_restores_move() -> None:
    caster = Character(name="Healer", level=12, is_npc=False, move=30, max_move=30)
    target = Character(name="Scout", level=10, is_npc=False, move=10, max_move=25)

    assert skill_handlers.refresh(caster, target) is True
    assert target.move == 22
    assert target.messages[-1] == "You feel less tired."
    assert caster.messages[-1] == "Ok."

    caster.messages.clear()
    target.messages.clear()
    target.move = 20

    assert skill_handlers.refresh(caster, target) is True
    assert target.move == 25
    assert target.messages[-1] == "You feel fully refreshed!"
    assert caster.messages[-1] == "Ok."

    target.messages.clear()
    assert skill_handlers.refresh(target) is True
    assert target.messages[-1] == "You feel fully refreshed!"


def test_remove_curse_dispels_affect_and_object_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Cleric", level=30, is_npc=False)
    victim = Character(name="Bearer", level=20, is_npc=False)
    observer = Character(name="Witness", level=18, is_npc=False)
    room = Room(vnum=3006)
    for character in (caster, victim, observer):
        room.add_character(character)

    prototype = ObjIndex(vnum=5000, short_descr="cursed sword", name="cursed sword")
    cursed_weapon = Object(
        instance_id=1,
        prototype=prototype,
        level=20,
        extra_flags=int(ExtraFlag.NODROP | ExtraFlag.NOREMOVE),
    )
    victim.add_object(cursed_weapon)

    victim.apply_spell_effect(
        SpellEffect(
            name="curse",
            duration=5,
            level=20,
            affect_flag=AffectFlag.CURSE,
            wear_off_message="The curse wears off.",
        )
    )

    for character in (caster, victim, observer):
        character.messages.clear()

    monkeypatch.setattr(rng_mm, "number_percent", lambda: 99)

    assert skill_handlers.remove_curse(caster, victim) is True
    assert not victim.has_spell_effect("curse")
    assert not victim.has_affect(AffectFlag.CURSE)
    assert cursed_weapon.extra_flags & int(ExtraFlag.NODROP) == 0
    assert cursed_weapon.extra_flags & int(ExtraFlag.NOREMOVE) == 0
    assert "You feel better." in victim.messages
    assert any(msg == "Your cursed sword glows blue." for msg in victim.messages)
    assert observer.messages[-1] == "Bearer's cursed sword glows blue."
    assert caster.messages[-1] == "Bearer's cursed sword glows blue."

    cursed_weapon.extra_flags = int(ExtraFlag.NODROP | ExtraFlag.NOREMOVE)
    caster.messages.clear()
    observer.messages.clear()

    assert skill_handlers.remove_curse(caster, cursed_weapon) is True
    assert cursed_weapon.extra_flags & int(ExtraFlag.NODROP) == 0
    assert cursed_weapon.extra_flags & int(ExtraFlag.NOREMOVE) == 0
    assert caster.messages[-1] == "cursed sword glows blue."
    assert observer.messages[-1] == "cursed sword glows blue."
