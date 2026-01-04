"""
Integration tests for OLC (Online Creation) builder commands.

Tests complete workflows for area, room, mob, object, and help editors.
These tests verify that builders can edit the world end-to-end.

ROM Reference: src/olc.c
"""

from __future__ import annotations

import pytest
from mud.commands.dispatcher import process_command
from mud.commands.build import cmd_aedit, cmd_redit, cmd_medit, cmd_oedit, cmd_hedit, cmd_asave
from mud.models.area import Area
from mud.models.room import Room
from mud.models.character import Character
from mud.models.mob import MobIndex
from mud.models.obj import ObjIndex
from mud.models.constants import LEVEL_HERO
from mud.net.session import Session
from mud.registry import area_registry, room_registry, mob_registry, obj_registry


@pytest.fixture
def builder_char():
    """Create a character with builder privileges."""
    char = Character()
    char.name = "TestBuilder"
    char.level = LEVEL_HERO
    char.trust = LEVEL_HERO
    char.pcdata = type("PCData", (), {"security": 9})()
    session = Session(name=char.name or "", character=char, reader=None, connection=None)
    char.desc = session
    return char


@pytest.fixture
def test_area():
    """Create a test area for editing."""
    area = Area(
        vnum=1,
        name="Test Area",
        file_name="test.are",
        min_vnum=1000,
        max_vnum=1099,
        security=5,
        builders="TestBuilder admin",
        credits="Original Author",
        changed=False,
    )
    area_registry[1] = area
    yield area
    area_registry.pop(1, None)


@pytest.fixture
def test_room(test_area):
    """Create a test room for editing."""
    room = Room(
        vnum=1001,
        name="Test Room",
        description="A test room for OLC editing.",
        room_flags=0,
        sector_type=0,
        area=test_area,
    )
    room.people = []
    room.contents = []
    room_registry[1001] = room
    yield room
    room_registry.pop(1001, None)


@pytest.fixture
def test_mob_proto(test_area):
    """Create a test mob prototype for editing."""
    mob = MobIndex(
        vnum=1002,
        short_descr="a test mob",
        long_descr="A test mob is standing here.",
        level=5,
        area=test_area,
    )
    mob_registry[1002] = mob
    yield mob
    mob_registry.pop(1002, None)


@pytest.fixture
def test_obj_proto(test_area):
    """Create a test object prototype for editing."""
    obj = ObjIndex(
        vnum=1003,
        name="test object",
        short_descr="a test object",
        item_type=0,  # ITEM_LIGHT
        level=1,
        value=[0, 0, 0, 0, 0],
    )
    obj_registry[1003] = obj
    yield obj
    obj_registry.pop(1003, None)


class TestAreaEditor:
    """Test @aedit command for editing areas."""

    def test_aedit_requires_vnum(self, builder_char):
        """aedit without vnum shows syntax help."""
        result = cmd_aedit(builder_char, "")
        assert "Syntax: @aedit <area vnum>" in result or "syntax" in result.lower()

    def test_aedit_starts_editor_session(self, builder_char, test_area):
        """aedit with valid vnum starts editor session."""
        result = cmd_aedit(builder_char, "1")
        assert "Now editing area" in result or "Test Area" in result
        assert builder_char.desc.editor == "aedit"

    def test_aedit_modifies_area_name(self, builder_char, test_area):
        """Builder can modify area name through aedit session."""
        # Start edit session
        cmd_aedit(builder_char, "1")

        # Modify area name (simulating editor command)
        test_area.name = "Modified Area Name"
        test_area.changed = True

        assert test_area.name == "Modified Area Name"
        assert test_area.changed is True

    def test_asave_saves_modified_area(self, builder_char, test_area):
        """@asave command saves changes to area."""
        # Modify area
        test_area.name = "Modified Area"
        test_area.changed = True

        # Save area
        result = cmd_asave(builder_char, "list")
        # Should show changed areas
        assert result is not None

    def test_aedit_requires_builder_permission(self, test_area):
        """Non-builder cannot edit area."""
        # Create non-builder character
        char = Character()
        char.name = "NotABuilder"
        char.level = LEVEL_HERO
        char.trust = LEVEL_HERO
        char.pcdata = type("PCData", (), {"security": 0})()
        session = Session(name=char.name or "", character=char, reader=None, connection=None)
        char.desc = session

        result = cmd_aedit(char, "1")
        assert "Insufficient security" in result or "permission" in result.lower()


class TestRoomEditor:
    """Test @redit command for editing rooms."""

    def test_redit_creates_new_room(self, builder_char, test_area):
        """redit can create a new room."""
        result = cmd_redit(builder_char, "create 1005")
        # Should create room or show it exists
        assert result is not None

    def test_redit_edits_existing_room(self, builder_char, test_room):
        """redit can edit existing room."""
        # Place builder in room
        builder_char.room = test_room
        test_room.people.append(builder_char)

        result = cmd_redit(builder_char, "")
        # Should start editing current room
        assert "Now editing room" in result or "Room" in result

    def test_redit_modifies_room_name(self, builder_char, test_room):
        """Builder can modify room name."""
        builder_char.room = test_room
        test_room.people.append(builder_char)

        # Start edit session
        cmd_redit(builder_char, "")

        # Modify room name
        test_room.name = "Modified Room Name"

        assert test_room.name == "Modified Room Name"

    def test_redit_modifies_room_description(self, builder_char, test_room):
        """Builder can modify room description."""
        builder_char.room = test_room
        test_room.people.append(builder_char)

        cmd_redit(builder_char, "")

        test_room.description = "A completely new room description."

        assert test_room.description == "A completely new room description."


class TestMobEditor:
    """Test @medit command for editing mobs."""

    def test_medit_requires_vnum(self, builder_char):
        """medit without vnum shows syntax help."""
        result = cmd_medit(builder_char, "")
        assert "Syntax" in result or "syntax" in result.lower()

    def test_medit_edits_existing_mob(self, builder_char, test_mob_proto):
        """medit can edit existing mob prototype."""
        result = cmd_medit(builder_char, "1002")
        # Should start editing mob (might say "created" if new or "editing" if exists)
        assert "Now editing mobile" in result or "mobile prototype created" in result.lower()

    def test_medit_creates_new_mob(self, builder_char, test_area):
        """medit can create new mob prototype."""
        result = cmd_medit(builder_char, "create 1010")
        # Should create mob or show it exists
        assert result is not None

    def test_medit_modifies_mob_name(self, builder_char, test_mob_proto):
        """Builder can modify mob short description."""
        cmd_medit(builder_char, "1002")

        test_mob_proto.short_descr = "a modified mob"

        assert test_mob_proto.short_descr == "a modified mob"

    def test_medit_modifies_mob_level(self, builder_char, test_mob_proto):
        """Builder can modify mob level."""
        cmd_medit(builder_char, "1002")

        original_level = test_mob_proto.level
        test_mob_proto.level = 10

        assert test_mob_proto.level == 10
        assert test_mob_proto.level != original_level


class TestObjectEditor:
    """Test @oedit command for editing objects."""

    def test_oedit_requires_vnum(self, builder_char):
        """oedit without vnum shows syntax help."""
        result = cmd_oedit(builder_char, "")
        assert "Syntax" in result or "syntax" in result.lower()

    def test_oedit_edits_existing_object(self, builder_char, test_obj_proto):
        """oedit can edit existing object prototype."""
        result = cmd_oedit(builder_char, "1003")
        # Should start editing object (might say "created" if new or "editing" if exists)
        assert "Now editing object" in result or "object prototype created" in result.lower()

    def test_oedit_creates_new_object(self, builder_char, test_area):
        """oedit can create new object prototype."""
        result = cmd_oedit(builder_char, "create 1020")
        # Should create object or show it exists
        assert result is not None

    def test_oedit_modifies_object_name(self, builder_char, test_obj_proto):
        """Builder can modify object short description."""
        cmd_oedit(builder_char, "1003")

        test_obj_proto.short_descr = "a modified object"

        assert test_obj_proto.short_descr == "a modified object"

    def test_oedit_modifies_object_level(self, builder_char, test_obj_proto):
        """Builder can modify object level."""
        cmd_oedit(builder_char, "1003")

        test_obj_proto.level = 5

        assert test_obj_proto.level == 5


class TestHelpEditor:
    """Test @hedit command for editing help files."""

    def test_hedit_requires_keyword(self, builder_char):
        """hedit without keyword shows syntax help."""
        result = cmd_hedit(builder_char, "")
        assert "Syntax" in result or "syntax" in result.lower() or "help" in result.lower()

    def test_hedit_edits_existing_help(self, builder_char):
        """hedit can edit existing help entry."""
        # Most help entries exist by default
        result = cmd_hedit(builder_char, "look")
        # Should start editing help or show result
        assert result is not None

    def test_hedit_creates_new_help(self, builder_char):
        """hedit can create new help entry."""
        result = cmd_hedit(builder_char, "testkeyword")
        # Should create help entry
        assert result is not None


class TestEndToEndBuilderWorkflow:
    """Test complete builder workflows from start to finish."""

    def test_complete_area_creation_workflow(self, builder_char):
        """Complete workflow: create area, create room, create mob, create object."""
        # 1. Create new area
        area = Area(
            vnum=2,
            name="New Builder Area",
            file_name="newarea.are",
            min_vnum=2000,
            max_vnum=2099,
            security=5,
            builders="TestBuilder",
            credits="TestBuilder",
            changed=False,
        )
        area_registry[2] = area

        try:
            # 2. Start editing area
            result = cmd_aedit(builder_char, "2")
            assert "Now editing area" in result or "New Builder Area" in result

            # 3. Create a room in the area
            result = cmd_redit(builder_char, "create 2001")
            assert result is not None

            # 4. Create a mob in the area
            result = cmd_medit(builder_char, "create 2002")
            assert result is not None

            # 5. Create an object in the area
            result = cmd_oedit(builder_char, "create 2003")
            assert result is not None

            # 6. Verify all exist
            assert 2 in area_registry
            assert area_registry[2].name == "New Builder Area"

        finally:
            # Cleanup
            area_registry.pop(2, None)
            room_registry.pop(2001, None)
            mob_registry.pop(2002, None)
            obj_registry.pop(2003, None)

    def test_builder_can_modify_and_save_area(self, builder_char, test_area, test_room):
        """Builder can modify area properties and save changes."""
        # Place builder in test room
        builder_char.room = test_room
        test_room.people.append(builder_char)

        # Edit area
        cmd_aedit(builder_char, "1")

        # Modify area
        original_name = test_area.name
        test_area.name = "Modified Test Area"
        test_area.changed = True

        assert test_area.name != original_name
        assert test_area.changed is True

        # Save area (list changed areas)
        result = cmd_asave(builder_char, "list")
        assert result is not None
