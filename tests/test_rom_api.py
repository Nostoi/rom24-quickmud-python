"""
Tests for ROM API public wrapper functions.

Validates that ROM C-compatible public API wrappers correctly delegate
to underlying Python implementations.
"""

from __future__ import annotations

import pytest


def test_board_lookup_finds_existing_board():
    """Test board_lookup wrapper finds board by name."""
    from mud.notes import get_board
    from mud.rom_api import board_lookup
    from mud.world.world_state import initialize_world

    initialize_world(use_json=True)

    # Create the board first
    get_board("general", description="General discussion", read_level=0, write_level=0)

    board = board_lookup("general")
    assert board is not None
    assert board.name == "general"


def test_board_number_is_alias_for_lookup():
    """Test board_number is compatible alias for board_lookup."""
    from mud.rom_api import board_lookup, board_number
    from mud.world.world_state import initialize_world

    initialize_world(use_json=True)

    board1 = board_lookup("general")
    board2 = board_number("general")

    assert board1 == board2


def test_note_from_returns_sender():
    """Test note_from wrapper extracts sender name."""
    from mud.models.note import Note
    from mud.rom_api import note_from

    note = Note(sender="TestPlayer", to="all", subject="Test Note", text="This is a test", timestamp=1.0)

    assert note_from(note) == "TestPlayer"


def test_do_ncatchup_marks_all_read(movable_char_factory):
    """Test do_ncatchup wrapper marks notes as read."""
    from mud.notes import get_board
    from mud.rom_api import do_ncatchup
    from mud.world.world_state import initialize_world

    initialize_world(use_json=True)
    char = movable_char_factory("TestChar", 3001)

    board = get_board("general", description="General discussion", read_level=0, write_level=0)
    board.post("TestAuthor", "Test Subject", "Test message")

    result = do_ncatchup(char)
    assert "skipped" in result.lower() or "caught up" in result.lower() or "marked" in result.lower()


def test_do_nlist_shows_notes(movable_char_factory):
    """Test do_nlist wrapper displays note list."""
    from mud.rom_api import do_nlist
    from mud.world.world_state import initialize_world

    initialize_world(use_json=True)
    char = movable_char_factory("TestChar", 3001)

    result = do_nlist(char)
    assert result  # Should return some output


def test_check_blind_returns_visibility(movable_char_factory):
    """Test check_blind wrapper checks character vision."""
    from mud.rom_api import check_blind
    from mud.world.world_state import initialize_world

    initialize_world(use_json=True)
    char = movable_char_factory("TestChar", 3001)

    can_see = check_blind(char)
    assert isinstance(can_see, bool)
    assert can_see is True  # Normal character can see


def test_mult_argument_parses_quantity():
    """Test mult_argument wrapper parses quantity from argument."""
    from mud.rom_api import mult_argument

    quantity, item = mult_argument("5.sword", "5")
    assert quantity >= 1
    assert "sword" in item.lower() or item == "5.sword"


def test_show_flag_cmds_lists_flags():
    """Test show_flag_cmds wrapper displays room flags."""
    from mud.rom_api import show_flag_cmds

    result = show_flag_cmds()
    assert "flag" in result.lower()
    assert len(result) > 0


def test_wear_loc_lookup_finds_location():
    """Test wear_loc_lookup wrapper resolves wear locations."""
    from mud.rom_api import wear_loc_lookup

    loc = wear_loc_lookup("head")
    assert loc is not None

    invalid = wear_loc_lookup("invalid_location_xyz")
    assert invalid is None


def test_show_liqlist_displays_liquids():
    """Test show_liqlist displays liquid types."""
    from mud.rom_api import show_liqlist

    result = show_liqlist()
    assert "liquid" in result.lower()
    assert "water" in result.lower()
    assert len(result) > 0


def test_show_damlist_displays_damage_types():
    """Test show_damlist displays damage types."""
    from mud.rom_api import show_damlist

    result = show_damlist()
    assert "damage" in result.lower()
    assert len(result) > 0


def test_show_skill_cmds_displays_skills():
    """Test show_skill_cmds displays skill list."""
    from mud.rom_api import show_skill_cmds
    from mud.world.world_state import initialize_world

    initialize_world(use_json=True)

    result = show_skill_cmds()
    assert "skill" in result.lower()
    assert len(result) > 0


def test_show_spec_cmds_displays_specs():
    """Test show_spec_cmds displays special functions."""
    from mud.rom_api import show_spec_cmds

    result = show_spec_cmds()
    assert "spec" in result.lower()
    assert len(result) > 0


def test_recursive_clone_duplicates_object(object_factory):
    """Test recursive_clone deep clones objects."""
    from mud.rom_api import recursive_clone

    original = object_factory({"vnum": 1001, "name": "test sword", "short_descr": "a test sword"})

    cloned = recursive_clone(original)

    assert cloned is not original
    assert cloned.name == original.name
    assert cloned.short_descr == original.short_descr
    assert cloned.prototype.vnum == original.prototype.vnum


def test_do_imotd_returns_help(movable_char_factory):
    """Test do_imotd wrapper returns help text."""
    from mud.rom_api import do_imotd
    from mud.world.world_state import initialize_world

    initialize_world(use_json=True)
    char = movable_char_factory("TestChar", 3001)

    result = do_imotd(char)
    assert isinstance(result, str)


def test_get_max_train_returns_limit(movable_char_factory):
    """Test get_max_train returns stat limit."""
    from mud.rom_api import get_max_train
    from mud.world.world_state import initialize_world

    initialize_world(use_json=True)
    char = movable_char_factory("TestChar", 3001)

    limit = get_max_train(char, "str")
    assert isinstance(limit, int)
    assert limit > 0
