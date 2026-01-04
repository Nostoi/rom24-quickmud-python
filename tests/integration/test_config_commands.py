"""
Integration tests for act_info.c config commands (Batch 4).

ROM Reference: src/act_info.c lines 558-950
Tests: do_scroll, do_show, do_prompt, do_autolist

These tests verify ROM C behavioral parity for player configuration commands.
"""

import pytest

from mud.commands.player_info import do_scroll, do_show
from mud.commands.auto_settings import do_prompt, do_autolist
from mud.models.character import Character
from mud.models.constants import CommFlag, PlayerFlag
from mud.models.room import Room


@pytest.fixture
def test_room():
    room = Room(
        vnum=3001,
        name="Test Room",
        description="A test room for integration tests.",
        sector_type=0,
    )
    room.people = []
    yield room
    room.people.clear()


@pytest.fixture
def test_char(test_room):
    char = Character(
        name="TestChar",
        level=1,
        room=test_room,
        is_npc=False,
    )
    char.act = 0
    char.comm = 0
    char.lines = 0
    test_room.people.append(char)
    yield char
    if char in test_room.people:
        test_room.people.remove(char)


@pytest.fixture
def test_npc(test_room):
    npc = Character(
        name="TestNPC",
        level=1,
        room=test_room,
        is_npc=True,
    )
    npc.act = 0
    npc.comm = 0
    test_room.people.append(npc)
    yield npc
    if npc in test_room.people:
        test_room.people.remove(npc)


# ============================================================================
# do_scroll() Tests - Set Lines Per Page (ROM C lines 558-604)
# ============================================================================


def test_scroll_show_default(test_char):
    """Scroll with no args shows current setting (ROM C line 566-577)."""
    # Default lines = 0
    test_char.lines = 0
    output = do_scroll(test_char, "")
    assert output == "You do not page long messages."


def test_scroll_set_valid(test_char):
    """Scroll with valid number sets lines - 2 (ROM C line 600-603)."""
    output = do_scroll(test_char, "20")
    assert output == "Scroll set to 20 lines."
    assert test_char.lines == 18, "ROM C stores input - 2"


def test_scroll_invalid_range(test_char):
    """Scroll rejects out-of-range values (ROM C line 594-598)."""
    output = do_scroll(test_char, "5")
    assert output == "You must provide a reasonable number."

    output = do_scroll(test_char, "150")
    assert output == "You must provide a reasonable number."


def test_scroll_disable(test_char):
    """Scroll 0 disables paging (ROM C line 587-592)."""
    test_char.lines = 20
    output = do_scroll(test_char, "0")
    assert output == "Paging disabled."
    assert test_char.lines == 0


def test_scroll_non_numeric(test_char):
    """Scroll rejects non-numeric input (ROM C line 579-583)."""
    output = do_scroll(test_char, "abc")
    assert output == "You must provide a number."


# ============================================================================
# do_show() Tests - Toggle Affects in Score (ROM C lines 905-918)
# ============================================================================


def test_show_toggle_on(test_char):
    """Show toggles affects display ON (ROM C line 912-916)."""
    test_char.comm = 0  # Flag OFF
    output = do_show(test_char, "")
    assert output == "Affects will now be shown in score."
    assert test_char.comm & CommFlag.SHOW_AFFECTS, "COMM_SHOW_AFFECTS should be set"


def test_show_toggle_off(test_char):
    """Show toggles affects display OFF (ROM C line 907-911)."""
    test_char.comm = CommFlag.SHOW_AFFECTS  # Flag ON
    output = do_show(test_char, "")
    assert output == "Affects will no longer be shown in score."
    assert not (test_char.comm & CommFlag.SHOW_AFFECTS), "COMM_SHOW_AFFECTS should be removed"


# ============================================================================
# do_prompt() Tests - Toggle/Set Prompt (ROM C lines 919-956)
# ============================================================================


def test_prompt_toggle_on(test_char):
    """Prompt with no args toggles prompt ON (ROM C line 930-934)."""
    test_char.comm = 0  # Flag OFF
    output = do_prompt(test_char, "")
    assert output == "You will now see prompts."
    assert test_char.comm & CommFlag.PROMPT, "COMM_PROMPT should be set"


def test_prompt_toggle_off(test_char):
    """Prompt with no args toggles prompt OFF (ROM C line 925-929)."""
    test_char.comm = CommFlag.PROMPT  # Flag ON
    output = do_prompt(test_char, "")
    assert output == "You will no longer see prompts."
    assert not (test_char.comm & CommFlag.PROMPT), "COMM_PROMPT should be removed"


def test_prompt_set_all(test_char):
    """Prompt all sets default full prompt (ROM C line 938-939)."""

    # Create pcdata object for test_char
    class PCData:
        prompt = ""

    test_char.pcdata = PCData()
    test_char.comm = 0

    output = do_prompt(test_char, "all")
    assert "Prompt set" in output
    assert test_char.pcdata.prompt == "<%hhp %mm %vmv> ", "Default prompt should match ROM C"
    assert test_char.comm & CommFlag.PROMPT, "COMM_PROMPT should be set"


def test_prompt_custom(test_char):
    """Prompt with custom string sets custom prompt (ROM C line 941-953)."""

    class PCData:
        prompt = ""

    test_char.pcdata = PCData()
    test_char.comm = 0

    output = do_prompt(test_char, "<%h hp>")
    assert "Prompt set" in output
    assert test_char.pcdata.prompt == "<%h hp>", "Custom prompt should be stored"
    assert test_char.comm & CommFlag.PROMPT, "COMM_PROMPT should be set"


# ============================================================================
# do_autolist() Tests - List Auto-Settings (ROM C lines 659-742)
# ============================================================================


def test_autolist_format(test_char):
    """Autolist shows header and divider (ROM C line 665-666)."""
    test_char.is_npc = False
    test_char.act = 0
    test_char.comm = 0

    output = do_autolist(test_char, "")
    lines = output.split("\n")

    assert lines[0] == "   action     status", "Header line should match ROM C"
    assert lines[1] == "---------------------", "Divider should match ROM C"


def test_autolist_flags_on(test_char):
    """Autolist shows ON for enabled flags (ROM C line 668-726)."""
    test_char.is_npc = False
    # Enable all auto flags
    test_char.act = (
        PlayerFlag.AUTOASSIST
        | PlayerFlag.AUTOEXIT
        | PlayerFlag.AUTOGOLD
        | PlayerFlag.AUTOLOOT
        | PlayerFlag.AUTOSAC
        | PlayerFlag.AUTOSPLIT
    )
    test_char.comm = CommFlag.TELNET_GA | CommFlag.COMPACT | CommFlag.PROMPT | CommFlag.COMBINE

    output = do_autolist(test_char, "")

    # All settings should show {GON{x (ROM C format, no closing })
    assert output.count("{GON{x") == 10, "All 10 flags should show ON"
    assert "{ROFF{x" not in output, "No flags should show OFF"


def test_autolist_flags_off(test_char):
    """Autolist shows OFF for disabled flags (ROM C line 668-726)."""
    test_char.is_npc = False
    test_char.act = 0
    test_char.comm = 0

    output = do_autolist(test_char, "")

    # All settings should show {ROFF{x (ROM C format, no closing })
    assert output.count("{ROFF{x") == 10, "All 10 flags should show OFF"
    assert "{GON{x" not in output, "No flags should show ON"


def test_autolist_extra_info(test_char):
    """Autolist shows extra info for CANLOOT/NOSUMMON/NOFOLLOW (ROM C line 728-742)."""
    test_char.is_npc = False
    test_char.act = 0  # CANLOOT not set
    test_char.comm = 0

    output = do_autolist(test_char, "")

    # CANLOOT not set -> corpse is safe
    assert "Your corpse is safe from thieves." in output, "ROM C line 729"

    # NOSUMMON not set -> can be summoned
    assert "You can be summoned." in output, "ROM C line 736"

    # NOFOLLOW not set -> accept followers
    assert "You accept followers." in output, "ROM C line 741"


def test_autolist_extra_info_inverted(test_char):
    """Autolist shows inverted messages when flags are set (ROM C line 728-742)."""
    test_char.is_npc = False
    # Set all three flags
    test_char.act = PlayerFlag.CANLOOT | PlayerFlag.NOSUMMON | PlayerFlag.NOFOLLOW
    test_char.comm = 0

    output = do_autolist(test_char, "")

    # CANLOOT set -> corpse may be looted
    assert "Your corpse may be looted." in output, "ROM C line 731"

    # NOSUMMON set -> cannot be summoned
    assert "You cannot be summoned." in output, "ROM C line 734"

    # NOFOLLOW set -> do not welcome followers
    assert "You do not welcome followers." in output, "ROM C line 739"


def test_autolist_npc_returns_empty(test_npc):
    """NPCs can't use autolist (ROM C line 662-663)."""
    test_npc.is_npc = True
    output = do_autolist(test_npc, "")
    assert output == "", "NPCs should get empty string"


# ============================================================================
# Edge Cases & ROM C Parity Verification
# ============================================================================


def test_scroll_shows_adjusted_value(test_char):
    """Scroll shows input value, stores input - 2 (ROM C line 572-573, 602)."""
    test_char.lines = 18  # Stored as 20 - 2
    output = do_scroll(test_char, "")
    assert "20 lines per page" in output, "Should show stored value + 2"


def test_autolist_compact_flag_correct(test_char):
    """Autolist uses COMM_COMPACT for compact mode, not COMM_COMBINE (ROM C line 711)."""
    test_char.is_npc = False
    test_char.act = 0
    test_char.comm = CommFlag.COMPACT

    output = do_autolist(test_char, "")
    lines = output.split("\n")

    compact_line = [line for line in lines if "compact mode" in line][0]
    combine_line = [line for line in lines if "combine items" in line][0]

    assert "{GON{x" in compact_line, "compact mode should be ON"
    assert "{ROFF{x" in combine_line, "combine items should be OFF"


def test_prompt_enables_flag_on_custom(test_char):
    """Setting custom prompt enables COMM_PROMPT flag (ROM C behavior)."""

    class PCData:
        prompt = ""

    test_char.pcdata = PCData()
    test_char.comm = 0  # Flag OFF

    do_prompt(test_char, "test")
    assert test_char.comm & CommFlag.PROMPT, "Custom prompt should enable COMM_PROMPT"
