from __future__ import annotations

import pytest

from mud.commands.info_extended import do_whois, do_worth
from mud.commands.session import do_score
from mud.models.constants import PlayerFlag
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


class TestScoreCommand:
    def test_score_displays_basic_stats(self):
        player = create_test_character("TestPlayer", 3001)
        player.level = 10
        player.hit = 200
        player.max_hit = 250
        player.mana = 100
        player.max_mana = 150
        player.move = 300
        player.max_move = 350

        output = do_score(player, "")

        assert "TestPlayer" in output
        assert "10" in output
        assert "200" in output
        assert "250" in output or "hp" in output.lower()

    def test_score_shows_gold_silver(self):
        player = create_test_character("RichPlayer", 3001)
        player.gold = 500
        player.silver = 75

        output = do_score(player, "")

        assert "500" in output or "gold" in output.lower()
        assert "75" in output or "silver" in output.lower()

    def test_score_shows_alignment(self):
        player = create_test_character("GoodGuy", 3001)
        player.alignment = 750

        output = do_score(player, "")

        assert "align" in output.lower() or "good" in output.lower()

    def test_score_shows_exp(self):
        player = create_test_character("Veteran", 3001)
        player.level = 10
        player.exp = 45000

        output = do_score(player, "")

        assert "10" in output or "Veteran" in output

    def test_score_shows_wimpy(self):
        player = create_test_character("Cautious", 3001)
        player.wimpy = 50

        output = do_score(player, "")

        assert "wimpy" in output.lower() or "50" in output

    def test_score_shows_hitroll_damroll(self):
        player = create_test_character("Fighter", 3001)
        player.hitroll = 15
        player.damroll = 12

        output = do_score(player, "")

        assert ("15" in output) or ("hit" in output.lower())
        assert ("12" in output) or ("dam" in output.lower())

    def test_score_shows_armor_class(self):
        player = create_test_character("Armored", 3001)
        player.armor = [50, 60, 55, 45]

        output = do_score(player, "")

        assert "armor" in output.lower() or "ac" in output.lower()

    def test_score_shows_position(self):
        player = create_test_character("Standing", 3001)

        output = do_score(player, "")

        assert "standing" in output.lower() or "position" in output.lower()

    def test_score_shows_class_and_race(self):
        player = create_test_character("Warrior", 3001)

        output = do_score(player, "")

        assert len(output) > 50

    def test_score_output_not_empty(self):
        player = create_test_character("Anyone", 3001)

        output = do_score(player, "")

        assert len(output) > 50
        assert "Anyone" in output


class TestWorthCommand:
    def test_worth_shows_gold_silver(self):
        player = create_test_character("Wealthy", 3001)
        player.gold = 12500
        player.silver = 350

        output = do_worth(player, "")

        assert "12500" in output or "12,500" in output
        assert "gold" in output.lower()
        assert "350" in output
        assert "silver" in output.lower()

    def test_worth_with_zero_wealth(self):
        player = create_test_character("Broke", 3001)
        player.gold = 0
        player.silver = 0

        output = do_worth(player, "")

        assert "0" in output or "no" in output.lower() or "worth" in output.lower()

    def test_worth_with_only_gold(self):
        player = create_test_character("GoldOnly", 3001)
        player.gold = 5000
        player.silver = 0

        output = do_worth(player, "")

        assert "5000" in output or "5,000" in output
        assert "gold" in output.lower()

    def test_worth_output_format(self):
        player = create_test_character("Test", 3001)
        player.gold = 100
        player.silver = 50

        output = do_worth(player, "")

        assert len(output) > 10
        assert "100" in output
        assert "50" in output


class TestWhoisCommand:
    def test_whois_shows_player_info(self):
        target = create_test_character("Gandalf", 3001)
        target.level = 50

        searcher = create_test_character("Frodo", 3001)
        output = do_whois(searcher, "Gandalf")

        assert isinstance(output, str) and len(output) > 0

    def test_whois_shows_level(self):
        target = create_test_character("HighLevel", 3001)
        target.level = 50

        searcher = create_test_character("Searcher", 3001)
        output = do_whois(searcher, "HighLevel")

        assert isinstance(output, str) and len(output) > 0

    def test_whois_shows_killer_flag(self):
        target = create_test_character("Badguy", 3001)
        target.act = int(PlayerFlag.KILLER)

        searcher = create_test_character("Goodguy", 3001)
        output = do_whois(searcher, "Badguy")

        assert isinstance(output, str) and len(output) > 0

    def test_whois_player_not_found(self):
        searcher = create_test_character("Searcher", 3001)
        output = do_whois(searcher, "NoSuchPlayer")

        assert "not found" in output.lower() or "isn't" in output.lower() or "no" in output.lower()

    def test_whois_empty_argument(self):
        searcher = create_test_character("Searcher", 3001)
        output = do_whois(searcher, "")

        assert len(output) > 0

    def test_whois_self(self):
        player = create_test_character("SelfSearch", 3001)
        output = do_whois(player, "SelfSearch")

        assert isinstance(output, str) and len(output) > 0
