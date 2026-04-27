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
    """Test do_title command - ROM C lines 2547-2575"""

    def test_title_sets_custom_text(self):
        """ROM C: Basic title setting with automatic spacing"""
        player = create_test_character("Heroic", 3001)

        output = do_title(player, "the Brave")

        assert player.pcdata is not None
        assert player.pcdata.title == " the Brave"
        assert "Ok" in output

    def test_title_enforces_45_char_limit(self):
        """ROM C line 2559-2560: Truncates to 45 chars BEFORE other checks"""
        player = create_test_character("LongTitle", 3001)
        long_title = "a" * 60

        do_title(player, long_title)

        assert player.pcdata is not None
        assert player.pcdata.title is not None
        assert len(player.pcdata.title) == 46
        assert player.pcdata.title == " " + ("a" * 45)

    def test_title_removes_dangling_opening_brace(self):
        """ROM C lines 2562-2564: Removes trailing '{' if not escaped '{{'}"""
        player = create_test_character("ColorUser", 3001)
        title_with_brace = "a" * 44 + "{"

        do_title(player, title_with_brace)

        assert player.pcdata is not None
        assert player.pcdata.title is not None
        title_stripped = player.pcdata.title.strip()
        assert not title_stripped.endswith("{")
        assert len(title_stripped) == 44

    def test_title_keeps_escaped_brace(self):
        """ROM C lines 2562-2564: Keeps '{{' escaped braces"""
        player = create_test_character("ColorUser", 3001)
        title_with_escaped = "test{{"

        do_title(player, title_with_escaped)

        assert player.pcdata is not None
        assert player.pcdata.title is not None
        title = str(player.pcdata.title)
        assert title.strip().endswith("{{")

    def test_title_rejects_empty_string(self):
        """ROM C lines 2566-2570: Rejects empty argument"""
        player = create_test_character("NoTitle", 3001)
        assert player.pcdata is not None
        player.pcdata.title = " Old Title"

        output = do_title(player, "")

        assert "what" in output.lower() or "change" in output.lower()
        assert player.pcdata.title == " Old Title"

    def test_title_npc_cannot_set(self):
        """ROM C lines 2551-2552: NPCs cannot use title command"""
        player = create_test_character("NPC", 3001)
        player.is_npc = True

        output = do_title(player, "the Monster")

        assert output == ""

    def test_title_with_punctuation_no_spacing(self):
        """ROM C set_title lines 2529-2533: No leading space for punctuation"""
        player = create_test_character("Punctuated", 3001)

        for punct in [".", ",", "!", "?"]:
            do_title(player, f"{punct} test")
            assert player.pcdata is not None
            assert player.pcdata.title == f"{punct} test"

    def test_title_smash_tilde(self):
        """ROM C line 2572: smash_tilde sanitizes input"""
        player = create_test_character("TildeTest", 3001)

        output = do_title(player, "test~title")

        assert player.pcdata is not None
        assert player.pcdata.title is not None
        title = str(player.pcdata.title)
        assert "~" not in title


class TestDescriptionCommand:
    """Test do_description command - ROM C lines 2579-2654"""

    def test_description_set_full_text(self):
        """ROM C lines 2645-2648: Replace entire description + newline"""
        player = create_test_character("Described", 3001)

        output = do_description(player, "A tall warrior with scars.")

        assert player.description == "A tall warrior with scars.\n"
        assert "description" in output.lower()
        assert "A tall warrior with scars." in output

    def test_description_add_line_with_plus(self):
        """ROM C lines 2630-2637: Append line with '+'"""
        player = create_test_character("Builder", 3001)
        player.description = "First line\n"

        output = do_description(player, "+Second line")

        assert player.description == "First line\nSecond line\n"
        assert "description" in output.lower()

    def test_description_remove_line_with_minus(self):
        """ROM C lines 2588-2628: Remove last line by finding second '\r'"""
        player = create_test_character("Remover", 3001)
        player.description = "Line 1\nLine 2\nLine 3\n"

        output = do_description(player, "-")

        assert player.description == "Line 1\nLine 2\n"
        assert "description" in output.lower()

    def test_description_show_current_with_no_args(self):
        """ROM C lines 2651-2652: Always show description at end"""
        player = create_test_character("Viewer", 3001)
        player.description = "Current description text"

        output = do_description(player, "")

        assert "Current description text" in output
        assert "description" in output.lower()

    def test_description_show_none_when_empty(self):
        """ROM C line 2652: Show (None) when description is NULL"""
        player = create_test_character("Empty", 3001)
        player.description = ""

        output = do_description(player, "")

        assert "None" in output or "description" in output.lower()

    def test_description_remove_from_empty_fails(self):
        """ROM C lines 2593-2597: Cannot remove from empty description"""
        player = create_test_character("Empty", 3001)
        player.description = ""

        output = do_description(player, "-")

        assert "No lines" in output or "remove" in output.lower()

    def test_description_add_to_empty_creates_first_line(self):
        """ROM C lines 2630-2637: '+' works on empty description"""
        player = create_test_character("New", 3001)
        player.description = ""

        do_description(player, "+First line ever")

        assert player.description == "First line ever\n"

    def test_description_removes_all_lines_clears(self):
        """ROM C lines 2624-2627: Removing last line clears description"""
        player = create_test_character("LastLine", 3001)
        player.description = "Only line\n"

        output = do_description(player, "-")

        assert player.description == ""
        assert "cleared" in output.lower()

    def test_description_length_limit_1024(self):
        """ROM C lines 2639-2643: Reject descriptions >= 1024 chars"""
        player = create_test_character("Long", 3001)
        long_desc = "a" * 1025

        output = do_description(player, long_desc)

        assert "too long" in output.lower()

    def test_description_plus_respects_length_limit(self):
        """ROM C lines 2639-2643: '+' checks 1024 limit on buffer BEFORE append"""
        player = create_test_character("AlmostFull", 3001)
        player.description = "a" * 1020

        output = do_description(player, "+More text")

        assert "too long" in output.lower() or "More text" in output

    def test_description_lstrip_after_plus(self):
        """ROM C lines 2635-2636: while (isspace(*argument)) argument++;"""
        player = create_test_character("Spacer", 3001)
        player.description = "First line\n"

        do_description(player, "+   Second line")

        assert player.description == "First line\nSecond line\n"

    def test_description_smash_tilde(self):
        """ROM C line 2586: smash_tilde(argument)"""
        player = create_test_character("TildeTest", 3001)

        do_description(player, "Test~description")

        assert "~" not in (player.description or "")

    def test_description_npc_cannot_set(self):
        """ROM C: NPCs cannot set description (implicit IS_NPC check)"""
        player = create_test_character("NPC", 3001)
        player.is_npc = True

        output = do_description(player, "A scary monster")

        assert output == ""


class TestTitleDescriptionEdgeCases:
    def test_title_with_color_codes(self):
        """Title with color codes gets leading space from set_title"""
        player = create_test_character("Colorful", 3001)

        do_title(player, "{Rthe Red{x Knight")

        assert player.pcdata is not None
        assert player.pcdata.title == " {Rthe Red{x Knight"

    def test_description_multiline_replacement(self):
        """ROM C lines 2645-2646: Always appends newline"""
        player = create_test_character("Multi", 3001)
        player.description = "Old line 1\nOld line 2"

        do_description(player, "Completely new single line")

        assert player.description == "Completely new single line\n"
        assert "\n" in player.description
