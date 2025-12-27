from __future__ import annotations

import pytest

from mud.commands.auto_settings import do_autoall, do_autoloot, do_autogold, do_autosac, do_autosplit
from mud.models.constants import PlayerFlag
from mud.world import create_test_character, initialize_world
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from helpers_player import enable_autos


@pytest.fixture(autouse=True)
def setup_world():
    initialize_world("area/area.lst")
    yield
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    room_registry.clear()


class TestAutoSequenceToggling:
    def test_autoall_on_enables_all_auto_flags(self):
        player = create_test_character("All", 3001)
        player.act = 0

        output = do_autoall(player, "on")

        act = player.act
        assert act & PlayerFlag.AUTOLOOT
        assert act & PlayerFlag.AUTOGOLD
        assert act & PlayerFlag.AUTOSAC
        assert act & PlayerFlag.AUTOSPLIT
        assert "all" in output.lower() or "on" in output.lower()

    def test_autoall_off_disables_all_auto_flags(self):
        player = create_test_character("None", 3001)
        enable_autos(player, autoloot=True, autogold=True, autosac=True, autosplit=True)

        output = do_autoall(player, "off")

        act = player.act
        assert not (act & PlayerFlag.AUTOLOOT)
        assert not (act & PlayerFlag.AUTOGOLD)
        assert not (act & PlayerFlag.AUTOSAC)
        assert not (act & PlayerFlag.AUTOSPLIT)
        assert "off" in output.lower()

    def test_autoloot_toggle_independent_of_others(self):
        player = create_test_character("Looter", 3001)
        enable_autos(player, autogold=True, autosac=True)
        initial_act = player.act

        do_autoloot(player, "")

        assert player.act & PlayerFlag.AUTOLOOT
        assert player.act & PlayerFlag.AUTOGOLD
        assert player.act & PlayerFlag.AUTOSAC

    def test_autogold_independent_toggle(self):
        player = create_test_character("GoldOnly", 3001)
        enable_autos(player, autoloot=True)

        do_autogold(player, "")

        assert player.act & PlayerFlag.AUTOLOOT
        assert player.act & PlayerFlag.AUTOGOLD

    def test_autosac_independent_toggle(self):
        player = create_test_character("Sacker", 3001)
        player.act = 0

        do_autosac(player, "")

        assert player.act & PlayerFlag.AUTOSAC
        assert not (player.act & PlayerFlag.AUTOLOOT)
        assert not (player.act & PlayerFlag.AUTOGOLD)

    def test_autosplit_independent_toggle(self):
        player = create_test_character("Splitter", 3001)
        player.act = 0

        do_autosplit(player, "")

        assert player.act & PlayerFlag.AUTOSPLIT
        assert not (player.act & PlayerFlag.AUTOLOOT)


class TestAutoFlagCombinations:
    def test_loot_and_sac_combination(self):
        player = create_test_character("LootSac", 3001)
        enable_autos(player, autoloot=True, autosac=True)

        act = player.act
        assert act & PlayerFlag.AUTOLOOT
        assert act & PlayerFlag.AUTOSAC
        assert not (act & PlayerFlag.AUTOGOLD)

    def test_gold_and_sac_without_loot(self):
        player = create_test_character("GoldSac", 3001)
        enable_autos(player, autogold=True, autosac=True, autoloot=False)

        act = player.act
        assert not (act & PlayerFlag.AUTOLOOT)
        assert act & PlayerFlag.AUTOGOLD
        assert act & PlayerFlag.AUTOSAC

    def test_all_four_auto_flags_enabled(self):
        player = create_test_character("AllFour", 3001)
        enable_autos(player, autoloot=True, autogold=True, autosac=True, autosplit=True)

        act = player.act
        assert act & PlayerFlag.AUTOLOOT
        assert act & PlayerFlag.AUTOGOLD
        assert act & PlayerFlag.AUTOSAC
        assert act & PlayerFlag.AUTOSPLIT

    def test_toggle_off_preserves_other_flags(self):
        player = create_test_character("Toggle", 3001)
        enable_autos(player, autoloot=True, autogold=True, autosac=True)

        do_autogold(player, "")

        act = player.act
        assert act & PlayerFlag.AUTOLOOT
        assert not (act & PlayerFlag.AUTOGOLD)
        assert act & PlayerFlag.AUTOSAC
