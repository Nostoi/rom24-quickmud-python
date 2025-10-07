from __future__ import annotations

import pytest

from mud.models.character import Character
from mud.models.constants import AffectFlag
from mud.models.room import Room
from mud.skills import handlers as skill_handlers
from mud.utils import rng_mm


def test_dispel_evil_damages_evil_targets(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Priest", level=30, is_npc=False, alignment=400)
    victim = Character(name="Shade", level=28, is_npc=False, alignment=-500, hit=200)
    room = Room(vnum=4100)
    room.add_character(caster)
    room.add_character(victim)

    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, target, dtype: False)
    monkeypatch.setattr(rng_mm, "dice", lambda number, size: 60)

    damage = skill_handlers.dispel_evil(caster, victim)

    assert damage == 60
    assert victim.hit == 140


def test_demonfire_applies_curse_and_fire_damage(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Warlock", level=32, is_npc=False, alignment=-600)
    victim = Character(name="Paladin", level=28, is_npc=False, alignment=450, hit=150)
    observer = Character(name="Witness", is_npc=False)
    room = Room(vnum=4200)
    for ch in (caster, victim, observer):
        room.add_character(ch)

    dice_values = iter([80])
    monkeypatch.setattr(rng_mm, "dice", lambda number, size: next(dice_values))

    save_results = iter([False, False])

    def fake_saves(level: int, target: Character, damage_type: int) -> bool:
        return next(save_results)

    monkeypatch.setattr(skill_handlers, "saves_spell", fake_saves)

    damage = skill_handlers.demonfire(caster, victim)

    assert damage == 80
    assert victim.hit == 70
    assert victim.has_affect(AffectFlag.CURSE)
    assert victim.has_spell_effect("curse")
    assert caster.alignment == -650
    assert victim.messages[-1] == "You feel unclean."
    assert caster.messages[-1] == "Paladin looks very uncomfortable."
    assert observer.messages[-1] == "Warlock calls forth the demons of Hell upon Paladin!"
    assert caster.messages[0] == "You conjure forth the demons of hell!"
    assert victim.messages[0] == "Warlock has assailed you with the demons of Hell!"
