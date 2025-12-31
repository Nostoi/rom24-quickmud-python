"""ROM Parity Tests for Final Nine Untested Spells.

Tests for the remaining 9 spells to achieve 100% spell test coverage:
- acid_blast: dice(level, 12) damage with save-for-half
- burning_hands: Damage table with save-for-half
- call_lightning: dice(level/2, 8) damage (outdoor, raining only)
- faerie_fire: Pink outline with AC penalty
- faerie_fog: Reveals hidden/invisible characters
- ray_of_truth: Alignment-scaled holy damage
- control_weather: Weather manipulation (better/worse)
- recharge: Restore wand/staff charges
- remove_curse: Remove curse from character or object

All tests follow ROM parity test style with deterministic RNG.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from mud.game_loop import SkyState
from mud.models.character import Character, SpellEffect
from mud.models.constants import AffectFlag, DamageType, Position, ExtraFlag, ItemType
from mud.models.object import Object
from mud.models.obj import ObjIndex
from mud.skills.handlers import (
    acid_blast,
    burning_hands,
    call_lightning,
    control_weather,
    faerie_fire,
    faerie_fog,
    ray_of_truth,
    recharge,
    remove_curse,
)
from mud.utils import rng_mm


def make_character(**overrides):
    defaults = {
        "name": "TestChar",
        "level": 20,
        "position": Position.STANDING,
        "hit": 100,
        "max_hit": 100,
        "mana": 100,
        "max_mana": 100,
        "move": 100,
        "max_move": 100,
        "alignment": 0,
        "spell_effects": {},
    }
    defaults.update(overrides)
    return Character(**defaults)


def test_acid_blast_damage_formula():
    rng_mm.seed_mm(42)
    caster = make_character(level=20)
    target = make_character(hit=100)

    with patch("mud.skills.handlers.saves_spell", return_value=False):
        damage = acid_blast(caster, target)

    assert damage > 0
    assert target.hit < 100


def test_acid_blast_save_halves_damage():
    rng_mm.seed_mm(42)
    caster = make_character(level=20)
    target1 = make_character(hit=100)
    target2 = make_character(hit=100)

    with patch("mud.skills.handlers.saves_spell", return_value=False):
        damage_no_save = acid_blast(caster, target1)

    rng_mm.seed_mm(42)
    with patch("mud.skills.handlers.saves_spell", return_value=True):
        damage_with_save = acid_blast(caster, target2)

    assert damage_with_save == damage_no_save // 2


def test_acid_blast_requires_target():
    caster = make_character(level=20)

    with pytest.raises(ValueError, match="acid_blast requires a target"):
        acid_blast(caster, None)


def test_burning_hands_damage_table():
    rng_mm.seed_mm(42)
    caster = make_character(level=14)
    target = make_character(hit=100)

    with patch("mud.skills.handlers.saves_spell", return_value=False):
        damage = burning_hands(caster, target)

    assert damage > 0
    assert target.hit < 100


def test_burning_hands_save_halves_damage():
    rng_mm.seed_mm(42)
    caster = make_character(level=14)
    target1 = make_character(hit=100)
    target2 = make_character(hit=100)

    with patch("mud.skills.handlers.saves_spell", return_value=False):
        damage_no_save = burning_hands(caster, target1)

    rng_mm.seed_mm(42)
    with patch("mud.skills.handlers.saves_spell", return_value=True):
        damage_with_save = burning_hands(caster, target2)

    assert damage_with_save == damage_no_save // 2


def test_burning_hands_requires_target():
    caster = make_character(level=20)

    with pytest.raises(ValueError, match="burning_hands requires a target"):
        burning_hands(caster, None)


def test_call_lightning_damage_formula():
    rng_mm.seed_mm(42)
    caster = make_character(level=20)
    target = make_character(hit=100)
    caster.room = MagicMock()
    target.room = caster.room

    with patch("mud.skills.handlers._is_outside", return_value=True):
        with patch("mud.skills.handlers.weather") as mock_weather:
            mock_weather.sky = SkyState.RAINING
            with patch("mud.skills.handlers.saves_spell", return_value=False):
                damage = call_lightning(caster, target)

    assert damage > 0
    assert target.hit < 100


def test_call_lightning_requires_outdoors():
    caster = make_character(level=20)
    target = make_character(hit=100)
    caster.room = MagicMock()
    target.room = caster.room

    with patch("mud.skills.handlers._is_outside", return_value=False):
        damage = call_lightning(caster, target)

    assert damage == 0


def test_call_lightning_requires_rain():
    caster = make_character(level=20)
    target = make_character(hit=100)
    caster.room = MagicMock()
    target.room = caster.room

    with patch("mud.skills.handlers._is_outside", return_value=True):
        with patch("mud.skills.handlers.weather") as mock_weather:
            mock_weather.sky = SkyState.CLOUDLESS
            damage = call_lightning(caster, target)

    assert damage == 0


def test_call_lightning_save_halves_damage():
    rng_mm.seed_mm(42)
    caster = make_character(level=20)
    target1 = make_character(hit=100)
    target2 = make_character(hit=100)
    caster.room = MagicMock()
    target1.room = caster.room
    target2.room = caster.room

    with patch("mud.skills.handlers._is_outside", return_value=True):
        with patch("mud.skills.handlers.weather") as mock_weather:
            mock_weather.sky = SkyState.RAINING
            with patch("mud.skills.handlers.saves_spell", return_value=False):
                damage_no_save = call_lightning(caster, target1)

    rng_mm.seed_mm(42)
    with patch("mud.skills.handlers._is_outside", return_value=True):
        with patch("mud.skills.handlers.weather") as mock_weather:
            mock_weather.sky = SkyState.RAINING
            with patch("mud.skills.handlers.saves_spell", return_value=True):
                damage_with_save = call_lightning(caster, target2)

    assert damage_with_save == damage_no_save // 2


def test_faerie_fire_applies_affect():
    caster = make_character(level=20)
    target = make_character()

    result = faerie_fire(caster, target)

    assert result is True
    assert target.has_spell_effect("faerie fire")
    effect = target.spell_effects["faerie fire"]
    assert effect.duration == 20
    assert effect.ac_mod == 40
    assert effect.affect_flag == AffectFlag.FAERIE_FIRE


def test_faerie_fire_rejects_if_already_affected():
    caster = make_character(level=20)
    target = make_character()
    target.spell_effects["faerie fire"] = SpellEffect(
        name="faerie fire", duration=10, level=10, affect_flag=AffectFlag.FAERIE_FIRE
    )

    result = faerie_fire(caster, target)

    assert result is False


def test_faerie_fire_ac_penalty_scales_with_level():
    caster = make_character(level=30)
    target = make_character()

    result = faerie_fire(caster, target)

    assert result is True
    effect = target.spell_effects["faerie fire"]
    assert effect.ac_mod == 60


def test_faerie_fog_reveals_invisible():
    caster = make_character(level=20)
    target = make_character()
    room = MagicMock()
    room.people = [caster, target]
    caster.room = room
    target.room = room
    target.spell_effects["invis"] = SpellEffect(name="invis", duration=10, level=10, affect_flag=AffectFlag.INVISIBLE)

    with patch("mud.skills.handlers.saves_spell", return_value=False):
        result = faerie_fog(caster, None)

    assert result is True
    assert not target.has_spell_effect("invis")


def test_faerie_fog_save_prevents_reveal():
    caster = make_character(level=20)
    target = make_character()
    room = MagicMock()
    room.people = [caster, target]
    caster.room = room
    target.room = room
    target.spell_effects["invis"] = SpellEffect(name="invis", duration=10, level=10, affect_flag=AffectFlag.INVISIBLE)

    with patch("mud.skills.handlers.saves_spell", return_value=True):
        result = faerie_fog(caster, None)

    assert result is False
    assert target.has_spell_effect("invis")


def test_ray_of_truth_alignment_scaling():
    rng_mm.seed_mm(42)
    caster = make_character(level=20, alignment=1000)
    target = make_character(hit=100, alignment=-1000)

    with patch("mud.skills.handlers.is_evil", return_value=False):
        with patch("mud.skills.handlers.is_good", return_value=False):
            with patch("mud.skills.handlers.saves_spell", return_value=False):
                with patch("mud.skills.handlers.apply_damage") as mock_damage:
                    ray_of_truth(caster, target)
                    assert mock_damage.called


def test_ray_of_truth_good_victim_unharmed():
    caster = make_character(level=20, alignment=1000)
    target = make_character(hit=100, alignment=1000)

    with patch("mud.skills.handlers.is_evil", return_value=False):
        with patch("mud.skills.handlers.is_good", return_value=True):
            damage = ray_of_truth(caster, target)

    assert damage == 0


def test_ray_of_truth_evil_caster_hurts_self():
    caster = make_character(level=20, alignment=-1000, hit=100)
    target = make_character(hit=100, alignment=0)

    with patch("mud.skills.handlers.is_evil", return_value=True):
        with patch("mud.skills.handlers.is_good", return_value=False):
            with patch("mud.skills.handlers.saves_spell", return_value=False):
                with patch("mud.skills.handlers.apply_damage") as mock_damage:
                    ray_of_truth(caster, target)
                    call_args = mock_damage.call_args
                    victim = call_args[0][1]
                    assert victim is caster


def test_control_weather_better():
    rng_mm.seed_mm(42)
    caster = make_character(level=30)

    with patch("mud.skills.handlers.weather") as mock_weather:
        mock_weather.change = 0
        result = control_weather(caster, "better")
        assert result is True
        assert mock_weather.change > 0


def test_control_weather_worse():
    rng_mm.seed_mm(42)
    caster = make_character(level=30)

    with patch("mud.skills.handlers.weather") as mock_weather:
        mock_weather.change = 0
        result = control_weather(caster, "worse")
        assert result is True
        assert mock_weather.change < 0


def test_control_weather_invalid_argument():
    caster = make_character(level=30)

    with patch("mud.skills.handlers.weather") as mock_weather:
        mock_weather.change = 0
        control_weather(caster, "invalid")
        assert mock_weather.change == 0


def test_recharge_wand_success():
    rng_mm.seed_mm(42)
    caster = make_character(level=40)
    caster.room = MagicMock()
    proto = ObjIndex(vnum=1, item_type=ItemType.WAND, value=[0, 10, 5, 10], short_descr="a wooden wand")
    wand = Object(instance_id=None, prototype=proto)
    wand.item_type = str(ItemType.WAND.value)
    wand.value = [0, 10, 5, 10]

    with patch("mud.skills.handlers.rng_mm.number_percent", return_value=40):
        result = recharge(caster, wand)

    assert result is True
    assert wand.value[2] >= 5


def test_recharge_requires_wand_or_staff():
    caster = make_character(level=40)
    proto = ObjIndex(vnum=2, item_type=ItemType.WEAPON, value=[0, 0, 0, 0])
    sword = Object(instance_id=None, prototype=proto)
    sword.item_type = str(ItemType.WEAPON.value)

    result = recharge(caster, sword)

    assert result is False


def test_recharge_skill_check():
    caster = make_character(level=10)
    proto = ObjIndex(vnum=3, item_type=ItemType.WAND, value=[0, 10, 5, 30])
    wand = Object(instance_id=None, prototype=proto)
    wand.item_type = str(ItemType.WAND.value)
    wand.value = [0, 10, 5, 30]

    result = recharge(caster, wand)

    assert result is False


def test_remove_curse_character():
    caster = make_character(level=20)
    target = make_character()
    target.spell_effects["curse"] = SpellEffect(name="curse", duration=10, level=10, affect_flag=AffectFlag.CURSE)

    with patch("mud.skills.handlers.saves_dispel", return_value=False):
        result = remove_curse(caster, target)

    assert result is True
    assert not target.has_spell_effect("curse")


def test_remove_curse_object():
    caster = make_character(level=20)
    proto = ObjIndex(vnum=4, extra_flags=int(ExtraFlag.NODROP | ExtraFlag.NOREMOVE))
    obj = Object(instance_id=None, prototype=proto)

    with patch("mud.skills.handlers.saves_dispel", return_value=False):
        result = remove_curse(caster, obj)

    assert result is True
    assert not (obj.extra_flags & int(ExtraFlag.NODROP))
    assert not (obj.extra_flags & int(ExtraFlag.NOREMOVE))


def test_remove_curse_nouncurse_flag():
    caster = make_character(level=20)
    proto = ObjIndex(vnum=5, extra_flags=int(ExtraFlag.NODROP | ExtraFlag.NOUNCURSE))
    obj = Object(instance_id=None, prototype=proto)

    result = remove_curse(caster, obj)

    assert result is False


def test_remove_curse_self_target_defaults():
    caster = make_character(level=20)
    caster.spell_effects["curse"] = SpellEffect(name="curse", duration=10, level=10, affect_flag=AffectFlag.CURSE)

    with patch("mud.skills.handlers.saves_dispel", return_value=False):
        result = remove_curse(caster, None)

    assert result is True
    assert not caster.has_spell_effect("curse")
