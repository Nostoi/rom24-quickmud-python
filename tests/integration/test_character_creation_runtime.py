"""
Integration tests for character creation runtime initialization.

Tests verify that characters created via create_character() are properly
initialized when loaded into the game runtime.

ROM Reference: src/nanny.c:742-802 (CON_READ_MOTD - final character initialization)
"""

from __future__ import annotations

import pytest

from mud.account.account_manager import load_character
from mud.account.account_service import (
    clear_active_accounts,
    create_account,
    create_character,
    get_creation_classes,
    get_creation_races,
    login,
)
from mud.commands.dispatcher import process_command
from mud.db.models import Base, Character as DBCharacter, PlayerAccount
from mud.db.session import SessionLocal, engine
from mud.models.character import Character
from mud.models.constants import ROOM_VNUM_SCHOOL, Stat
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from mud.security import bans
from mud.world import initialize_world
from mud.world.world_state import reset_lockdowns


@pytest.fixture(scope="module", autouse=True)
def setup_world():
    """Initialize world for character creation tests."""
    initialize_world("area/area.lst")
    yield
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    room_registry.clear()


@pytest.fixture(autouse=True)
def cleanup_db():
    """Clean up database before each test."""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()
    yield


def create_and_load_character(username: str, password: str, char_name: str, **create_kwargs) -> Character | None:
    assert create_account(username, password)
    account = login(username, password)
    assert account is not None

    assert create_character(account, char_name, **create_kwargs)

    capitalized_name = char_name.capitalize()
    return load_character(username, capitalized_name)


class TestCharacterRuntimeInitialization:
    """Test character initialization when loaded from database into runtime."""

    def test_character_loads_with_correct_stats(self):
        """ROM parity: src/nanny.c:476-478 - Race grants base stats + prime stat bonus."""
        races = get_creation_races()
        elf_race = next(r for r in races if r.name.lower() == "elf")

        runtime_char = create_and_load_character("testuser", "password", "TestElf", race=elf_race)
        assert runtime_char is not None

        assert runtime_char.perm_stat[int(Stat.STR)] == 12
        assert runtime_char.perm_stat[int(Stat.INT)] == 17  # 14 base + 3 prime (default mage class)
        assert runtime_char.perm_stat[int(Stat.WIS)] == 13
        assert runtime_char.perm_stat[int(Stat.DEX)] == 15
        assert runtime_char.perm_stat[int(Stat.CON)] == 11

    def test_character_loads_with_prime_stat_bonus(self):
        """ROM parity: src/nanny.c:769 - Prime stat gets +3 bonus."""
        races = get_creation_races()
        classes = get_creation_classes()
        human_race = next(r for r in races if r.name.lower() == "human")
        mage_class = next(c for c in classes if c.name.lower() == "mage")

        runtime_char = create_and_load_character(
            "mageuser", "password", "TestMage", race=human_race, class_type=mage_class
        )
        assert runtime_char is not None

        assert runtime_char.perm_stat[int(Stat.INT)] == 16

    def test_character_starts_in_correct_room(self):
        """
        ROM parity: src/nanny.c:786 - char_to_room(ch, ROOM_VNUM_SCHOOL).

        Verify character spawns in training school (vnum 3001).
        """
        runtime_char = create_and_load_character("roomuser", "password", "TestRoom")
        assert runtime_char is not None
        assert runtime_char.room is not None
        assert runtime_char.room.vnum == ROOM_VNUM_SCHOOL  # 3001

    def test_character_starts_at_level_1(self):
        """
        ROM parity: src/nanny.c:771 - ch->level = 1.

        Verify new characters start at level 1.
        """
        runtime_char = create_and_load_character("lvluser", "password", "TestLevel")
        assert runtime_char is not None
        assert runtime_char.level == 1

    def test_character_has_starting_hp_mana_move(self):
        """
        ROM parity: src/nanny.c:773-775 - hit=max_hit, mana=max_mana, move=max_move.

        Verify character starts with full HP/mana/move.
        """
        runtime_char = create_and_load_character("hpmuser", "password", "TestHpm")
        assert runtime_char is not None

        # Should start with full resources
        assert runtime_char.hit > 0
        assert runtime_char.hit == runtime_char.max_hit
        assert runtime_char.mana > 0
        assert runtime_char.mana == runtime_char.max_mana
        assert runtime_char.move > 0
        assert runtime_char.move == runtime_char.max_move

    def test_character_has_starting_practices_and_trains(self):
        """
        ROM parity: src/nanny.c:776-777 - train=3, practice=5.

        Verify new characters get 3 trains and 5 practices.
        """
        runtime_char = create_and_load_character("practuser", "password", "TestPract")
        assert runtime_char is not None

        assert runtime_char.train == 3
        assert runtime_char.practice == 5

    def test_character_can_execute_basic_commands(self):
        """
        Verify character can execute commands after runtime initialization.

        This ensures the runtime Character is fully functional.
        """
        runtime_char = create_and_load_character("cmduser", "password", "TestCmd")
        assert runtime_char is not None

        # Place character in room
        school_room = room_registry.get(ROOM_VNUM_SCHOOL)
        assert school_room is not None
        runtime_char.room = school_room
        school_room.people.append(runtime_char)

        # Test commands work
        result = process_command(runtime_char, "look")
        assert result is not None
        assert len(result) > 0

        result = process_command(runtime_char, "score")
        assert result is not None
        assert "Testcmd" in result  # Capitalized name in output

        result = process_command(runtime_char, "inventory")
        assert result is not None


class TestClassSpecificInitialization:
    """Test class-specific initialization behaviors."""

    def test_warrior_starts_with_correct_weapon(self):
        """
        ROM parity: Class-specific starting weapon.

        Warriors should start with sword (vnum from class table).
        """
        classes = get_creation_classes()
        warrior_class = next(c for c in classes if c.name.lower() == "warrior")

        runtime_char = create_and_load_character("waruser", "password", "TestWarrior", class_type=warrior_class)
        assert runtime_char is not None

        # Verify default weapon vnum set (warrior uses sword)
        assert runtime_char.default_weapon_vnum == warrior_class.first_weapon_vnum

    def test_mage_starts_with_correct_weapon(self):
        """Mages should start with dagger."""
        classes = get_creation_classes()
        mage_class = next(c for c in classes if c.name.lower() == "mage")

        runtime_char = create_and_load_character("mageweapon", "password", "TestMageWeap", class_type=mage_class)
        assert runtime_char is not None

        assert runtime_char.default_weapon_vnum == mage_class.first_weapon_vnum


class TestRaceSpecificInitialization:
    """Test race-specific initialization behaviors."""

    def test_human_starts_with_human_stats(self):
        """Humans should have balanced 13/13/13/13/13 stats (before class prime bonus)."""
        races = get_creation_races()
        human_race = next(r for r in races if r.name.lower() == "human")

        runtime_char = create_and_load_character("humanuser", "password", "TestHuman", race=human_race)
        assert runtime_char is not None

        assert runtime_char.perm_stat[int(Stat.STR)] == 13
        assert runtime_char.perm_stat[int(Stat.INT)] == 16  # 13 base + 3 prime (default mage)
        assert runtime_char.perm_stat[int(Stat.WIS)] == 13
        assert runtime_char.perm_stat[int(Stat.DEX)] == 13
        assert runtime_char.perm_stat[int(Stat.CON)] == 13

    def test_dwarf_starts_with_dwarf_stats(self):
        """Dwarves should have high STR/CON, low DEX (+ class prime bonus)."""
        races = get_creation_races()
        dwarf_race = next(r for r in races if r.name.lower() == "dwarf")

        runtime_char = create_and_load_character("dwarfuser", "password", "TestDwarf", race=dwarf_race)
        assert runtime_char is not None

        assert runtime_char.perm_stat[int(Stat.STR)] == 14
        assert runtime_char.perm_stat[int(Stat.INT)] == 15  # 12 base + 3 prime (default mage)
        assert runtime_char.perm_stat[int(Stat.WIS)] == 14
        assert runtime_char.perm_stat[int(Stat.DEX)] == 10
        assert runtime_char.perm_stat[int(Stat.CON)] == 15


class TestCharacterPersistence:
    """Test that character state persists correctly across load cycles."""

    def test_modified_character_saves_and_reloads(self):
        """
        Verify that character modifications persist across save/load cycles.
        """
        from mud.account.account_manager import save_character

        runtime_char = create_and_load_character("persistuser", "password", "TestPersist")
        assert runtime_char is not None

        runtime_char.level = 2
        runtime_char.practice = 10

        save_character(runtime_char)

        reloaded_char = load_character("persistuser", "Testpersist")
        assert reloaded_char is not None

        assert reloaded_char.level == 2
        assert reloaded_char.practice == 10
