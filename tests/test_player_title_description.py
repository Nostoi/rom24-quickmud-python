from __future__ import annotations

import pytest

from mud.commands.character import do_description, do_title
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


class TestTitleCommand:
    def test_title_sets_custom_text(self):
        player = create_test_character("Heroic", 3001)

        output = do_title(player, "the Brave")

        assert player.pcdata is not None
        assert player.pcdata.title == "the Brave"
        assert "Ok" in output

    def test_title_enforces_45_char_limit(self):
        player = create_test_character("LongTitle", 3001)
        long_title = "a" * 60

        do_title(player, long_title)

        assert player.pcdata is not None
        assert player.pcdata.title is not None
        assert len(player.pcdata.title) == 45
        assert player.pcdata.title == "a" * 45

    def test_title_removes_dangling_opening_brace(self):
        player = create_test_character("ColorUser", 3001)
        title_with_brace = "the Brave {R(Legendary){x but this is cut{"

        do_title(player, title_with_brace)

        assert player.pcdata is not None
        assert player.pcdata.title is not None
        assert not player.pcdata.title.endswith("{")
        assert len(player.pcdata.title) <= 45

    def test_title_rejects_empty_string(self):
        player = create_test_character("NoTitle", 3001)
        assert player.pcdata is not None
        player.pcdata.title = "Old Title"

        output = do_title(player, "")

        assert "what" in output.lower() or "change" in output.lower()
        assert player.pcdata.title == "Old Title"

    def test_title_npc_cannot_set(self):
        player = create_test_character("NPC", 3001)
        player.is_npc = True

        output = do_title(player, "the Monster")

        assert output == ""


class TestDescriptionCommand:
    def test_description_set_full_text(self):
        player = create_test_character("Described", 3001)

        output = do_description(player, "A tall warrior with scars.")

        assert player.description == "A tall warrior with scars."
        assert "Ok" in output

    def test_description_add_line_with_plus(self):
        player = create_test_character("Builder", 3001)
        player.description = "First line"

        output = do_description(player, "+Second line")

        assert player.description == "First line\nSecond line"
        assert "Ok" in output

    def test_description_remove_line_with_minus(self):
        player = create_test_character("Remover", 3001)
        player.description = "Line 1\nLine 2\nLine 3"

        output = do_description(player, "-")

        assert player.description == "Line 1\nLine 2"

    def test_description_show_current_with_no_args(self):
        player = create_test_character("Viewer", 3001)
        player.description = "Current description text"

        output = do_description(player, "")

        assert "Current description text" in output
        assert "description" in output.lower()

    def test_description_show_none_when_empty(self):
        player = create_test_character("Empty", 3001)
        player.description = ""

        output = do_description(player, "")

        assert "None" in output or "description" in output.lower()

    def test_description_remove_from_empty_fails(self):
        player = create_test_character("Empty", 3001)
        player.description = ""

        output = do_description(player, "-")

        assert "No lines" in output or "remove" in output.lower()

    def test_description_add_to_empty_creates_first_line(self):
        player = create_test_character("New", 3001)
        player.description = ""

        do_description(player, "+First line ever")

        assert player.description == "First line ever"

    def test_description_npc_cannot_set(self):
        player = create_test_character("NPC", 3001)
        player.is_npc = True

        output = do_description(player, "A scary monster")

        assert output == ""


class TestTitleDescriptionEdgeCases:
    def test_title_with_color_codes(self):
        player = create_test_character("Colorful", 3001)

        do_title(player, "{Rthe Red{x Knight")

        assert player.pcdata is not None
        assert player.pcdata.title == "{Rthe Red{x Knight"

    def test_description_multiline_replacement(self):
        player = create_test_character("Multi", 3001)
        player.description = "Old line 1\nOld line 2"

        do_description(player, "Completely new single line")

        assert player.description == "Completely new single line"
        assert "\n" not in player.description
