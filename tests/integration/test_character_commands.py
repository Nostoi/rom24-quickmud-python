"""
Integration tests for character customization commands.

ROM Reference: src/act_info.c lines 2297-2654
- do_compare (lines 2297-2395)
- do_title (lines 2547-2575)
- do_description (lines 2579-2654)

These tests verify ROM C behavioral parity for character customization.
"""

from __future__ import annotations

import pytest

from mud.commands.character import do_description, do_title
from mud.commands.compare import do_compare
from mud.models.character import Character
from mud.models.character import PCData
from mud.models.room import Room


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def test_room():
    """Create a test room."""
    room = Room(vnum=1, name="Test Room", description="A test room.")
    room.people = []
    yield room
    room.people.clear()


@pytest.fixture
def test_char(test_room):
    """Create a test character with pcdata."""
    char = Character(
        name="TestChar",
        level=10,
        room=test_room,
        is_npc=False,
        max_hit=100,
        hit=100,
        max_mana=100,
        mana=100,
        max_move=100,
        move=100,
    )
    char.pcdata = PCData()
    char.pcdata.title = ""
    char.description = ""
    char.act = 0
    char.comm = 0
    test_room.people.append(char)
    yield char
    if char in test_room.people:
        test_room.people.remove(char)


@pytest.fixture
def test_npc(test_room):
    """Create a test NPC (for negative tests)."""
    npc = Character(
        name="TestNPC",
        level=10,
        room=test_room,
        is_npc=True,
        max_hit=100,
        hit=100,
        max_mana=100,
        mana=100,
        max_move=100,
        move=100,
    )
    npc.act = 0
    npc.comm = 0
    test_room.people.append(npc)
    yield npc
    if npc in test_room.people:
        test_room.people.remove(npc)


# ============================================================================
# DO_COMPARE TESTS
# ============================================================================


class TestDoCompare:
    """Test do_compare command (ROM C lines 2297-2395)."""

    def test_compare_no_args(self, test_char):
        """
        Compare with no arguments shows error.

        ROM C: lines 2309-2313
        Expected: "Compare what to what?\n\r"
        """
        output = do_compare(test_char, "")
        assert "Compare what to what?" in output

    def test_compare_item_not_in_inventory(self, test_char):
        """
        Compare non-existent item shows error.

        ROM C: lines 2315-2319
        Expected: "You do not have that item.\n\r"
        """
        output = do_compare(test_char, "sword")
        assert "You do not have that item" in output


# ============================================================================
# DO_TITLE TESTS
# ============================================================================


class TestDoTitle:
    """Test do_title command (ROM C lines 2547-2575)."""

    def test_title_npc_returns_empty(self, test_npc):
        """
        NPCs can't set titles.

        ROM C: lines 2551-2552
        Expected: Returns without output
        """
        output = do_title(test_npc, "the Brave")
        assert output == ""

    def test_title_no_args(self, test_char):
        """
        Title with no args shows error.

        ROM C: lines 2566-2570
        Expected: "Change your title to what?\n\r"
        """
        output = do_title(test_char, "")
        assert "Change your title to what?" in output

    def test_title_set_success(self, test_char):
        """
        Setting title returns Ok and adds leading space.

        ROM C: lines 2572-2574 (do_title calls set_title)
        ROM C: lines 2529-2533 (set_title adds leading space)
        Expected: "Ok.\n\r" and title has leading space
        """
        output = do_title(test_char, "the Brave")
        assert output == "Ok."
        assert test_char.pcdata.title == " the Brave"

    def test_title_truncates_at_45_chars(self, test_char):
        """
        Title truncates at 45 characters (before adding space).

        ROM C: lines 2559-2560 (truncate to 45)
        ROM C: lines 2529-2533 (then add space if needed)
        Expected: argument[45] = '\0', then set_title adds space
        """
        long_title = "a" * 100
        output = do_title(test_char, long_title)
        assert output == "Ok."
        assert len(test_char.pcdata.title) == 46

    def test_title_removes_trailing_brace(self, test_char):
        """
        Remove trailing { if not escaped.

        ROM C: lines 2562-2564
        Expected: Removes trailing { unless preceded by {
        """
        # Single trailing { should be removed
        output = do_title(test_char, "the Brave{")
        assert output == "Ok."
        assert test_char.pcdata.title == " the Brave"  # set_title() adds leading space

        # Escaped {{ should NOT be removed
        output = do_title(test_char, "the Brave{{")
        assert output == "Ok."
        assert test_char.pcdata.title.endswith("{{")  # Escaped braces preserved
        assert test_char.pcdata.title == " the Brave{{"  # Full expectation with space


# ============================================================================
# DO_DESCRIPTION TESTS
# ============================================================================


class TestDoDescription:
    """Test do_description command (ROM C lines 2579-2654)."""

    def test_description_npc_returns_empty(self, test_npc):
        """
        NPCs can't set descriptions.

        ROM C: lines 2583 (implicit IS_NPC check in editor)
        Expected: Returns without output
        """
        output = do_description(test_npc, "test")
        assert output == ""

    def test_description_show_current_empty(self, test_char):
        """
        Show current description when empty.

        ROM C: lines 2651-2652
        Expected: "Your description is:\n\r(None).\n\r"
        """
        test_char.description = ""
        output = do_description(test_char, "")
        assert "Your description is:" in output
        assert "(None)" in output

    def test_description_show_current_nonempty(self, test_char):
        """
        Show current description when set.

        ROM C: lines 2651-2652
        Expected: Shows current description
        """
        test_char.description = "A brave warrior."
        output = do_description(test_char, "")
        assert "Your description is:" in output
        assert "A brave warrior" in output

    def test_description_set_new(self, test_char):
        """
        Set new description.

        ROM C: lines 2645-2648, 2651-2652
        Expected: Sets description and shows it
        """
        output = do_description(test_char, "A brave warrior.")
        assert test_char.description == "A brave warrior."

    def test_description_add_line(self, test_char):
        """
        Add line to description.

        ROM C: lines 2630-2637, 2645-2648, 2651-2652
        Expected: Adds line and shows full description
        """
        test_char.description = "A brave warrior."
        output = do_description(test_char, "+ He wields a mighty sword.")

        # Check description was appended
        assert "A brave warrior" in test_char.description
        assert "He wields a mighty sword" in test_char.description

    def test_description_remove_line_empty(self, test_char):
        """
        Remove line when description is empty.

        ROM C: lines 2593-2597
        Expected: "No lines left to remove.\n\r"
        """
        test_char.description = ""
        output = do_description(test_char, "-")
        assert "No lines left to remove" in output

    def test_description_remove_last_line(self, test_char):
        """
        Remove last line from description.

        ROM C: lines 2588-2628
        Expected: Removes last line and shows result
        """
        test_char.description = "Line 1\nLine 2\nLine 3"
        output = do_description(test_char, "-")

        # Should remove "Line 3"
        assert "Line 1" in test_char.description
        assert "Line 2" in test_char.description
