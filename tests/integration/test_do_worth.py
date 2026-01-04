"""
Integration tests for do_worth command (ROM C parity verification).

ROM Reference: src/act_info.c do_worth (lines 1453-1474)
               src/skills.c exp_per_level (lines 639-672)

Tests verify:
- NPC worth display (gold/silver only)
- PC worth display (gold/silver/exp/exp-to-level)
- Exp-to-level calculation accuracy
- ROM C exp_per_level formula correctness
- Race/class multiplier application
"""

from __future__ import annotations

import pytest

from mud.commands.info_extended import _exp_per_level, do_worth
from mud.models.character import Character, PCData


def test_worth_npc_shows_gold_silver():
    """Test worth command for NPCs shows only gold/silver."""
    mob = Character(name="TestMob", is_npc=True, gold=100, silver=50)
    result = do_worth(mob, "")

    assert "100 gold" in result
    assert "50 silver" in result
    assert "experience" not in result.lower()


def test_worth_pc_shows_gold_silver_exp():
    """Test worth command for PCs shows gold/silver/exp."""
    char = Character(name="TestChar", is_npc=False, gold=100, silver=50, exp=5000, level=10)
    char.pcdata = PCData(points=40)

    result = do_worth(char, "")

    assert "100 gold" in result
    assert "50 silver" in result
    assert "5000 experience" in result
    assert "exp to level" in result.lower()


def test_worth_exp_to_level_calculation():
    """Test exp-to-level calculation is correct."""
    char = Character(name="TestChar", is_npc=False, exp=5000, level=10, race=0, ch_class=0)
    char.pcdata = PCData(points=40)

    result = do_worth(char, "")

    exp_per_lvl = 1000
    expected_exp_to_level = (10 + 1) * exp_per_lvl - 5000

    assert str(expected_exp_to_level) in result
    assert "6000 exp to level" in result or "(6000 exp" in result


def test_worth_exp_per_level_standard_character():
    """Test exp_per_level for standard character (40 points)."""
    char = Character(name="TestChar", is_npc=False, race=0, ch_class=0)
    char.pcdata = PCData(points=40)

    exp_per_lvl = _exp_per_level(char)

    assert exp_per_lvl == 1000


def test_worth_exp_per_level_optimized_character():
    """Test exp_per_level for optimized character (60 points)."""
    char = Character(name="TestChar", is_npc=False, race=0, ch_class=0)
    char.pcdata = PCData(points=60)

    exp_per_lvl = _exp_per_level(char)

    assert exp_per_lvl == 2000


def test_worth_exp_per_level_highly_optimized():
    """Test exp_per_level for highly optimized character (80 points)."""
    char = Character(name="TestChar", is_npc=False, race=0, ch_class=0)
    char.pcdata = PCData(points=80)

    exp_per_lvl = _exp_per_level(char)

    assert exp_per_lvl == 4000


def test_worth_exp_per_level_npc():
    """Test exp_per_level for NPCs always returns 1000."""
    mob = Character(name="TestMob", is_npc=True)

    exp_per_lvl = _exp_per_level(mob)

    assert exp_per_lvl == 1000


def test_worth_exp_per_level_with_class_multiplier():
    """Test exp_per_level applies race/class multiplier."""
    char = Character(name="TestChar", is_npc=False, race=1, ch_class=1)
    char.pcdata = PCData(points=40)

    exp_per_lvl = _exp_per_level(char)

    assert exp_per_lvl > 1000


def test_worth_integration_low_exp():
    """Test worth display with low experience (negative exp-to-level shouldn't occur)."""
    char = Character(name="TestChar", is_npc=False, gold=50, silver=25, exp=500, level=5, race=0, ch_class=0)
    char.pcdata = PCData(points=40)

    result = do_worth(char, "")

    assert "50 gold" in result
    assert "25 silver" in result
    assert "500 experience" in result


def test_worth_integration_high_level():
    """Test worth display with high level character."""
    char = Character(name="TestChar", is_npc=False, gold=10000, silver=5000, exp=500000, level=50, race=0, ch_class=0)
    char.pcdata = PCData(points=60)

    result = do_worth(char, "")

    assert "10000 gold" in result
    assert "5000 silver" in result
    assert "500000 experience" in result

    exp_to_level = (50 + 1) * 2000 - 500000
    assert str(exp_to_level) in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
