"""Integration tests for do_look command ROM C parity.

ROM Reference: src/act_info.c do_look (lines 1037-1313)
"""

from __future__ import annotations

from mud.commands.inspection import do_look
from mud.models.character import Character
from mud.models.constants import AffectFlag, ContainerFlag, Direction, ItemType, PlayerFlag, Position, RoomFlag, Sector
from mud.models.room import Exit, Room


def _basic_room() -> Room:
    room = Room(vnum=3001)
    room.name = "Midgaard Temple"
    room.description = "You are in the temple."
    room.sector_type = int(Sector.INSIDE)
    room.room_flags = 0
    room.light = 1
    room.people = []
    room.contents = []
    room.exits = [None, None, None, None, None, None]
    return room


def _basic_char() -> Character:
    char = Character()
    char.name = "Looker"
    char.level = 1
    char.trust = 0
    char.is_npc = False
    char.position = int(Position.STANDING)
    char.act = 0
    char.comm = 0
    return char


def test_look_room_without_autoexit_does_not_show_exit_line():
    """ROM only calls do_exits('auto') when PLR_AUTOEXIT is set."""
    room = _basic_room()
    north = Room(vnum=3002)
    north.name = "Temple Square"
    north.description = "A busy square."
    north.sector_type = int(Sector.CITY)
    north.room_flags = 0
    north.light = 1
    north.people = []
    north.contents = []
    north.exits = [None, None, None, None, None, None]
    room.exits[int(Direction.NORTH)] = Exit(to_room=north, vnum=north.vnum)

    char = _basic_char()
    char.room = room
    room.people = [char]

    output = do_look(char, "")

    assert output == "Midgaard Temple\nYou are in the temple."


def test_look_room_with_autoexit_shows_exit_line_once():
    """ROM appends auto exits once when PLR_AUTOEXIT is set."""
    room = _basic_room()
    north = Room(vnum=3002)
    north.name = "Temple Square"
    north.description = "A busy square."
    north.sector_type = int(Sector.CITY)
    north.room_flags = 0
    north.light = 1
    north.people = []
    north.contents = []
    north.exits = [None, None, None, None, None, None]
    room.exits[int(Direction.NORTH)] = Exit(to_room=north, vnum=north.vnum)

    char = _basic_char()
    char.act |= int(PlayerFlag.AUTOEXIT)
    char.room = room
    room.people = [char]

    output = do_look(char, "")

    assert output == "Midgaard Temple\nYou are in the temple.\n{o[Exits: north]{x\n"


def test_look_room_contents_are_not_prefixed_with_objects_label():
    """ROM room look appends object lines directly via show_list_to_char."""
    room = _basic_room()

    class Obj:
        # ROM format_obj_to_char(fShort=FALSE) lists ground objects by description.
        short_descr = "a wooden sword"
        description = "A wooden sword lies here."
        name = "sword"
        wear_loc = -1

    obj = Obj()
    room.contents = [obj]

    char = _basic_char()
    char.room = room
    room.people = [char]

    output = do_look(char, "")

    assert output == "Midgaard Temple\nYou are in the temple.\nA wooden sword lies here."


def test_look_room_people_are_not_prefixed_with_characters_label():
    """ROM room look appends visible character lines directly via show_char_to_char."""
    room = _basic_room()

    char = _basic_char()
    char.room = room

    other = Character()
    other.name = "Sneaky"
    other.level = 1
    other.trust = 0
    other.is_npc = False
    other.position = int(Position.STANDING)
    other.room = room

    room.people = [char, other]

    output = do_look(char, "")

    assert output == "Midgaard Temple\nYou are in the temple.\nSneaky"


def test_look_dark_room_shows_raw_visible_character_lines_without_label():
    """ROM dark-room look prints the pitch-black line plus raw show_char_to_char output."""
    room = _basic_room()
    room.light = 0
    room.room_flags = int(RoomFlag.ROOM_DARK)

    char = _basic_char()
    char.affected_by = int(AffectFlag.INFRARED)
    char.room = room

    other = Character()
    other.name = "Sneaky"
    other.level = 1
    other.trust = 0
    other.is_npc = False
    other.position = int(Position.STANDING)
    other.room = room

    room.people = [char, other]

    output = do_look(char, "")

    assert output == "It is pitch black ...\nSneaky"


def test_look_in_drink_container_uses_rom_liquid_color_wording():
    """ROM drink containers show the amount band and liquid color."""
    room = _basic_room()

    class Drink:
        name = "flask water"
        short_descr = "a flask of water"
        item_type = int(ItemType.DRINK_CON)
        value = [10, 10, 0, 0, 0]

    drink = Drink()
    room.contents = [drink]

    char = _basic_char()
    char.room = room
    room.people = [char]

    output = do_look(char, "in flask")

    assert output == "It's more than half-filled with  a clear liquid."


def test_look_in_closed_container_uses_rom_cont_closed_bit():
    """ROM uses CONT_CLOSED=4, not a hardcoded low bit."""
    room = _basic_room()

    class Container:
        name = "chest wooden"
        short_descr = "a wooden chest"
        item_type = int(ItemType.CONTAINER)
        value = [50, int(ContainerFlag.CLOSED), 0, 0, 0]
        contained_items = []

    container = Container()
    room.contents = [container]

    char = _basic_char()
    char.room = room
    room.people = [char]

    output = do_look(char, "in chest")

    assert output == "It is closed."


def test_look_blind_character_gets_rom_blind_message():
    """ROM check_blind gate blocks look before any room/object output."""
    room = _basic_room()

    char = _basic_char()
    char.affected_by = int(AffectFlag.BLIND)
    char.room = room
    room.people = [char]

    output = do_look(char, "")

    assert output == "You can't see a thing!"
