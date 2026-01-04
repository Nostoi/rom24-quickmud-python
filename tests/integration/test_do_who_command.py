"""Integration tests for do_who command ROM C parity.

Tests verify do_who implements all ROM C features from act_info.c lines 2016-2226.

ROM C Features Tested:
- Argument parsing (level ranges, class/race/immortals filters)
- Level range filtering
- Class filtering
- Race filtering
- Immortals-only filter
- Immortal rank display (IMP/CRE/SUP/DEI/GOD/IMM/DEM/ANG/AVA)
- Race WHO name display
- Class WHO name display
- Status flags (Incog/Wizi/AFK/KILLER/THIEF)
- ROM C output formatting
"""

from __future__ import annotations

import pytest

from mud.commands.info import do_who
from mud.models.character import Character
from mud.models.constants import (
    CommFlag,
    LEVEL_HERO,
    MAX_LEVEL,
    PlayerFlag,
)
from mud.models.races import PC_RACE_TABLE
from mud.net.session import SESSIONS


@pytest.fixture
def clear_sessions():
    """Clear all sessions before each test."""
    SESSIONS.clear()
    yield
    SESSIONS.clear()


@pytest.fixture
def create_test_session():
    """Factory for creating test sessions with characters."""
    from mud.net.session import Session
    from mud.models.room import Room

    def _create(name: str, level: int, ch_class: int, race: int, **kwargs):
        """Create a test session with a character."""
        from mud.models.character import Character

        char = Character()
        char.name = name
        char.level = level
        char.ch_class = ch_class
        char.race = race
        char.title = kwargs.get("title", "")
        char.act = kwargs.get("act", 0)
        char.comm = kwargs.get("comm", 0)
        char.incog_level = kwargs.get("incog_level", 0)
        char.invis_level = kwargs.get("invis_level", 0)

        test_room = Room(vnum=3001)
        char.room = test_room

        sess = Session(name=name, character=char, reader=None, connection=None)
        SESSIONS[name] = sess

        return sess

    return _create


def test_who_no_arguments_shows_all_players(clear_sessions, create_test_session):
    """Test 'who' with no arguments shows all visible players."""
    # Create test characters
    viewer = create_test_session("TestViewer", 1, 0, 0).character
    create_test_session("Player1", 10, 0, 0, title=" the novice")
    create_test_session("Player2", 25, 1, 1, title=" the cleric")
    create_test_session("Player3", 50, 2, 2, title=" the master thief")

    result = do_who(viewer, "")

    assert "Player1" in result
    assert "Player2" in result
    assert "Player3" in result
    assert "Players found: 4" in result  # 3 + viewer


def test_who_level_range_single_number(clear_sessions, create_test_session):
    """Test 'who 40' sets lower bound to 40."""
    viewer = create_test_session("TestViewer", 60, 0, 0).character
    create_test_session("LowLevel", 10, 0, 0)
    create_test_session("HighLevel", 50, 0, 0)

    result = do_who(viewer, "40")

    assert "LowLevel" not in result
    assert "HighLevel" in result
    assert "Players found: 2" in result  # HighLevel + viewer (level 60)


def test_who_level_range_two_numbers(clear_sessions, create_test_session):
    """Test 'who 40 50' filters levels 40-50."""
    viewer = create_test_session("TestViewer", 60, 0, 0).character
    create_test_session("TooLow", 35, 0, 0)
    create_test_session("JustRight", 45, 0, 0)
    create_test_session("TooHigh", 55, 0, 0)

    result = do_who(viewer, "40 50")

    assert "TooLow" not in result
    assert "JustRight" in result
    assert "TooHigh" not in result
    assert "Players found: 1" in result


def test_who_level_range_three_numbers_error(clear_sessions, create_test_session):
    """Test 'who 10 20 30' returns error message."""
    viewer = create_test_session("TestViewer", 60, 0, 0).character

    result = do_who(viewer, "10 20 30")

    assert "Only two level numbers allowed" in result


def test_who_class_filter_warrior(clear_sessions, create_test_session):
    """Test 'who warrior' shows only warriors (class 3)."""
    viewer = create_test_session("TestViewer", 60, 0, 0).character
    create_test_session("Mage1", 20, 0, 0)  # Mage
    create_test_session("Warrior1", 25, 3, 0)  # Warrior
    create_test_session("Warrior2", 30, 3, 1)  # Warrior

    result = do_who(viewer, "warrior")

    assert "Mage1" not in result
    assert "Warrior1" in result
    assert "Warrior2" in result
    assert "Players found: 2" in result


def test_who_race_filter_elf(clear_sessions, create_test_session):
    """Test 'who elf' shows only elves (race 1)."""
    viewer = create_test_session("TestViewer", 60, 0, 0).character
    create_test_session("Human1", 20, 0, 0)  # Human (race 0)
    create_test_session("Elf1", 25, 0, 1)  # Elf (race 1)
    create_test_session("Elf2", 30, 1, 1)  # Elf (race 1)

    result = do_who(viewer, "elf")

    assert "Human1" not in result
    assert "Elf1" in result
    assert "Elf2" in result
    assert "Players found: 2" in result


def test_who_immortals_filter(clear_sessions, create_test_session):
    """Test 'who immortals' shows only immortals (level 52+)."""
    from mud.models.constants import LEVEL_IMMORTAL

    viewer = create_test_session("TestViewer", 60, 0, 0).character
    create_test_session("Mortal1", 50, 0, 0)
    create_test_session("Hero1", 51, 0, 0)
    create_test_session("Immortal1", LEVEL_IMMORTAL, 0, 0)
    create_test_session("Immortal2", 55, 0, 0)

    result = do_who(viewer, "immortals")

    assert "Mortal1" not in result
    assert "Hero1" not in result
    assert "Immortal1" in result
    assert "Immortal2" in result


def test_who_combined_filters(clear_sessions, create_test_session):
    """Test 'who 40 50 elf warrior' combines all filters."""
    viewer = create_test_session("TestViewer", 60, 0, 0).character
    create_test_session("WrongLevel", 35, 3, 1)  # Too low
    create_test_session("WrongClass", 45, 0, 1)  # Mage, not warrior
    create_test_session("WrongRace", 45, 3, 0)  # Human, not elf
    create_test_session("Perfect", 45, 3, 1)  # Level 45, warrior, elf

    result = do_who(viewer, "40 50 elf warrior")

    assert "WrongLevel" not in result
    assert "WrongClass" not in result
    assert "WrongRace" not in result
    assert "Perfect" in result
    assert "Players found: 1" in result


def test_who_invalid_argument(clear_sessions, create_test_session):
    """Test 'who foobar' returns error for invalid class/race."""
    viewer = create_test_session("TestViewer", 60, 0, 0).character

    result = do_who(viewer, "foobar")

    assert "not a valid race, class, or clan" in result


def test_who_immortal_ranks_displayed(clear_sessions, create_test_session):
    """Test immortal ranks display correctly (IMP/CRE/SUP/DEI/GOD/IMM/DEM/ANG/AVA)."""
    viewer = create_test_session("TestViewer", 60, 0, 0).character

    # Create immortals at each rank
    create_test_session("Implementor", MAX_LEVEL - 0, 0, 0)
    create_test_session("Creator", MAX_LEVEL - 1, 0, 0)
    create_test_session("Supreme", MAX_LEVEL - 2, 0, 0)
    create_test_session("Deity", MAX_LEVEL - 3, 0, 0)
    create_test_session("God", MAX_LEVEL - 4, 0, 0)
    create_test_session("Immortal", MAX_LEVEL - 5, 0, 0)
    create_test_session("Demigod", MAX_LEVEL - 6, 0, 0)
    create_test_session("Angel", MAX_LEVEL - 7, 0, 0)
    create_test_session("Avatar", MAX_LEVEL - 8, 0, 0)

    result = do_who(viewer, "")

    # Check rank abbreviations appear
    assert "IMP]" in result
    assert "CRE]" in result
    assert "SUP]" in result
    assert "DEI]" in result
    assert "GOD]" in result
    assert "IMM]" in result
    assert "DEM]" in result
    assert "ANG]" in result
    assert "AVA]" in result


def test_who_race_who_name_displayed(clear_sessions, create_test_session):
    """Test race WHO names display correctly."""
    viewer = create_test_session("TestViewer", 60, 0, 0).character

    # Create characters of different races
    create_test_session("HumanPlayer", 20, 0, 0)  # Race 0 - Human
    create_test_session("ElfPlayer", 20, 0, 1)  # Race 1 - Elf
    create_test_session("DwarfPlayer", 20, 0, 2)  # Race 2 - Dwarf

    result = do_who(viewer, "")

    # Check race WHO names appear (from pc_race_table)
    # Format: [Lv Race   Class]
    assert "Human" in result
    assert " Elf " in result
    assert "Dwarf" in result


def test_who_class_who_name_displayed(clear_sessions, create_test_session):
    """Test class WHO names display correctly."""
    viewer = create_test_session("TestViewer", 60, 0, 0).character

    # Create characters of different classes
    create_test_session("MagePlayer", 20, 0, 0)  # Class 0 - Mage
    create_test_session("ClericPlayer", 20, 1, 0)  # Class 1 - Cleric
    create_test_session("ThiefPlayer", 20, 2, 0)  # Class 2 - Thief
    create_test_session("WarriorPlayer", 20, 3, 0)  # Class 3 - Warrior

    result = do_who(viewer, "")

    # Check class WHO names appear (from CLASS_TABLE)
    # Format: [Lv Race   Class]
    assert "Mag]" in result
    assert "Cle]" in result
    assert "Thi]" in result
    assert "War]" in result


def test_who_status_flag_incog(clear_sessions, create_test_session):
    """Test (Incog) flag displays for incog immortals."""
    viewer = create_test_session("TestViewer", 60, 0, 0).character
    create_test_session("IncogImm", 55, 0, 0, incog_level=LEVEL_HERO)

    result = do_who(viewer, "")

    assert "(Incog)" in result
    assert "IncogImm" in result


def test_who_status_flag_wizi(clear_sessions, create_test_session):
    """Test (Wizi) flag displays for invisible immortals."""
    viewer = create_test_session("TestViewer", 60, 0, 0).character
    create_test_session("WiziImm", 55, 0, 0, invis_level=LEVEL_HERO)

    result = do_who(viewer, "")

    assert "(Wizi)" in result
    assert "WiziImm" in result


def test_who_status_flag_afk(clear_sessions, create_test_session):
    """Test [AFK] flag displays for AFK players."""
    viewer = create_test_session("TestViewer", 60, 0, 0).character
    create_test_session("AFKPlayer", 20, 0, 0, comm=CommFlag.AFK)

    result = do_who(viewer, "")

    assert "[AFK]" in result
    assert "AFKPlayer" in result


def test_who_status_flag_killer(clear_sessions, create_test_session):
    """Test (KILLER) flag displays for killer-flagged players."""
    viewer = create_test_session("TestViewer", 60, 0, 0).character
    create_test_session("KillerPlayer", 20, 0, 0, act=PlayerFlag.KILLER)

    result = do_who(viewer, "")

    assert "(KILLER)" in result
    assert "KillerPlayer" in result


def test_who_status_flag_thief(clear_sessions, create_test_session):
    """Test (THIEF) flag displays for thief-flagged players."""
    viewer = create_test_session("TestViewer", 60, 0, 0).character
    create_test_session("ThiefPlayer", 20, 0, 0, act=PlayerFlag.THIEF)

    result = do_who(viewer, "")

    assert "(THIEF)" in result
    assert "ThiefPlayer" in result


def test_who_multiple_status_flags(clear_sessions, create_test_session):
    """Test multiple status flags display together."""
    viewer = create_test_session("TestViewer", 60, 0, 0).character
    create_test_session(
        "FlaggedPlayer",
        20,
        0,
        0,
        comm=CommFlag.AFK,
        act=PlayerFlag.KILLER | PlayerFlag.THIEF,
    )

    result = do_who(viewer, "")

    assert "[AFK]" in result
    assert "(KILLER)" in result
    assert "(THIEF)" in result
    assert "FlaggedPlayer" in result


def test_who_output_format_matches_rom_c(clear_sessions, create_test_session):
    """Test output format matches ROM C exactly: [Lv Race   Class] Flags Name Title."""
    viewer = create_test_session("TestViewer", 60, 0, 0).character
    create_test_session("TestPlayer", 25, 3, 1, title=" the Warrior")

    result = do_who(viewer, "")

    # Check format: [Lv Race   Class] Name Title
    # Should contain: [25  Elf  War] TestPlayer the Warrior
    assert "[25" in result
    assert "Elf" in result
    assert "War]" in result
    assert "TestPlayer the Warrior" in result


def test_who_no_matches_shows_zero(clear_sessions, create_test_session):
    """Test 'who' with filters that match nothing shows 'Players found: 0'."""
    viewer = create_test_session("TestViewer", 60, 0, 0).character
    create_test_session("Player1", 10, 0, 0)

    result = do_who(viewer, "warrior")  # No warriors exist

    assert "Player1" not in result
    assert "Players found: 0" in result
