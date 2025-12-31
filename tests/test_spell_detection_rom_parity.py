"""ROM parity tests for detection spells.

C reference locations (ROM 2.4b6):
- detect_evil:   src/magic.c:2718 (AFF_DETECT_EVIL)
- detect_good:   src/magic.c:2750 (AFF_DETECT_GOOD)
- detect_hidden: src/magic.c:2782 (AFF_DETECT_HIDDEN)
- detect_invis:  src/magic.c:2814 (AFF_DETECT_INVIS)
- detect_magic:  src/magic.c:2846 (AFF_DETECT_MAGIC)
- detect_poison: src/magic.c:2878 (checks food/drink for poison)

These tests assert QuickMUD handlers match the ROM semantics implemented in
`mud/skills/handlers.py`:
- detection spells apply an affect flag + named SpellEffect
- duration formula is `level`
- duplicate casting is gated (no affect_join)
- detect_poison inspects FOOD/DRINK_CON `value[3]`
"""

from __future__ import annotations

import pytest

from mud.models.character import Character
from mud.models.constants import AffectFlag, ItemType, Position
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.skills.handlers import (
    detect_evil,
    detect_good,
    detect_hidden,
    detect_invis,
    detect_magic,
    detect_poison,
)
from mud.utils import rng_mm


@pytest.fixture(autouse=True)
def _seed_rng() -> None:
    """Ensure deterministic RNG for parity tests."""

    rng_mm.seed_mm(42)


def make_character(**overrides) -> Character:
    """Helper to create test characters with common defaults."""

    base = {
        "name": overrides.get("name", "TestChar"),
        "level": overrides.get("level", 30),
        "hit": overrides.get("hit", 120),
        "max_hit": overrides.get("max_hit", 120),
        "mana": overrides.get("mana", 100),
        "max_mana": overrides.get("max_mana", 100),
        "move": overrides.get("move", 100),
        "max_move": overrides.get("max_move", 100),
        "position": overrides.get("position", Position.STANDING),
        "is_npc": overrides.get("is_npc", True),
        "alignment": overrides.get("alignment", 0),
        "affected_by": overrides.get("affected_by", 0),
    }
    char = Character(**base)
    for key, value in overrides.items():
        setattr(char, key, value)
    return char


def _make_object(*, item_type: ItemType, value: list[int] | None = None, **overrides) -> Object:
    proto = ObjIndex(
        vnum=overrides.get("vnum", 9999),
        name=overrides.get("name", "object"),
        short_descr=overrides.get("short_descr", "an object"),
        item_type=int(item_type),
    )
    obj = Object(instance_id=None, prototype=proto)
    if value is not None:
        obj.value = value.copy()
    for key, val in overrides.items():
        setattr(obj, key, val)
    return obj


def _assert_detect_effect(target: Character, *, name: str, flag: AffectFlag, level: int) -> None:
    assert target.has_affect(flag)
    assert target.has_spell_effect(name)

    effect = target.spell_effects.get(name)
    assert effect is not None
    assert effect.level == level
    assert effect.duration == level
    assert effect.affect_flag == flag


def test_detect_evil_applies_affect_self_and_duration() -> None:
    caster = make_character(name="Cleric", level=18, is_npc=False)

    assert detect_evil(caster) is True

    _assert_detect_effect(caster, name="detect evil", flag=AffectFlag.DETECT_EVIL, level=18)
    assert caster.messages[-1] == "Your eyes tingle."


def test_detect_evil_other_target_and_duplicate_gating_messages() -> None:
    caster = make_character(name="Cleric", level=18, is_npc=False)
    target = make_character(name="Scout", level=12, is_npc=False)

    assert detect_evil(caster, target) is True
    _assert_detect_effect(target, name="detect evil", flag=AffectFlag.DETECT_EVIL, level=18)
    assert target.messages[-1] == "Your eyes tingle."
    assert caster.messages[-1] == "Ok."

    caster.messages.clear()
    prior = target.spell_effects["detect evil"].duration
    assert detect_evil(caster, target) is False
    assert target.spell_effects["detect evil"].duration == prior
    assert caster.messages[-1] == "Scout can already detect evil."

    caster.messages.clear()
    assert detect_evil(caster) is True
    caster.messages.clear()
    assert detect_evil(caster) is False
    assert caster.messages[-1] == "You can already sense evil."


def test_detect_good_applies_affect_self_and_duration() -> None:
    caster = make_character(name="Paladin", level=21, is_npc=False)

    assert detect_good(caster) is True

    _assert_detect_effect(caster, name="detect good", flag=AffectFlag.DETECT_GOOD, level=21)
    assert caster.messages[-1] == "Your eyes tingle."


def test_detect_good_other_target_and_duplicate_gating_messages() -> None:
    caster = make_character(name="Paladin", level=21, is_npc=False)
    target = make_character(name="Squire", level=10, is_npc=False)

    assert detect_good(caster, target) is True
    _assert_detect_effect(target, name="detect good", flag=AffectFlag.DETECT_GOOD, level=21)
    assert target.messages[-1] == "Your eyes tingle."
    assert caster.messages[-1] == "Ok."

    caster.messages.clear()
    prior = target.spell_effects["detect good"].duration
    assert detect_good(caster, target) is False
    assert target.spell_effects["detect good"].duration == prior
    assert caster.messages[-1] == "Squire can already detect good."

    caster.messages.clear()
    assert detect_good(caster) is True
    caster.messages.clear()
    assert detect_good(caster) is False
    assert caster.messages[-1] == "You can already sense good."


def test_detect_hidden_applies_affect_self_and_duration() -> None:
    caster = make_character(name="Ranger", level=13, is_npc=False)

    assert detect_hidden(caster) is True

    _assert_detect_effect(caster, name="detect hidden", flag=AffectFlag.DETECT_HIDDEN, level=13)
    assert caster.messages[-1] == "Your awareness improves."


def test_detect_hidden_other_target_and_duplicate_gating_messages() -> None:
    caster = make_character(name="Ranger", level=13, is_npc=False)
    target = make_character(name="Scout", level=8, is_npc=False)

    assert detect_hidden(caster, target) is True
    _assert_detect_effect(target, name="detect hidden", flag=AffectFlag.DETECT_HIDDEN, level=13)
    assert target.messages[-1] == "Your awareness improves."
    assert caster.messages[-1] == "Ok."

    caster.messages.clear()
    prior = target.spell_effects["detect hidden"].duration
    assert detect_hidden(caster, target) is False
    assert target.spell_effects["detect hidden"].duration == prior
    assert caster.messages[-1] == "Scout can already sense hidden lifeforms."

    caster.messages.clear()
    assert detect_hidden(caster) is True
    caster.messages.clear()
    assert detect_hidden(caster) is False
    assert caster.messages[-1] == "You are already as alert as you can be."


def test_detect_invis_applies_affect_self_and_duration() -> None:
    caster = make_character(name="Seer", level=24, is_npc=False)

    assert detect_invis(caster) is True

    _assert_detect_effect(caster, name="detect invis", flag=AffectFlag.DETECT_INVIS, level=24)
    assert caster.messages[-1] == "Your eyes tingle."


def test_detect_invis_other_target_and_duplicate_gating_messages() -> None:
    caster = make_character(name="Seer", level=24, is_npc=False)
    target = make_character(name="Watcher", level=10, is_npc=False)

    assert detect_invis(caster, target) is True
    _assert_detect_effect(target, name="detect invis", flag=AffectFlag.DETECT_INVIS, level=24)
    assert target.messages[-1] == "Your eyes tingle."
    assert caster.messages[-1] == "Ok."

    caster.messages.clear()
    prior = target.spell_effects["detect invis"].duration
    assert detect_invis(caster, target) is False
    assert target.spell_effects["detect invis"].duration == prior
    assert caster.messages[-1] == "Watcher can already see invisible things."

    caster.messages.clear()
    assert detect_invis(caster) is True
    caster.messages.clear()
    assert detect_invis(caster) is False
    assert caster.messages[-1] == "You can already see invisible."


def test_detect_magic_applies_affect_self_and_duration() -> None:
    caster = make_character(name="Wizard", level=9, is_npc=False)

    assert detect_magic(caster) is True

    _assert_detect_effect(caster, name="detect magic", flag=AffectFlag.DETECT_MAGIC, level=9)
    assert caster.messages[-1] == "Your eyes tingle."


def test_detect_magic_other_target_and_duplicate_gating_messages() -> None:
    caster = make_character(name="Wizard", level=9, is_npc=False)
    target = make_character(name="Apprentice", level=5, is_npc=False)

    assert detect_magic(caster, target) is True
    _assert_detect_effect(target, name="detect magic", flag=AffectFlag.DETECT_MAGIC, level=9)
    assert target.messages[-1] == "Your eyes tingle."
    assert caster.messages[-1] == "Ok."

    caster.messages.clear()
    prior = target.spell_effects["detect magic"].duration
    assert detect_magic(caster, target) is False
    assert target.spell_effects["detect magic"].duration == prior
    assert caster.messages[-1] == "Apprentice can already detect magic."

    caster.messages.clear()
    assert detect_magic(caster) is True
    caster.messages.clear()
    assert detect_magic(caster) is False
    assert caster.messages[-1] == "You can already sense magical auras."


def test_detect_poison_food_poisoned_reports_fumes() -> None:
    caster = make_character(name="Inspector", level=10, is_npc=False)
    food = _make_object(item_type=ItemType.FOOD, value=[5, 0, 0, 1, 0], short_descr="a loaf of bread")

    assert detect_poison(caster, food) is True
    assert caster.messages[-1] == "You smell poisonous fumes."


def test_detect_poison_drink_not_poisoned_reports_delicious() -> None:
    caster = make_character(name="Inspector", level=10, is_npc=False)
    drink = _make_object(item_type=ItemType.DRINK_CON, value=[10, 0, 0, 0, 0], short_descr="a water skin")

    assert detect_poison(caster, drink) is True
    assert caster.messages[-1] == "It looks delicious."


def test_detect_poison_non_food_drink_reports_not_poisoned() -> None:
    caster = make_character(name="Inspector", level=10, is_npc=False)
    sword = _make_object(item_type=ItemType.WEAPON, value=[0, 0, 0, 1, 0], short_descr="a sword")

    assert detect_poison(caster, sword) is True
    assert caster.messages[-1] == "It doesn't look poisoned."
