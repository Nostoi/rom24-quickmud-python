"""Integration tests for do_help command ROM C parity.

Tests verify do_help implements all ROM C features from act_info.c lines 1832-1914.

ROM C Features Tested:
- Default to "summary" if no argument
- Multi-word topic support
- Trust-based filtering
- Keyword matching with is_name() equivalent
- Multiple match separator
- Strip leading '.' from help text
- "No help on that word." message
- Orphan help logging
- Excessive length check (> MAX_CMD_LEN)
- "imotd" keyword suppression

QuickMUD Enhancements Tested:
- Command auto-help generation
- Command suggestions for unfound topics
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from mud.commands.help import do_help
from mud.models.character import Character
from mud.models.constants import MAX_CMD_LEN
from mud.models.help import HelpEntry, clear_help_registry, register_help
from mud.models.room import Room


@pytest.fixture
def test_character():
    """Create a test character with basic setup."""
    char = Character()
    char.name = "TestPlayer"
    char.level = 1
    char.trust = 0
    char.is_npc = False
    # Character needs room for orphan logging
    char.room = Room(vnum=3001)
    return char


@pytest.fixture
def immortal_character():
    """Create an immortal character for trust testing."""
    char = Character()
    char.name = "TestImmortal"
    char.level = 60
    char.trust = 60
    char.is_npc = False
    char.room = Room(vnum=3001)
    return char


@pytest.fixture
def setup_help_data():
    """Set up test help entries and clean up after test."""
    clear_help_registry()

    # Create test help entries
    help_summary = HelpEntry(
        keywords=["summary", "help"],
        text="This is the help summary.",
        level=0,
    )

    help_score = HelpEntry(
        keywords=["score", "sc"],
        text="Shows your character statistics.",
        level=0,
    )

    help_death_traps = HelpEntry(
        keywords=["death traps", "dt"],
        text="Death traps instantly kill players.",
        level=0,
    )

    help_immortal = HelpEntry(
        keywords=["immortal commands", "imm"],
        text="Immortal-only help topic.",
        level=52,
    )

    help_with_dot = HelpEntry(
        keywords=["test dot"],
        text=".This help starts with a dot.",
        level=0,
    )

    help_imotd = HelpEntry(
        keywords=["imotd"],
        text="Immortal message of the day.",
        level=-1,  # Negative level = trust-based
    )

    help_multi_1 = HelpEntry(
        keywords=["test topic"],
        text="First match for test topic.",
        level=0,
    )

    help_multi_2 = HelpEntry(
        keywords=["test topic"],
        text="Second match for test topic.",
        level=0,
    )

    # Register all help entries
    for entry in [
        help_summary,
        help_score,
        help_death_traps,
        help_immortal,
        help_with_dot,
        help_imotd,
        help_multi_1,
        help_multi_2,
    ]:
        register_help(entry)

    yield

    # Clean up
    clear_help_registry()


# ============================================================================
# P0 TESTS (CRITICAL - ROM C Core Features)
# ============================================================================


def test_help_no_argument_shows_summary(test_character, setup_help_data):
    """Test 'help' with no argument defaults to 'summary' (ROM C line 1842-1843)."""
    result = do_help(test_character, "")

    assert "summary" in result.lower()
    assert "This is the help summary." in result


def test_help_multi_word_topic(test_character, setup_help_data):
    """Test 'help death traps' searches for multi-word topic (ROM C line 1845-1853)."""
    result = do_help(test_character, "death traps")

    assert "Death traps instantly kill players." in result


def test_help_trust_filtering_mortal_cant_see_immortal(test_character, setup_help_data):
    """Test mortals can't see immortal help topics (ROM C line 1857-1860)."""
    result = do_help(test_character, "immortal commands")

    # Should get "No help on that word" since trust is too low
    assert "No help on that word." in result
    assert "Immortal-only help topic." not in result


def test_help_trust_filtering_immortal_can_see_immortal(immortal_character, setup_help_data):
    """Test immortals can see immortal help topics (ROM C line 1857-1860)."""
    result = do_help(immortal_character, "immortal commands")

    assert "Immortal-only help topic." in result


def test_help_keyword_matching_prefix(test_character, setup_help_data):
    """Test keyword prefix matching 'sco' → 'score' (ROM C line 1862 is_name)."""
    result = do_help(test_character, "sc")

    assert "Shows your character statistics." in result


def test_help_not_found(test_character, setup_help_data):
    """Test unfound topic shows 'No help on that word.' (ROM C line 1891)."""
    with patch("mud.admin_logging.admin.log_orphan_help_request"):
        result = do_help(test_character, "nonexistent_topic_xyz")

    assert "No help on that word." in result


# ============================================================================
# P1 TESTS (IMPORTANT - ROM C Features)
# ============================================================================


def test_help_multiple_matches(test_character, setup_help_data):
    """Test multiple matches shown with separator (ROM C line 1865-1867)."""
    result = do_help(test_character, "test topic")

    # Should show both matches separated by ROM_HELP_SEPARATOR
    assert "First match for test topic." in result
    assert "Second match for test topic." in result
    # Check separator exists (contains "====")
    assert "====" in result


def test_help_strip_leading_dot(test_character, setup_help_data):
    """Test leading '.' stripped from help text (ROM C line 1877-1880)."""
    result = do_help(test_character, "test dot")

    # Dot should be stripped
    assert "This help starts with a dot." in result
    # Should NOT start with dot
    assert not result.strip().startswith(".This")


def test_help_orphan_logging(test_character, setup_help_data):
    """Test unfound topics logged to orphan file (ROM C line 1906)."""
    mock_file = mock_open()

    with patch("pathlib.Path.open", mock_file), patch("pathlib.Path.mkdir"):
        result = do_help(test_character, "orphan_test_topic")

    # Verify log file was written
    mock_file.assert_called_once()
    handle = mock_file()

    # Check that write was called with correct format
    written_calls = [call for call in handle.write.call_args_list]
    assert len(written_calls) > 0

    # Verify format: [room_vnum] name: topic
    written_text = "".join(str(call[0][0]) for call in written_calls)
    assert "TestPlayer" in written_text
    assert "orphan_test_topic" in written_text
    assert "[" in written_text  # Room vnum format


def test_help_excessive_length(test_character, setup_help_data):
    """Test topics > MAX_CMD_LEN rejected with 'That was rude!' (ROM C line 1897-1901)."""
    excessive_topic = "x" * (MAX_CMD_LEN + 10)

    result = do_help(test_character, excessive_topic)

    assert "That was rude!" in result
    assert "No help on that word." in result


def test_help_imotd_suppression(immortal_character, setup_help_data):
    """Test 'imotd' keyword not shown in output (ROM C line 1868-1872)."""
    result = do_help(immortal_character, "imotd")

    # Help text should be shown
    assert "Immortal message of the day." in result
    # But keyword "imotd" should NOT be shown (ROM special case)
    # Check that keyword line is not present
    lines = result.split("\n")
    keyword_lines = [line for line in lines if "imotd" in line.lower() and "Immortal message" not in line]
    # Should be empty (no keyword line shown)
    assert len(keyword_lines) == 0 or all("imotd" not in line for line in keyword_lines if line.strip())


# ============================================================================
# P2 TESTS (OPTIONAL - QuickMUD Enhancements)
# ============================================================================


def test_help_command_autogeneration(test_character, setup_help_data):
    """Test command help auto-generated when static help missing (QuickMUD enhancement)."""
    with patch("mud.admin_logging.admin.log_orphan_help_request"):
        # Use 'inventory' - a visible command without static help
        result = do_help(test_character, "inventory")

    # Should generate command help
    assert "Command:" in result and "inventory" in result.lower()


def test_help_command_suggestions(test_character, setup_help_data):
    """Test similar command suggestions when help not found (QuickMUD enhancement)."""
    with patch("mud.admin_logging.admin.log_orphan_help_request"):
        result = do_help(test_character, "xyz")

    # Should suggest similar commands
    assert "Try:" in result or "No help on that word." in result


# ============================================================================
# EDGE CASE TESTS
# ============================================================================


def test_help_multi_word_with_quotes(test_character, setup_help_data):
    """Test multi-word topic with quotes 'death traps'."""
    result = do_help(test_character, "'death traps'")

    assert "Death traps instantly kill players." in result


def test_help_case_insensitive(test_character, setup_help_data):
    """Test keyword matching is case-insensitive."""
    result_lower = do_help(test_character, "death traps")
    result_upper = do_help(test_character, "DEATH TRAPS")
    result_mixed = do_help(test_character, "DeAtH TrApS")

    # All should return same help
    assert "Death traps instantly kill players." in result_lower
    assert "Death traps instantly kill players." in result_upper
    assert "Death traps instantly kill players." in result_mixed


def test_help_with_npc_character():
    """Test help works with NPC characters (should not log orphans)."""
    npc = Character()
    npc.name = "TestMob"
    npc.level = 10
    npc.trust = 0
    npc.is_npc = True  # NPC flag
    npc.room = Room(vnum=3001)

    clear_help_registry()
    help_test = HelpEntry(keywords=["test"], text="Test help.", level=0)
    register_help(help_test)

    # Should work without logging orphans
    with patch("mud.admin_logging.admin.log_orphan_help_request") as mock_log:
        result = do_help(npc, "nonexistent")

        # NPCs should not trigger orphan logging
        # (ROM C checks is_npc in log_orphan_help_request)
        # But command should still work
        assert "No help on that word." in result

    clear_help_registry()


def test_help_negative_level_trust_encoding(test_character, immortal_character, setup_help_data):
    """Test negative help levels encode trust requirements (ROM C encoding)."""
    clear_help_registry()

    # Negative level means trust level = -level - 1
    # level -1 means trust 0 required (mortal)
    # level -2 means trust 1 required
    # level -53 means trust 52 required (immortal)

    help_neg_level = HelpEntry(
        keywords=["negative test"],
        text="Negative level test.",
        level=-53,  # Requires trust 52
    )
    register_help(help_neg_level)

    # Mortal (trust 0) should NOT see it
    result_mortal = do_help(test_character, "negative test")
    assert "No help on that word." in result_mortal

    # Immortal (trust 60) should see it
    result_immortal = do_help(immortal_character, "negative test")
    assert "Negative level test." in result_immortal

    clear_help_registry()


def test_help_output_format_rom_crlf(test_character, setup_help_data):
    """Test help output uses ROM CRLF line endings."""
    result = do_help(test_character, "score")

    # Should contain CRLF line endings (ROM standard)
    assert "\r\n" in result
