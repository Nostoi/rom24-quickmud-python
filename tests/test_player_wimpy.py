from __future__ import annotations

import pytest

from mud.commands.remaining_rom import do_wimpy
from mud.world import create_test_character, initialize_world
from mud.registry import area_registry, mob_registry, obj_registry, room_registry


@pytest.fixture(autouse=True)
def setup_world():
    initialize_world("area/area.lst")
    yield
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    room_registry.clear()


class TestWimpyCommand:
    def test_wimpy_default_is_max_hp_divided_by_5(self):
        player = create_test_character("Cautious", 3001)
        player.max_hit = 100

        output = do_wimpy(player, "")

        assert player.wimpy == 20
        assert "20" in output

    def test_wimpy_allows_zero(self):
        player = create_test_character("Brave", 3001)
        player.max_hit = 100

        output = do_wimpy(player, "0")

        assert player.wimpy == 0
        assert "0" in output

    def test_wimpy_max_is_half_max_hp(self):
        player = create_test_character("Coward", 3001)
        player.max_hit = 100

        output = do_wimpy(player, "60")

        assert "cowardice" in output.lower() or "ill becomes" in output.lower()
        assert player.wimpy != 60

    def test_wimpy_not_retroactively_clamped_when_max_hp_decreases(self):
        player = create_test_character("LevelUp", 3001)
        player.max_hit = 200

        do_wimpy(player, "90")
        assert player.wimpy == 90

        player.max_hit = 100

        assert player.wimpy == 90


class TestWimpyEdgeCases:
    def test_wimpy_negative_rejected(self):
        player = create_test_character("Test", 3001)
        player.max_hit = 100

        output = do_wimpy(player, "-10")

        assert "courage" in output.lower() or "wisdom" in output.lower()
        assert player.wimpy != -10

    def test_wimpy_invalid_input(self):
        player = create_test_character("Test", 3001)
        player.max_hit = 100
        player.wimpy = 50

        output = do_wimpy(player, "abc")

        assert "number" in output.lower()
        assert player.wimpy == 50

    def test_wimpy_preserves_existing_value_on_invalid_input(self):
        player = create_test_character("Test", 3001)
        player.max_hit = 100
        player.wimpy = 30

        do_wimpy(player, "invalid")

        assert player.wimpy == 30
