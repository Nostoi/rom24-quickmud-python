from __future__ import annotations

from mud.math.c_compat import c_div
from mud.models.character import Character
from mud.models.constants import Position
from mud.skills.handlers import armor, bless, cure_light
from mud.utils import rng_mm


def make_character(**overrides) -> Character:
    base = {
        "name": "mob",
        "level": overrides.get("level", 10),
        "hit": overrides.get("hit", 50),
        "max_hit": overrides.get("max_hit", 100),
        "position": overrides.get("position", Position.STANDING),
        "is_npc": overrides.get("is_npc", True),
    }
    char = Character(**base)
    # Allow callers to override post-init attributes like armor lists
    for key, value in overrides.items():
        setattr(char, key, value)
    return char


def test_rom_buff_spells() -> None:
    caster = make_character(name="Gandalf", level=20)
    target = make_character(
        name="Pippin",
        level=12,
        hit=40,
        max_hit=100,
        armor=[10, 10, 10, 10],
    )

    assert armor(caster, target) is True
    assert target.armor == [-10, -10, -10, -10]
    assert target.has_spell_effect("armor") is True

    # Second cast should fail gracefully without stacking AC
    assert armor(caster, target) is False
    assert target.armor == [-10, -10, -10, -10]

    target.hitroll = 0
    target.saving_throw = 0
    assert bless(caster, target) is True
    bless_bonus = c_div(caster.level, 8)
    assert target.hitroll == bless_bonus
    assert target.saving_throw == -bless_bonus
    assert target.has_spell_effect("bless") is True

    # Blessing a fighting character or stacking should be prevented
    target.position = Position.FIGHTING
    assert bless(caster, target) is False

    healer = make_character(name="Priest", level=18)
    wounded = make_character(name="Merry", level=18, hit=20, max_hit=100)
    rng_mm.seed_mm(1337)
    expected_heal = rng_mm.dice(1, 8) + c_div(healer.level, 3)
    rng_mm.seed_mm(1337)
    heal_amount = cure_light(healer, wounded)
    assert heal_amount == expected_heal
    assert wounded.hit == min(20 + heal_amount, wounded.max_hit)

    near_full = make_character(name="Sam", level=18, hit=98, max_hit=100)
    rng_mm.seed_mm(2024)
    heal_capped = cure_light(healer, near_full)
    assert heal_capped >= 0
    assert near_full.hit == near_full.max_hit
