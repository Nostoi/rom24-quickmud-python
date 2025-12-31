"""ROM Parity Tests for High-Priority Missing Spells.

Tests for critical spells that lacked comprehensive test coverage:
- teleport: Random room teleportation
- word_of_recall: Return to temple
- heal: Fixed 100 HP healing
- fireball: Damage table with save-for-half
- dispel_magic: Remove spell effects
- stone_skin: -40 AC buff

All tests follow ROM parity test style with deterministic RNG.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from mud.models.character import Character, SpellEffect
from mud.models.constants import AffectFlag, DamageType, Position, RoomFlag, ROOM_VNUM_TEMPLE
from mud.skills.handlers import (
    dispel_magic,
    fireball,
    heal,
    stone_skin,
    teleport,
    word_of_recall,
)
from mud.utils import rng_mm


def make_character(**overrides) -> Character:
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
    }
    char = Character(**base)
    for key, value in overrides.items():
        setattr(char, key, value)
    return char


def test_stone_skin_applies_ac_buff():
    caster = make_character(level=20)
    target = make_character()

    result = stone_skin(caster, target)

    assert result is True
    assert target.has_spell_effect("stone skin") is True
    effect = target.spell_effects["stone skin"]
    assert effect.ac_mod == -40
    assert effect.duration == 20
    assert effect.level == 20


def test_stone_skin_rejects_if_already_affected():
    caster = make_character(level=20)
    target = make_character()

    stone_skin(caster, target)
    result = stone_skin(caster, target)

    assert result is False


def test_stone_skin_self_target_defaults():
    caster = make_character(level=15)

    result = stone_skin(caster, None)

    assert result is True
    assert caster.has_spell_effect("stone skin") is True
    effect = caster.spell_effects["stone skin"]
    assert effect.ac_mod == -40
    assert effect.duration == 15


def test_heal_fixed_100_hp():
    caster = make_character(level=20)
    target = make_character(hit=50, max_hit=200)

    result = heal(caster, target)

    assert result == 100
    assert target.hit == 150


def test_heal_caps_at_max_hit():
    caster = make_character(level=30)
    target = make_character(hit=90, max_hit=100)

    result = heal(caster, target)

    assert result == 100
    assert target.hit == 100


def test_heal_self_target_defaults():
    caster = make_character(level=15, hit=50, max_hit=200)

    result = heal(caster, None)

    assert result == 100
    assert caster.hit == 150


def test_fireball_damage_table_level_14():
    rng_mm.seed_mm(42)
    caster = make_character(level=14)
    target = make_character()

    with patch("mud.skills.handlers.saves_spell", return_value=False):
        with patch("mud.skills.handlers.apply_damage", return_value=0) as mock_damage:
            fireball(caster, target)
            mock_damage.assert_called_once()
            damage = mock_damage.call_args[0][2]
            assert 15 <= damage <= 60


def test_fireball_damage_table_level_20():
    rng_mm.seed_mm(42)
    caster = make_character(level=20)
    target = make_character()

    with patch("mud.skills.handlers.saves_spell", return_value=False):
        with patch("mud.skills.handlers.apply_damage", return_value=0) as mock_damage:
            fireball(caster, target)
            mock_damage.assert_called_once()
            damage = mock_damage.call_args[0][2]
            assert 30 <= damage <= 120


def test_fireball_damage_table_level_30():
    rng_mm.seed_mm(42)
    caster = make_character(level=30)
    target = make_character()

    with patch("mud.skills.handlers.saves_spell", return_value=False):
        with patch("mud.skills.handlers.apply_damage", return_value=0) as mock_damage:
            fireball(caster, target)
            mock_damage.assert_called_once()
            damage = mock_damage.call_args[0][2]
            assert 46 <= damage <= 184


def test_fireball_save_halves_damage():
    rng_mm.seed_mm(42)
    caster = make_character(level=20)
    target = make_character()

    with patch("mud.skills.handlers.saves_spell", return_value=True):
        with patch("mud.skills.handlers.apply_damage", return_value=0) as mock_damage:
            fireball(caster, target)
            mock_damage.assert_called_once()
            damage = mock_damage.call_args[0][2]
            assert 15 <= damage <= 60


def test_dispel_magic_removes_effects():
    caster = make_character(level=30)
    target = make_character()

    target.spell_effects["armor"] = SpellEffect(name="armor", duration=10, level=10, ac_mod=-20)
    target.spell_effects["bless"] = SpellEffect(name="bless", duration=10, level=10, hitroll_mod=2)

    with patch("mud.skills.handlers.check_dispel", return_value=True):
        result = dispel_magic(caster, target)

    assert result is True


def test_dispel_magic_returns_false_when_no_effects():
    caster = make_character(level=30)
    target = make_character()

    result = dispel_magic(caster, target)

    assert result is False


def test_dispel_magic_self_target_defaults():
    caster = make_character(level=20)
    caster.spell_effects["armor"] = SpellEffect(name="armor", duration=10, level=10, ac_mod=-20)

    with patch("mud.skills.handlers.check_dispel", return_value=True):
        result = dispel_magic(caster, None)

    assert result is True


def test_teleport_moves_caster_to_random_room():
    caster = make_character(level=20)

    mock_room = MagicMock()
    mock_room.people = []
    caster.room = mock_room

    mock_dest = MagicMock()
    mock_dest.people = []

    with patch("mud.skills.handlers._get_room_flags", return_value=0):
        with patch("mud.skills.handlers._get_random_room", return_value=mock_dest):
            with patch("mud.skills.handlers.look", return_value="You see a room."):
                with patch("mud.skills.handlers.broadcast_room"):
                    result = teleport(caster, None)

    assert result is True
    mock_room.remove_character.assert_called_once_with(caster)
    mock_dest.add_character.assert_called_once_with(caster)


def test_teleport_blocked_by_no_recall_room():
    caster = make_character(level=20)

    mock_room = MagicMock()
    caster.room = mock_room

    with patch("mud.skills.handlers._get_room_flags", return_value=int(RoomFlag.ROOM_NO_RECALL)):
        result = teleport(caster, None)

    assert result is False


def test_teleport_target_can_save():
    caster = make_character(level=20)
    target = make_character()

    mock_room = MagicMock()
    target.room = mock_room

    with patch("mud.skills.handlers._get_room_flags", return_value=0):
        with patch("mud.skills.handlers.saves_spell", return_value=True):
            result = teleport(caster, target)

    assert result is False


def test_word_of_recall_returns_to_temple():
    caster = make_character(level=20, is_npc=False, move=100)

    mock_current = MagicMock()
    mock_current.people = []
    caster.room = mock_current

    mock_temple = MagicMock()
    mock_temple.people = []

    with patch.dict("mud.skills.handlers.room_registry", {ROOM_VNUM_TEMPLE: mock_temple}):
        with patch("mud.skills.handlers._get_room_flags", return_value=0):
            with patch("mud.skills.handlers.look", return_value="Temple."):
                with patch("mud.skills.handlers.broadcast_room"):
                    result = word_of_recall(caster, None)

    assert result is True
    assert caster.move == 50
    mock_current.remove_character.assert_called_once_with(caster)
    mock_temple.add_character.assert_called_once_with(caster)


def test_word_of_recall_blocked_by_no_recall_room():
    caster = make_character(level=20, is_npc=False)

    mock_room = MagicMock()
    caster.room = mock_room

    with patch("mud.skills.handlers._get_room_flags", return_value=int(RoomFlag.ROOM_NO_RECALL)):
        result = word_of_recall(caster, None)

    assert result is False


def test_word_of_recall_blocked_by_curse():
    caster = make_character(level=20, is_npc=False)
    caster.spell_effects["curse"] = SpellEffect(name="curse", duration=10, level=10)

    mock_room = MagicMock()
    caster.room = mock_room

    with patch("mud.skills.handlers._get_room_flags", return_value=0):
        result = word_of_recall(caster, None)

    assert result is False


def test_word_of_recall_halves_move_points():
    caster = make_character(level=20, is_npc=False, move=100)

    mock_current = MagicMock()
    mock_current.people = []
    caster.room = mock_current

    mock_temple = MagicMock()
    mock_temple.people = []

    with patch.dict("mud.skills.handlers.room_registry", {ROOM_VNUM_TEMPLE: mock_temple}):
        with patch("mud.skills.handlers._get_room_flags", return_value=0):
            with patch("mud.skills.handlers.look", return_value="Temple."):
                with patch("mud.skills.handlers.broadcast_room"):
                    word_of_recall(caster, None)

    assert caster.move == 50
